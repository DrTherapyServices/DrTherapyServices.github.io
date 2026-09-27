/* =========================================================
   Booking page logic: calendar -> time slots -> details -> submit.
   Talks to the Google Apps Script backend (backend/Code.gs).
   All times are in DTS_CONFIG.TIMEZONE regardless of the visitor's zone.
   ========================================================= */
(function () {
  const cfg = window.DTS_CONFIG || {};
  const TZ = cfg.TIMEZONE || "America/Toronto";
  const DEMO = !cfg.API_URL;
  const $ = (id) => document.getElementById(id);

  // ---------- helpers: dates in the business time-zone ----------
  const pad = (n) => String(n).padStart(2, "0");
  function nowInTZ() {
    // Returns {y,m,d,h,min} for the current moment in TZ, plus a pseudo-UTC ms value for arithmetic.
    const parts = new Intl.DateTimeFormat("en-US", {
      timeZone: TZ, hour12: false, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit",
    }).formatToParts(new Date());
    const g = (t) => Number(parts.find((p) => p.type === t).value);
    const o = { y: g("year"), m: g("month"), d: g("day"), h: g("hour") % 24, min: g("minute") };
    o.ms = Date.UTC(o.y, o.m - 1, o.d, o.h, o.min);
    return o;
  }
  const ymd = (y, m, d) => `${y}-${pad(m)}-${pad(d)}`;
  const parseYmd = (s) => s.split("-").map(Number);
  const weekday = (y, m, d) => new Date(Date.UTC(y, m - 1, d)).getUTCDay();
  const daysInMonth = (y, m) => new Date(Date.UTC(y, m, 0)).getUTCDate();
  const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  const DOWS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  function fmtLongDate(s) {
    const [y, m, d] = parseYmd(s);
    return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric", year: "numeric", timeZone: "UTC" });
  }
  function fmtTime(hhmm) {
    const [h, m] = hhmm.split(":").map(Number);
    const ap = h >= 12 ? "pm" : "am";
    const h12 = ((h + 11) % 12) + 1;
    return `${h12}:${pad(m)} ${ap}`;
  }
  function endOf(hhmm) {
    const [h, m] = hhmm.split(":").map(Number);
    const t = h * 60 + m + (cfg.SLOT_MINUTES || 30);
    return `${pad(Math.floor(t / 60))}:${pad(t % 60)}`;
  }
  function allSlots() {
    const out = [];
    for (let t = (cfg.START_HOUR || 9) * 60; t + (cfg.SLOT_MINUTES || 30) <= (cfg.END_HOUR || 17) * 60; t += cfg.SLOT_MINUTES || 30) {
      out.push(`${pad(Math.floor(t / 60))}:${pad(t % 60)}`);
    }
    return out;
  }

  // ---------- state ----------
  const now = nowInTZ();
  const today = ymd(now.y, now.m, now.d);
  const maxDate = (() => { const t = new Date(Date.UTC(now.y, now.m - 1, now.d + (cfg.MAX_DAYS_AHEAD || 60))); return ymd(t.getUTCFullYear(), t.getUTCMonth() + 1, t.getUTCDate()); })();
  let view = { y: now.y, m: now.m };
  let selDate = null, selTime = null;
  const bookedCache = {};

  function dateBookable(s) {
    if (s < today || s > maxDate) return false;
    const [y, m, d] = parseYmd(s);
    return (cfg.WORKING_DAYS || [1, 2, 3, 4, 5]).includes(weekday(y, m, d));
  }
  function slotTooSoon(dateStr, hhmm) {
    const [y, m, d] = parseYmd(dateStr); const [h, mi] = hhmm.split(":").map(Number);
    return Date.UTC(y, m - 1, d, h, mi) < nowInTZ().ms + (cfg.MIN_NOTICE_HOURS || 0) * 3600e3;
  }

  // ---------- header chips ----------
  $("book-meta").innerHTML = [
    `⏱ ${cfg.APPOINTMENT_TYPE || "Free consultation"}`,
    `▶ ${cfg.MEETING_PLATFORM || "Video call"}`,
    `🕘 ${fmtTime(pad(cfg.START_HOUR || 9) + ":00")} – ${fmtTime(pad(cfg.END_HOUR || 17) + ":00")} ${cfg.TIMEZONE_LABEL || TZ}`,
  ].map((t) => `<span class="chip">${t}</span>`).join("");
  $("tz-note").textContent = `All times are shown in ${cfg.TIMEZONE_LABEL || TZ}. Each consultation lasts ${cfg.SLOT_MINUTES || 30} minutes.`;
  $("s-type").textContent = cfg.APPOINTMENT_TYPE || "Consultation";
  $("s-where").textContent = cfg.MEETING_PLATFORM || "Video call";
  if (DEMO) $("demo-banner").style.display = "block";
  const cc = $("c-contact"); if (cc) { cc.href = "mailto:" + (cfg.CONTACT_EMAIL || ""); cc.textContent = cfg.CONTACT_EMAIL || ""; }

  // Pre-fill notes from ?for=child|teen|adult (links on the home page)
  const forParam = new URLSearchParams(location.search).get("for");
  if (forParam) {
    const map = { child: "This consultation is for my child.", teen: "This consultation is for my teenager.", adult: "This consultation is for myself / my family." };
    if (map[forParam]) $("notes").value = map[forParam] + " ";
  }

  // ---------- calendar ----------
  function renderCalendar() {
    const { y, m } = view;
    $("cal-title").textContent = `${MONTHS[m - 1]} ${y}`;
    const grid = $("cal-grid");
    grid.innerHTML = DOWS.map((d) => `<div class="dow">${d}</div>`).join("");
    const first = weekday(y, m, 1);
    for (let i = 0; i < first; i++) grid.insertAdjacentHTML("beforeend", '<button class="day empty" tabindex="-1" disabled></button>');
    for (let d = 1; d <= daysInMonth(y, m); d++) {
      const s = ymd(y, m, d);
      const ok = dateBookable(s);
      const cls = ["day", s === today ? "today" : "", s === selDate ? "selected" : ""].join(" ").trim();
      grid.insertAdjacentHTML("beforeend", `<button class="${cls}" data-date="${s}" ${ok ? "" : "disabled"} aria-label="${fmtLongDate(s)}${ok ? "" : " (unavailable)"}" aria-pressed="${s === selDate}">${d}</button>`);
    }
    // prev/next limits
    $("cal-prev").disabled = y === now.y && m === now.m;
    const [my, mm] = parseYmd(maxDate);
    $("cal-next").disabled = y === my && m === mm;
  }
  $("cal-prev").addEventListener("click", () => { view.m--; if (view.m < 1) { view.m = 12; view.y--; } renderCalendar(); });
  $("cal-next").addEventListener("click", () => { view.m++; if (view.m > 12) { view.m = 1; view.y++; } renderCalendar(); });
  $("cal-grid").addEventListener("click", (e) => {
    const b = e.target.closest(".day[data-date]");
    if (!b || b.disabled) return;
    selDate = b.dataset.date; selTime = null;
    renderCalendar(); renderSlots(); updateSummary();
    $("date-done").textContent = "✓ " + fmtLongDate(selDate).replace(/,\s\d{4}$/, "");
    $("time-done").textContent = "";
    if (window.innerWidth < 960) $("step-time").scrollIntoView({ behavior: "smooth", block: "start" });
  });

  // ---------- slots ----------
  async function fetchBooked(dateStr) {
    if (bookedCache[dateStr]) return bookedCache[dateStr];
    if (DEMO) {
      // Fake a couple of taken slots so the UI can be tested offline.
      const fake = allSlots().filter((_, i) => (i * 7 + dateStr.charCodeAt(9)) % 5 === 0);
      bookedCache[dateStr] = fake; return fake;
    }
    const res = await fetch(`${cfg.API_URL}?action=slots&date=${encodeURIComponent(dateStr)}&key=${encodeURIComponent(cfg.SITE_KEY || "")}`, { method: "GET" });
    const data = await res.json();
    if (!data.ok) throw new Error(data.error || "Could not load availability");
    bookedCache[dateStr] = data.booked || [];
    return bookedCache[dateStr];
  }
  async function renderSlots() {
    const wrap = $("slots-wrap");
    if (!selDate) { wrap.innerHTML = '<div class="placeholder">Select a date to see available times.</div>'; return; }
    wrap.innerHTML = '<div class="placeholder">Checking availability…</div>';
    let booked = [];
    try { booked = await fetchBooked(selDate); }
    catch (err) { wrap.innerHTML = `<div class="alert alert-err">Sorry — we couldn't load availability (${err.message}). Please try again in a moment.</div>`; return; }
    const slots = allSlots();
    let free = 0;
    wrap.innerHTML = '<div class="slots">' + slots.map((t) => {
      const taken = booked.includes(t) || slotTooSoon(selDate, t);
      if (!taken) free++;
      return `<button class="slot ${t === selTime ? "selected" : ""}" data-time="${t}" ${taken ? "disabled" : ""} aria-pressed="${t === selTime}">${fmtTime(t)}</button>`;
    }).join("") + "</div>";
    if (!free) wrap.insertAdjacentHTML("beforeend", '<p class="slots-note">No openings left on this day — please pick another date.</p>');
  }
  $("slots-wrap").addEventListener("click", (e) => {
    const b = e.target.closest(".slot[data-time]");
    if (!b || b.disabled) return;
    selTime = b.dataset.time;
    document.querySelectorAll(".slot").forEach((s) => { s.classList.toggle("selected", s === b); s.setAttribute("aria-pressed", String(s === b)); });
    $("time-done").textContent = "✓ " + fmtTime(selTime);
    updateSummary();
    if (window.innerWidth < 960) $("step-details").scrollIntoView({ behavior: "smooth", block: "start" });
  });

  // ---------- summary + validation ----------
  const form = $("book-form");
  const emailOk = (v) => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v);
  const phoneOk = (v) => !v || /^[+()\-.\s\d]{7,25}$/.test(v);
  function validate(showErrors) {
    const name = $("name").value.trim(), email = $("email").value.trim(), phone = $("phone").value.trim();
    const checks = [["f-name", !!name], ["f-email", emailOk(email)], ["f-phone", phoneOk(phone)]];
    let ok = true;
    checks.forEach(([id, pass]) => { if (showErrors) $(id).classList.toggle("invalid", !pass); if (!pass) ok = false; });
    return ok && $("consent").checked && !!selDate && !!selTime;
  }
  function updateSummary() {
    $("s-date").textContent = selDate ? fmtLongDate(selDate) : "Not selected";
    $("s-date").classList.toggle("empty", !selDate);
    $("s-time").textContent = selTime ? `${fmtTime(selTime)} – ${fmtTime(endOf(selTime))}` : "Not selected";
    $("s-time").classList.toggle("empty", !selTime);
    $("submit-btn").disabled = !validate(false);
  }
  form.addEventListener("input", () => { validate(true); updateSummary(); });
  form.addEventListener("submit", (e) => e.preventDefault());

  // ---------- submit ----------
  async function submit() {
    if (!validate(true)) { updateSummary(); return; }
    const btn = $("submit-btn"), errBox = $("submit-error");
    btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Booking…'; errBox.style.display = "none";
    const payload = {
      key: cfg.SITE_KEY || "",
      date: selDate, time: selTime,
      name: $("name").value.trim(), email: $("email").value.trim(), phone: $("phone").value.trim(),
      notes: $("notes").value.trim(),
      website: form.elements.website.value,           // honeypot
      clientTimezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "",
      page: location.href,
    };
    try {
      let data;
      if (DEMO) {
        await new Promise((r) => setTimeout(r, 900));
        data = { ok: true, id: "DEMO-" + Math.random().toString(36).slice(2, 8).toUpperCase(), meetLink: "https://meet.google.com/demo-link-xyz" };
      } else {
        // text/plain avoids a CORS pre-flight request, which Apps Script web apps do not answer.
        const res = await fetch(cfg.API_URL, { method: "POST", headers: { "Content-Type": "text/plain;charset=utf-8" }, body: JSON.stringify(payload), redirect: "follow" });
        data = await res.json();
      }
      if (!data.ok) throw new Error(data.error || "Booking failed");
      showConfirmation(data, payload);
    } catch (err) {
      errBox.textContent = /taken|no longer available/i.test(err.message)
        ? "That time was just taken by someone else. Please choose another slot."
        : `Something went wrong (${err.message}). Please try again, or email us directly.`;
      errBox.style.display = "block";
      delete bookedCache[selDate]; renderSlots();
      btn.disabled = false; btn.innerHTML = 'Book now <span class="arrow">→</span>';
    }
  }
  $("submit-btn").addEventListener("click", submit);

  function showConfirmation(data, payload) {
    $("booking-ui").style.display = "none";
    document.querySelector(".book-hero").style.display = "none";
    $("demo-banner").style.display = "none";
    $("c-email").textContent = payload.email;
    $("c-type").textContent = cfg.APPOINTMENT_TYPE || "Consultation";
    $("c-when").textContent = `${fmtLongDate(payload.date)} · ${fmtTime(payload.time)} – ${fmtTime(endOf(payload.time))} ${cfg.TIMEZONE_LABEL || TZ}`;
    const link = $("c-link"); link.href = data.meetLink || "#"; link.textContent = data.meetLink || "Sent by email";
    $("c-id").textContent = data.id || "—";
    $("confirmation").style.display = "block";
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  // ---------- init ----------
  renderCalendar(); updateSummary();
})();
