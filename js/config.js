/* =========================================================
   DTS site configuration — the ONLY file you must edit to go live.
   ========================================================= */
window.DTS_CONFIG = {
  // 1) Paste the Google Apps Script "Web app" URL here after you deploy backend/Code.gs.
  //    It looks like: https://script.google.com/macros/s/AKfycb.../exec
  //    Leave it empty ("") to run the booking page in DEMO MODE (no emails are sent).
  API_URL: "",

  // 2) A shared secret. Must be IDENTICAL to SITE_KEY inside backend/Code.gs.
  //    (It is visible in the browser, so it only deters casual spam — that is expected.)
  SITE_KEY: "change-me-to-a-long-random-string",

  // 3) Business hours. Slots are generated from START_HOUR to END_HOUR in SLOT_MINUTES steps.
  //    9 -> 17 with 30-minute slots gives 9:00, 9:30, ... 16:30 (the last slot ends at 5:00 pm).
  TIMEZONE: "America/Denver",          // IANA time-zone name used for all bookings
  TIMEZONE_LABEL: "Mountain Time (MT)",
  START_HOUR: 9,
  END_HOUR: 17,
  SLOT_MINUTES: 30,
  WORKING_DAYS: [1, 2, 3, 4, 5],       // 0 = Sunday ... 6 = Saturday
  MIN_NOTICE_HOURS: 12,                // earliest bookable slot is this many hours from now
  MAX_DAYS_AHEAD: 60,                  // how far into the future clients may book

  // 4) Copy shown on the booking page and in emails.
  APPOINTMENT_TYPE: "Free 30-minute consultation",
  MEETING_PLATFORM: "Google Meet",

  // 5) Public contact address shown in the footer (admins are managed in the Google Sheet, not here).
  CONTACT_EMAIL: "digonto10602@gmail.com",
};
