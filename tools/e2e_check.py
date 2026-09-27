#!/usr/bin/env python3
"""End-to-end checks for the DTS website (Playwright + Chromium).

Usage:
    python3 -m http.server 8000                       # in another terminal
    python3 tools/e2e_check.py                        # local, screenshots -> tools/screenshots/
    python3 tools/e2e_check.py --base https://drtherapyservices.github.io --prefix live-

Setup: pip install playwright && playwright install chromium
Exit code is 0 when every check passes, 1 otherwise.
"""
import argparse
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright

# Keep in sync with js/config.js
TZ = ZoneInfo("America/Toronto")
TZ_LABEL = "Eastern Time (Toronto)"
WORKING_DAYS = {0, 1, 2, 3, 4}  # Python weekday(): Monday = 0
MAX_DAYS_AHEAD = 60
MIN_NOTICE_HOURS = 12
EXPECTED_SLOTS = [f"{(h + 11) % 12 + 1}:{m:02d} {'pm' if h >= 12 else 'am'}"
                  for h in range(9, 17) for m in (0, 30)]  # 9:00 am ... 4:30 pm

VIEWPORTS = {"desktop": (1400, 900), "mobile": (390, 844)}
SHOTS = Path(__file__).resolve().parent / "screenshots"
IGNORED_ERRORS = ("fonts.googleapis.com", "fonts.gstatic.com")

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail and not ok else ""))
    return ok


def new_page(browser, viewport, errors):
    w, h = VIEWPORTS[viewport]
    ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=1)
    page = ctx.new_page()

    def on_console(msg):
        if msg.type == "error" and not any(s in msg.text for s in IGNORED_ERRORS) \
                and not any(s in (msg.location or {}).get("url", "") for s in IGNORED_ERRORS):
            errors.append(msg.text)

    page.on("console", on_console)
    page.on("pageerror", lambda exc: errors.append(f"pageerror: {exc}"))
    page.on("requestfailed", lambda req: None if any(s in req.url for s in IGNORED_ERRORS)
            else errors.append(f"request failed: {req.url}"))
    return ctx, page


def scroll_through(page):
    """Scroll down in viewport-sized steps so every .reveal element intersects and animates in."""
    height = page.evaluate("document.documentElement.scrollHeight")
    step = page.viewport_size["height"] // 2
    for y in range(0, height + step, step):
        page.evaluate(f"window.scrollTo(0, {y})")
        page.wait_for_timeout(120)
    page.wait_for_timeout(900)  # let the .7s reveal transitions finish
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(300)


def layout_checks(page, label):
    overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
    check(f"{label}: no horizontal overflow", overflow <= 0, f"page is {overflow}px wider than viewport")
    hidden = page.evaluate("[...document.querySelectorAll('.reveal')].filter(e => !e.classList.contains('in')).length")
    check(f"{label}: all reveal elements animated in", hidden == 0, f"{hidden} still hidden")
    broken = page.evaluate("[...document.images].filter(i => !i.complete || i.naturalWidth === 0).map(i => i.src)")
    check(f"{label}: all images loaded", not broken, ", ".join(broken))
    no_alt = page.evaluate("[...document.images].filter(i => !i.hasAttribute('alt')).map(i => i.src)")
    check(f"{label}: every <img> has an alt attribute", not no_alt, ", ".join(no_alt))


def screenshot_pages(browser, base, prefix):
    for path in ("index.html", "book.html"):
        for vp in VIEWPORTS:
            label = f"{path} @ {vp}"
            print(f"\n{label}")
            errors = []
            ctx, page = new_page(browser, vp, errors)
            resp = page.goto(f"{base}/{path}", wait_until="networkidle")
            check(f"{label}: HTTP 200", resp and resp.status == 200, f"status {resp and resp.status}")
            scroll_through(page)
            layout_checks(page, label)
            if path == "book.html":
                check(f"{label}: demo-mode banner visible", page.is_visible("#demo-banner"))
            out = SHOTS / f"{prefix}{path.replace('.html', '')}-{vp}.png"
            page.screenshot(path=str(out), full_page=True)
            check(f"{label}: no console errors", not errors, " | ".join(errors))
            ctx.close()


def mobile_menu_and_anchor(browser, base):
    print("\nindex.html @ mobile: menu + anchor")
    errors = []
    ctx, page = new_page(browser, "mobile", errors)
    page.goto(f"{base}/index.html", wait_until="networkidle")
    toggle, links = page.locator(".nav-toggle"), page.locator("#navlinks")
    check("mobile: menu toggle visible", toggle.is_visible())
    check("mobile: menu starts closed", "open" not in (links.get_attribute("class") or ""))
    toggle.click()
    page.wait_for_timeout(400)
    check("mobile: menu opens", "open" in links.get_attribute("class")
          and toggle.get_attribute("aria-expanded") == "true")
    check("mobile: menu links clickable when open", page.locator("#navlinks a[href='#services']").is_visible())
    toggle.click()
    page.wait_for_timeout(400)
    check("mobile: menu closes", "open" not in links.get_attribute("class")
          and toggle.get_attribute("aria-expanded") == "false")
    toggle.click()
    page.wait_for_timeout(400)
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    check("mobile: Escape closes menu", "open" not in links.get_attribute("class"))
    toggle.click()
    page.wait_for_timeout(400)
    page.locator("#navlinks a[href='#services']").click()
    page.wait_for_timeout(1500)  # smooth scroll
    top = page.evaluate("document.getElementById('services').getBoundingClientRect().top")
    check("mobile: anchor link closes menu", "open" not in links.get_attribute("class"))
    check("mobile: anchor scrolls to #services with nav offset", 40 <= top <= 100, f"section top at {top:.0f}px")
    check("mobile: URL hash updated", page.evaluate("location.hash") == "#services")
    check("mobile menu: no console errors", not errors, " | ".join(errors))
    ctx.close()


def calendar_rules(page):
    """Walk every month the calendar allows and compare each day's enabled state with the rules."""
    now = datetime.now(TZ)
    today, max_day = now.date(), now.date() + timedelta(days=MAX_DAYS_AHEAD)
    check("calendar: previous-month button disabled on current month", page.is_disabled("#cal-prev"))
    today_btn = page.locator(f".day[data-date='{today.isoformat()}']")
    check("calendar: today is marked", "today" in (today_btn.get_attribute("class") or ""))
    wrong, seen, months = [], {"past": 0, "weekend": 0, "beyond": 0}, 0
    while True:
        months += 1
        for btn in page.locator(".day[data-date]").all():
            d = date.fromisoformat(btn.get_attribute("data-date"))
            expect = today <= d <= max_day and d.weekday() in WORKING_DAYS
            enabled = btn.is_enabled()
            if enabled != expect:
                wrong.append(f"{d} enabled={enabled}")
            if not enabled:
                seen["past"] += d < today
                seen["weekend"] += d.weekday() not in WORKING_DAYS
                seen["beyond"] += d > max_day
            if not btn.get_attribute("aria-label"):
                wrong.append(f"{d} missing aria-label")
        if page.is_disabled("#cal-next"):
            break
        page.click("#cal-next")
    check("calendar: every day enabled/disabled per rules (past, weekends, >60 days)", not wrong, ", ".join(wrong[:8]))
    check("calendar: weekend days disabled", seen["weekend"] > 0)
    check(f"calendar: days beyond {MAX_DAYS_AHEAD} days disabled", seen["beyond"] > 0)
    if today.day > 1:
        check("calendar: past days disabled", seen["past"] > 0)
    last_month = (max_day.year, max_day.month)
    title = page.inner_text("#cal-title")
    check("calendar: next-month button stops at the month of the last bookable day",
          title == max_day.strftime("%B %Y") and months == (last_month[0] - today.year) * 12 + last_month[1] - today.month + 1,
          f"stopped at {title}")
    # back to the first month
    while not page.is_disabled("#cal-prev"):
        page.click("#cal-prev")


def pick_day_with_free_slot(page):
    """Click enabled days in order until one has at least one enabled slot. Returns the date string."""
    while True:
        for btn in page.locator(".day[data-date]:enabled").all():
            d = btn.get_attribute("data-date")
            btn.click()
            page.wait_for_selector(".slot")
            if page.locator(".slot:enabled").count():
                return d
        if page.is_disabled("#cal-next"):
            return None
        page.click("#cal-next")


def booking_flow(browser, base, prefix, vp):
    label = f"booking @ {vp}"
    print(f"\n{label}")
    errors = []
    ctx, page = new_page(browser, vp, errors)
    page.goto(f"{base}/book.html", wait_until="networkidle")
    submit = page.locator("#submit-btn")
    check(f"{label}: demo-mode banner shown", page.is_visible("#demo-banner"))
    check(f"{label}: Book now disabled initially", submit.is_disabled())
    if vp == "desktop":
        calendar_rules(page)

    # first enabled day
    first = page.locator(".day[data-date]:enabled").first
    first_date = first.get_attribute("data-date") if first.count() else None
    if first_date is None:  # month has no bookable days left; go to next month
        page.click("#cal-next")
        first = page.locator(".day[data-date]:enabled").first
        first_date = first.get_attribute("data-date")
    first.click()
    page.wait_for_selector(".slot")
    slots = page.locator(".slot")
    texts = [t.strip() for t in slots.all_inner_texts()]
    check(f"{label}: exactly 16 time slots 9:00 am … 4:30 pm", texts == EXPECTED_SLOTS, str(texts))
    n_disabled = page.locator(".slot:disabled").count()
    n_enabled = page.locator(".slot:enabled").count()
    check(f"{label}: enabled + disabled slots = 16", n_enabled + n_disabled == 16, f"{n_enabled}+{n_disabled}")
    check(f"{label}: slot buttons carry aria-pressed", all(s.get_attribute("aria-pressed") in ("true", "false") for s in slots.all()))
    # MIN_NOTICE_HOURS: every slot less than 12 h away must be disabled
    now = datetime.now(TZ)
    y, m, d = map(int, first_date.split("-"))
    too_soon = []
    for s, t in zip(slots.all(), EXPECTED_SLOTS):
        hh, mm = divmod(EXPECTED_SLOTS.index(t) * 30 + 9 * 60, 60)
        start = datetime(y, m, d, hh, mm, tzinfo=TZ)
        if start < now + timedelta(hours=MIN_NOTICE_HOURS) and s.is_enabled():
            too_soon.append(t)
    check(f"{label}: slots within {MIN_NOTICE_HOURS} h are disabled", not too_soon, ", ".join(too_soon))
    check(f"{label}: Book now still disabled with only a date", submit.is_disabled())

    day = first_date if n_enabled else pick_day_with_free_slot(page)
    check(f"{label}: found a day with a free slot", day is not None)
    slot = page.locator(".slot:enabled").first
    slot_text = slot.inner_text().strip()
    slot.click()
    check(f"{label}: selected slot marked aria-pressed=true", slot.get_attribute("aria-pressed") == "true")
    check(f"{label}: Book now disabled with date + time only", submit.is_disabled())

    page.fill("#name", "Test Client")
    page.fill("#email", "not-an-email")
    page.locator("#email").blur()
    check(f"{label}: invalid email shows error message",
          "invalid" in page.get_attribute("#f-email", "class") and page.is_visible("#f-email .err"))
    check(f"{label}: Book now disabled with invalid email", submit.is_disabled())
    page.fill("#phone", "abc")
    check(f"{label}: invalid phone shows error message", page.is_visible("#f-phone .err"))
    page.fill("#phone", "+1 (555) 123-4567")
    check(f"{label}: valid phone clears error", not page.is_visible("#f-phone .err"))
    page.fill("#email", "test@example.com")
    check(f"{label}: valid email clears error", not page.is_visible("#f-email .err"))
    check(f"{label}: Book now disabled until consent ticked", submit.is_disabled())
    page.check("#consent")
    check(f"{label}: Book now enabled with email + consent + date + time", submit.is_enabled())
    page.fill("#email", "")
    check(f"{label}: Book now disabled when email removed", submit.is_disabled())
    page.fill("#email", "test@example.com")
    page.uncheck("#consent")
    check(f"{label}: Book now disabled when consent removed", submit.is_disabled())
    page.check("#consent")
    page.fill("#phone", "")
    check(f"{label}: phone is optional", submit.is_enabled())
    page.fill("#phone", "+1 (555) 123-4567")
    check(f"{label}: notes field optional (no required attr)", page.get_attribute("#notes", "required") is None)
    hp = page.locator(".hp").bounding_box()
    check(f"{label}: honeypot hidden off-screen", hp is None or hp["x"] + hp["width"] <= 0 or hp["width"] == 0)
    overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
    check(f"{label}: filled form has no horizontal overflow", overflow <= 0, f"{overflow}px")
    page.evaluate("window.scrollTo(0, 0)")  # sticky nav/summary would otherwise land mid-screenshot
    page.wait_for_timeout(600)
    page.screenshot(path=str(SHOTS / f"{prefix}book-filled-{vp}.png"), full_page=True)

    submit.click()
    page.wait_for_selector("#confirmation", state="visible", timeout=10000)
    page.wait_for_timeout(800)
    when = page.inner_text("#c-when")
    y, m, d = map(int, day.split("-"))
    long_date = date(y, m, d).strftime("%A, %B ") + str(d) + date(y, m, d).strftime(", %Y")
    check(f"{label}: confirmation visible", page.is_visible("#confirmation"))
    check(f"{label}: confirmation shows date + time in Eastern Time (Toronto)",
          long_date in when and slot_text in when and TZ_LABEL in when, when)
    href = page.get_attribute("#c-link", "href")
    check(f"{label}: confirmation shows a meet link", bool(re.match(r"https://meet\.google\.com/\S+", href or "")), href)
    check(f"{label}: confirmation email echoed", page.inner_text("#c-email") == "test@example.com")
    page.screenshot(path=str(SHOTS / f"{prefix}book-confirmation-{vp}.png"), full_page=True)
    overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
    check(f"{label}: confirmation has no horizontal overflow", overflow <= 0, f"{overflow}px")
    check(f"{label}: no console errors", not errors, " | ".join(errors))
    ctx.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000")
    ap.add_argument("--prefix", default="", help="screenshot filename prefix, e.g. live-")
    args = ap.parse_args()
    base = args.base.rstrip("/")
    SHOTS.mkdir(exist_ok=True)
    print(f"Testing {base}  (today in Toronto: {datetime.now(TZ):%a %Y-%m-%d %H:%M})")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        screenshot_pages(browser, base, args.prefix)
        mobile_menu_and_anchor(browser, base)
        for vp in VIEWPORTS:
            booking_flow(browser, base, args.prefix, vp)
        browser.close()
    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed. Screenshots: {SHOTS}")
    for name, _, detail in failed:
        print(f"  FAILED: {name} — {detail}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
