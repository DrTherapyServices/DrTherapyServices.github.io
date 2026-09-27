# DTS — Doctor Therapy Services · Website

Static website + free booking backend for **DTS** (ABA therapy, autism support, mental-health counseling).

* Live site (after setup): **https://drtherapyservices.github.io**
* Deployed from: `DrTherapyServices/DrTherapyServices.github.io` (GitHub Pages)
* Backup mirror: `digonto10602/DrTherapyServices-backup` (automatic via GitHub Actions)
* Booking backend: Google Apps Script (`backend/Code.gs`) → Google Meet link, confirmation emails, admin-only Google Sheet + CSV

## Quick start

```bash
python3 -m http.server 8000     # open http://localhost:8000  (booking page runs in demo mode until configured)
```

Then follow **[docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md)** step by step, or hand the folder to Claude Code and use the
prompts in **[CLAUDE_CODE_PROMPT.md](CLAUDE_CODE_PROMPT.md)**.

## Structure

```
index.html            home page
book.html             booking page (calendar · 30-min slots 9–5 MT · form · confirmation)
css/styles.css        design system + components
js/config.js          ← the only file you must edit to go live
js/main.js            nav, smooth scroll, reveal animations
js/booking.js         booking logic (talks to the Apps Script backend)
assets/               logo + SVG illustrations
tools/                make_illustrations.py (regenerates the SVGs)
backend/              Code.gs + appsscript.json (Google Apps Script)
.github/workflows/    mirror-backup.yml
docs/SETUP_GUIDE.md   step-by-step setup (GitHub org, Pages, backup, Google backend, admins, domain)
CLAUDE.md             instructions for Claude Code
CLAUDE_CODE_PROMPT.md prompts to paste into Claude Code
```

## Admins

Admins are rows in the **Admins** tab of the `DTS Bookings` Google Sheet (email · name · TRUE/FALSE).
Edit the tab, then run **DTS Admin → Sync admin access** from the sheet menu. No code changes needed.
