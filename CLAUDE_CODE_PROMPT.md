# Prompts for Claude Code (copy-paste, one at a time)

Open a terminal in the unzipped `dts-website` folder and start `claude`. Claude Code will read
`CLAUDE.md` automatically. Paste the prompts below in order; wait for each to finish.

---

## Prompt 1 — Verify the package and run it locally

```
Read CLAUDE.md and docs/SETUP_GUIDE.md first. Then:
1. Start a local server (python3 -m http.server 8000) in the background.
2. Install Playwright with Chromium if it isn't available (pip install playwright && playwright install chromium).
3. Write a small Playwright script under tools/ that screenshots index.html and book.html at 390x844 and 1400x900
   (full page), and also walks the booking flow in demo mode: click the first available day, click the first available
   slot, fill name/email/phone, tick consent, press "Book now", and screenshot the confirmation.
4. Show me the screenshots and report any console errors other than blocked Google Fonts requests.
5. Run through the "Testing checklist" in CLAUDE.md and tell me what passes and what fails. Fix anything that fails.
Do not change the design or copy in this step.
```

## Prompt 2 — Personalize the content (do this before going live)

```
Help me make the site copy truthful for my actual practice. Ask me, one question at a time:
- the legal business name and the state(s) we operate in,
- which of the 8 services we really offer today (remove or mark "coming soon" the others),
- our clinicians' real credentials (only keep "BCBA"/"licensed" wording if true),
- ages served, in-person locations vs telehealth-only,
- the public contact email and (optional) phone,
- whether we accept insurance.
Then update index.html, book.html and js/config.js accordingly, add a simple privacy.html page (plain-language privacy
policy covering what the booking form collects, how it is stored in Google Sheets/Drive, and how to request deletion),
link it from the footer of both pages, and re-run the screenshot script from Prompt 1.
```

## Prompt 3 — Set up GitHub (org + Pages + backup mirror)

```
Walk me through docs/SETUP_GUIDE.md Steps 1–6 interactively. Use the GitHub CLI (gh) where possible:
- check `gh auth status`; if not logged in, tell me the exact command to run and wait.
- create the org repo DrTherapyServices/DrTherapyServices.github.io (public) and the personal repo
  digonto10602/DrTherapyServices-backup (private) if they don't exist,
- git init, commit everything, push main to both remotes,
- enable GitHub Pages from branch main / root via `gh api`,
- explain how to create the fine-grained token for the mirror workflow and add it as the BACKUP_TOKEN secret with
  `gh secret set BACKUP_TOKEN --repo DrTherapyServices/DrTherapyServices.github.io`,
- trigger the mirror workflow and confirm the backup repo received the push.
Stop and ask me before any step that costs money or cannot be undone.
```

## Prompt 4 — Connect the Google backend

```
I have created the Google Sheet, pasted backend/Code.gs, run setupSheet(), and deployed the web app. My web-app URL is:
<PASTE URL HERE>
and my SITE_KEY is: <PASTE KEY HERE>
1. Put them into js/config.js.
2. curl "<URL>?action=health" and "<URL>?action=slots&date=<next weekday>&key=<KEY>" and show me the JSON.
3. Send one real test booking with curl (POST JSON, Content-Type text/plain) using my email digonto10602@gmail.com for a
   slot two working days from now at 10:00, then ask me to confirm I received both the client and admin emails and that a
   row appeared in the Bookings tab.
4. Commit and push "Connect booking backend" to origin main and confirm the live page at
   https://drtherapyservices.github.io/book.html is no longer in demo mode (curl the page and check config.js).
```

## Prompt 5 — Later improvements (optional, one per session)

```
Add a second appointment type ("Paid 50-minute session") selectable on book.html, passed to the backend as `service`,
stored in a new "Service" column, and shown in both emails. Keep the free consultation as the default. Update
docs/SETUP_GUIDE.md Step 12 and the CLAUDE.md testing checklist.
```

```
Add an admin-only "cancel" flow: a signed link in the admin email that calls the Apps Script with action=cancel&id=…&token=…
(HMAC of the booking id with SITE_KEY), which sets Status=Cancelled, deletes the Calendar event, and emails the client.
```

```
Add a Zoom option: implement createZoomMeeting_() in Code.gs using a Zoom Server-to-Server OAuth app (account id,
client id, client secret stored in Script Properties, never in code), selectable via SETTINGS.MEETING_PLATFORM.
```
