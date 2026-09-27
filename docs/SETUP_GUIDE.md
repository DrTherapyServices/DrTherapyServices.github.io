# DTS Website — Step-by-Step Setup Guide

This guide takes you from an empty GitHub account to a live booking website at
**https://drtherapyservices.github.io** that emails clients and admins and keeps an
admin-only spreadsheet/CSV of every appointment.

Plain-English glossary (terms are defined the first time they appear):

* **Repository (repo)** — a folder of files that GitHub stores and tracks changes to.
* **Organization (org)** — a GitHub account owned by a business or group rather than one person. Several people can be members.
* **GitHub Pages** — GitHub's free service that turns a repo of HTML files into a public website.
* **Static site** — a website made only of files (HTML, CSS, JavaScript, images). It cannot send email or save data by itself; that is why we add a small backend.
* **Backend** — a program that runs on a server and does the things a static site cannot (send email, create meeting links, save bookings). Ours runs on Google's servers for free using **Google Apps Script**.
* **Google Apps Script** — Google's free scripting service. A script attached to a Google Sheet can send Gmail, create Calendar events with Google Meet links, and write files to Google Drive.
* **Web app URL** — the address Google gives your script so the website can call it.
* **Secret / token** — a password-like string that lets one service act on your behalf. Never paste these into website files.

---

## Architecture in one picture

```
Visitor's phone / PC
   │  opens
   ▼
GitHub Pages  (org: DrTherapyServices → repo: DrTherapyServices.github.io)
   index.html · book.html · css/ · js/ · assets/
   │  book.html sends the booking as JSON to …
   ▼
Google Apps Script web app  (backend/Code.gs, attached to your private Google Sheet)
   ├─ creates a Google Calendar event with a Google Meet link
   ├─ emails the client a confirmation (Meet link, date, time)
   ├─ emails every ACTIVE admin (Admins tab of the sheet)
   ├─ appends a row to the Bookings tab (name, email, phone, link, …)
   └─ re-exports DTS-bookings.csv into a private Drive folder shared only with admins

GitHub Action "Mirror to personal backup" → digonto10602/DrTherapyServices-backup
```

Why Google Meet and not Zoom: a Meet link can be created automatically by Apps Script with
zero extra accounts, keys or cost. Zoom needs a developer app, OAuth credentials and a paid
plan for some features. You can switch later; the site copy reads `MEETING_PLATFORM` from
`js/config.js`.

---

## Step 1 — Create the GitHub organization

1. Sign in to GitHub as **digonto10602**.
2. Click your avatar (top-right) → **Your organizations** → **New organization** → choose **Create a free organization**.
3. Organization account name: **`DrTherapyServices`**
   *Why this name and not `dts`:* an organization's website address is always `<organization-name>.github.io`. To get `DrTherapyServices.github.io` the org itself must be called `DrTherapyServices` (`dts` is almost certainly taken anyway). GitHub addresses are case-insensitive, so `drtherapyservices.github.io` and `DrTherapyServices.github.io` are the same site.
4. Contact email: `digonto10602@gmail.com`. "This organization belongs to": **My personal account**. Finish the wizard (you can skip inviting members).

## Step 2 — Create the website repository in the organization

1. On the org page click **New repository**.
2. Owner: **DrTherapyServices**. Repository name: **`DrTherapyServices.github.io`** (must match exactly — this special name is what makes it the org's main site).
3. Visibility: **Public** (GitHub Pages on free plans requires a public repo).
4. Do **not** add a README/.gitignore (we already have files). Click **Create repository**.

## Step 3 — Create the backup repository under your personal account

1. Go to <https://github.com/new>.
2. Owner: **digonto10602**. Name: **`DrTherapyServices-backup`**. Visibility: Private is fine. Create it empty.

## Step 4 — Put the website files on your laptop and push them

Unzip `dts-website.zip` somewhere convenient (e.g. `~/Projects/dts-website`). Then, in a terminal:

```bash
cd ~/Projects/dts-website
git init -b main
git add .
git commit -m "Initial DTS website"
git remote add origin https://github.com/DrTherapyServices/DrTherapyServices.github.io.git
git remote add backup https://github.com/digonto10602/DrTherapyServices-backup.git
git push -u origin main
git push backup main
```

If Git asks you to log in, use a **personal access token** (GitHub → Settings → Developer settings → Personal access tokens → *Tokens (classic)* → Generate → tick `repo` and `workflow`) as the password, or install the GitHub CLI (`gh auth login`) which handles it for you.

## Step 5 — Turn on GitHub Pages

1. In the org repo, go to **Settings → Pages**.
2. Under **Build and deployment** choose **Source: Deploy from a branch**, Branch: **main**, folder **/ (root)**. Save.
3. Wait 1–2 minutes, then open <https://drtherapyservices.github.io>. The site is live (booking page runs in *demo mode* until Step 7 is done).
4. Optional: **Settings → Pages → Enforce HTTPS** should be ticked.

## Step 6 — Automatic backup mirror (org → personal)

The file `.github/workflows/mirror-backup.yml` copies every push on `main` to the backup repo. It needs permission to push to your personal repo:

1. Create a **fine-grained personal access token**: GitHub → Settings → Developer settings → Personal access tokens → **Fine-grained tokens** → Generate new token.
   Resource owner: `digonto10602`. Repository access: *Only select repositories* → `DrTherapyServices-backup`. Permissions: **Contents → Read and write**. Generate and copy it.
2. In the **org repo** go to **Settings → Secrets and variables → Actions → New repository secret**. Name: `BACKUP_TOKEN`. Value: the token. Save.
3. In the org repo **Settings → Actions → General**, make sure Actions are allowed. Push any commit (or run the workflow from the **Actions** tab → *Mirror to personal backup* → *Run workflow*). The backup repo now mirrors the org repo automatically.

## Step 7 — Set up the Google backend (email + Meet + CSV)

Do this while signed in to Google as **digonto10602@gmail.com** (that account will own the calendar events and send the emails).

1. **Create the Sheet.** Go to <https://sheets.new>. Name it `DTS Bookings`. This spreadsheet IS your admin database — only people it is shared with can open it.
2. **Open the script editor.** Menu **Extensions → Apps Script**. Delete the sample code in `Code.gs`, paste the entire contents of `backend/Code.gs`, and save (💾 or Ctrl/Cmd+S). Name the project `DTS Booking Backend`.
3. **Set the secret.** In `Code.gs` change `SITE_KEY: 'change-me-to-a-long-random-string'` to any long random string (e.g. 32 random letters/numbers). Remember it — you will paste the same value into `js/config.js` in Step 8.
4. **Enable the Calendar service** (needed to create Meet links): in the left sidebar click **Services (+)** → choose **Google Calendar API** → Add. (Alternatively: Project Settings → tick *Show "appsscript.json"* and paste `backend/appsscript.json` over it.)
5. **Run setup.** In the toolbar select the function **`setupSheet`** and press **▶ Run**. Google will ask you to authorize the script (Review permissions → choose your account → *Advanced* → *Go to DTS Booking Backend (unsafe)* → Allow). "Unsafe" only means Google hasn't reviewed your personal script; it is your own code. When it finishes, the Sheet has three tabs: **Bookings**, **Admins** (pre-filled with `digonto10602@gmail.com`), **Log**, and a private Drive folder **DTS Admin (private)** exists.
6. **Deploy as a web app.** Click **Deploy → New deployment** → gear icon → **Web app**. Description `v1`. **Execute as: Me**. **Who has access: Anyone**. Click **Deploy**, authorize again if asked, and **copy the Web app URL** (ends in `/exec`).
   *"Anyone" is required so visitors' browsers can call the script; the `SITE_KEY` check inside the script keeps random callers out, and the script never returns other people's data.*
7. **Sanity check.** Paste `<Web app URL>?action=health` into a browser tab. You should see `{"ok":true,...}`.

## Step 8 — Connect the website to the backend

Edit `js/config.js`:

```js
API_URL: "https://script.google.com/macros/s/AKfycb…/exec",   // from Step 7.6
SITE_KEY: "the-same-long-random-string-you-put-in-Code.gs",
```

Commit and push:

```bash
git add js/config.js && git commit -m "Connect booking backend" && git push origin main
```

Open <https://drtherapyservices.github.io/book.html>, book a test slot with your own email, and confirm that:

* you receive the **client** email with a working Google Meet link,
* you (as admin) receive the **admin** email,
* a row appeared in the **Bookings** tab and `DTS-bookings.csv` in Drive → *DTS Admin (private)*,
* the event with the Meet link is on your Google Calendar,
* going back to the booking page, that slot is now greyed out.

## Step 9 — Managing admins (add / remove)

Open the `DTS Bookings` sheet → **Admins** tab.

* **Add an admin:** add a row with their email, name and `TRUE`. Then menu **DTS Admin → Sync admin access**. They now receive booking notifications and get edit access to the sheet and the private CSV folder.
* **Remove an admin:** set their row to `FALSE` (or delete the row) and run **DTS Admin → Sync admin access** again. Their access to the sheet/folder is revoked and they stop receiving emails.
* The website code never needs to change for this. (Keep it to three admins per your plan — the sheet does not enforce a number, so just don't add more.)

## Step 10 — Every time you change the code

After Apps Script changes you must publish a new version or the live URL keeps running the old code: **Deploy → Manage deployments → ✎ (edit) → Version: New version → Deploy**. The URL stays the same.

Website changes: edit → commit → `git push origin main`. GitHub Pages redeploys in about a minute; the mirror workflow updates the backup.

## Step 11 — Custom domain later (e.g. drtherapyservices.com)

1. Buy the domain (Cloudflare, Namecheap, Porkbun, Google Domains successor Squarespace…).
2. At the DNS provider add: `A` records for the root pointing to `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`, and a `CNAME` record `www → drtherapyservices.github.io`.
3. In the org repo **Settings → Pages → Custom domain** type `www.drtherapyservices.com` → Save. GitHub creates a `CNAME` file in the repo (there is a `CNAME.example` to show what it looks like). Tick **Enforce HTTPS** once the certificate is issued (up to 24 h).
4. Update `SITE_URL` in `Code.gs` and `robots.txt`/`sitemap.xml`. The old `github.io` address keeps redirecting.

## Step 12 — Moving from free consultations to paid services (future)

* `js/config.js` → change `APPOINTMENT_TYPE`, hours, slot length; `Code.gs` `SETTINGS` must match.
* Multiple service types → add a `<select>` to `book.html` and pass `service` in the payload; add a column in `BOOKING_HEADERS`.
* Payments → Stripe Payment Links are the simplest static-site option (no server code): put the link in the confirmation email.
* Zoom instead of Meet → replace `createMeetEvent_()` with a call to Zoom's *Create meeting* API using a Server-to-Server OAuth app; the rest of the pipeline is unchanged.

---

## Privacy, security and compliance notes (please read)

* **Health data / HIPAA.** In the U.S., a provider that bills insurance electronically is usually a *covered entity* under HIPAA, and the booking form collects name, email, phone and free-text notes that may describe health concerns. The free Gmail/Sheets tier does **not** come with a Business Associate Agreement (BAA). Before storing anything clinical, move the Sheet/Script to a **Google Workspace** account with a BAA signed (Google offers one on paid Workspace plans) and keep the notes field short/optional. For a *free consultation request* many practices treat this as pre-intake contact info, but confirm with a compliance professional — this guide is not legal advice.
* **Never claim credentials you don't hold.** The site text mentions BCBAs and licensed clinicians. Edit `index.html` so every claim is true for your actual team before launch (BCBA is a protected credential of the BACB).
* **Add a privacy policy page** before collecting real bookings (required by many state laws and by Google if you ever add analytics).
* **Crisis wording.** The footer already states the site is not for emergencies and lists 911/988. Keep it.
* **Secrets.** `SITE_KEY` in `config.js` is visible to visitors by design; it only deters casual abuse. The real protection is that the script executes as you and only ever writes rows/sends email — it never exposes the sheet.
* **Quotas.** Free Gmail accounts can send ~100 emails/day via Apps Script (each booking sends 2). Plenty for now; Workspace accounts get 1,500/day.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Booking page says **Demo mode** | `API_URL` in `js/config.js` is empty or the file wasn't pushed. |
| `Unauthorized` error when booking | `SITE_KEY` differs between `config.js` and `Code.gs`. |
| `Meet link was not generated` | Enable the **Google Calendar API** advanced service (Step 7.4) and redeploy a new version. |
| Emails not arriving | Check spam; check the **Log** tab; free Gmail daily limit reached; run *DTS Admin → Send test emails*. |
| Changes to Code.gs have no effect | You must create a **New version** in *Manage deployments* (Step 10). |
| Slot shows as taken but sheet row is Cancelled | The script ignores rows whose Status is exactly `Cancelled` — check spelling. |
| GitHub Pages 404 | Repo name must be exactly `DrTherapyServices.github.io`, branch `main`, folder root, and `index.html` at the top level. |
| Site loads without fonts/illustrations locally | Open it through a local server (`python3 -m http.server`) rather than double-clicking the HTML file. |
