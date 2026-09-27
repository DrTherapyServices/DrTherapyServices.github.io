/**
 * =====================================================================
 *  DTS — Doctor Therapy Services · Booking backend (Google Apps Script)
 * =====================================================================
 *
 *  What this script does when a client books on the website:
 *    1. Checks the slot is still free (with a lock, so two people cannot book the same slot).
 *    2. Creates a Google Calendar event on the admin's calendar WITH a Google Meet link.
 *    3. Emails the client a confirmation (date, time, Meet link).
 *    4. Emails every active admin a notification with the client's details.
 *    5. Appends a row to the "Bookings" tab of this Google Sheet.
 *    6. Re-exports the whole Bookings tab to "DTS-bookings.csv" in the private admin Drive folder.
 *
 *  Admins are managed in the "Admins" tab of the Sheet (email, name, active TRUE/FALSE).
 *  Run  setupSheet()  once from the Apps Script editor to create the tabs.
 *
 *  Deploy:  Deploy > New deployment > Web app
 *           Execute as: Me   ·   Who has access: Anyone
 *  Then paste the web-app URL into js/config.js (API_URL).
 * ---------------------------------------------------------------------
 */

// ------------------------- SETTINGS (edit these) -------------------------
const SETTINGS = {
  SITE_KEY: 'change-me-to-a-long-random-string', // MUST match SITE_KEY in js/config.js
  ORG_NAME: 'Doctor Therapy Services (DTS)',
  TIMEZONE: 'America/Denver',                     // must match js/config.js TIMEZONE
  TIMEZONE_LABEL: 'Mountain Time (MT)',
  SLOT_MINUTES: 30,
  START_HOUR: 9,
  END_HOUR: 17,
  WORKING_DAYS: [1, 2, 3, 4, 5],                  // 0 = Sunday … 6 = Saturday
  MIN_NOTICE_HOURS: 12,
  MAX_DAYS_AHEAD: 60,
  APPOINTMENT_TYPE: 'Free 30-minute consultation',
  CALENDAR_ID: 'primary',                         // or a dedicated calendar's ID (Settings > Integrate calendar)
  ADD_CLIENT_AS_GUEST: true,                      // client sees the event in their own Google Calendar
  REPLY_TO: '',                                   // leave '' to use the first active admin's email
  SITE_URL: 'https://drtherapyservices.github.io',
  ADMIN_FOLDER_NAME: 'DTS Admin (private)',       // Drive folder for the CSV export
  CSV_FILE_NAME: 'DTS-bookings.csv',
  FIRST_ADMIN_EMAIL: 'digonto10602@gmail.com',    // seeded into the Admins tab by setupSheet()
  MAX_BOOKINGS_PER_EMAIL_PER_DAY: 3,              // simple abuse limit
};

const SHEET_BOOKINGS = 'Bookings';
const SHEET_ADMINS = 'Admins';
const SHEET_LOG = 'Log';
const BOOKING_HEADERS = ['Booking ID', 'Created (UTC)', 'Date', 'Start', 'End', 'Timezone', 'Client Name', 'Client Email',
  'Client Phone', 'Notes', 'Meeting Platform', 'Meeting Link', 'Calendar Event ID', 'Status', 'Client Timezone', 'Source Page'];

// ------------------------------ ONE-TIME SETUP ------------------------------
/** Run this once from the Apps Script editor (select the function, press ▶ Run). */
function setupSheet() {
  const ss = SpreadsheetApp.getActive();
  let b = ss.getSheetByName(SHEET_BOOKINGS);
  if (!b) { b = ss.insertSheet(SHEET_BOOKINGS); b.appendRow(BOOKING_HEADERS); b.setFrozenRows(1); b.getRange(1, 1, 1, BOOKING_HEADERS.length).setFontWeight('bold'); }
  let a = ss.getSheetByName(SHEET_ADMINS);
  if (!a) {
    a = ss.insertSheet(SHEET_ADMINS);
    a.appendRow(['Email', 'Name', 'Active (TRUE/FALSE)', 'Notes']);
    a.appendRow([SETTINGS.FIRST_ADMIN_EMAIL, 'Primary admin', true, 'Owner of this sheet']);
    a.setFrozenRows(1); a.getRange(1, 1, 1, 4).setFontWeight('bold');
  }
  let l = ss.getSheetByName(SHEET_LOG);
  if (!l) { l = ss.insertSheet(SHEET_LOG); l.appendRow(['Time (UTC)', 'Level', 'Message']); l.setFrozenRows(1); }
  const def = ss.getSheetByName('Sheet1'); if (def && ss.getSheets().length > 1 && def.getLastRow() === 0) ss.deleteSheet(def);
  getAdminFolder_(); // create the private Drive folder
  syncAdminAccess();
  log_('INFO', 'setupSheet completed');
  SpreadsheetApp.getUi && SpreadsheetApp.getUi().alert('DTS setup complete. Tabs created: Bookings, Admins, Log. Now deploy as a Web app.');
}

/** Adds a "DTS Admin" menu to the Sheet. */
function onOpen() {
  SpreadsheetApp.getUi().createMenu('DTS Admin')
    .addItem('Export bookings to CSV (Drive)', 'exportBookingsCsv')
    .addItem('Sync admin access (share sheet + folder)', 'syncAdminAccess')
    .addItem('Send test emails to admins', 'sendTestEmail')
    .addItem('Run setup again', 'setupSheet')
    .addToUi();
}

// ------------------------------ WEB ENDPOINTS ------------------------------
/** GET  ?action=slots&date=YYYY-MM-DD&key=SITE_KEY  -> {ok, booked:[...]}      GET ?action=health -> {ok} */
function doGet(e) {
  try {
    const p = (e && e.parameter) || {};
    if (p.action === 'health') return json_({ ok: true, service: 'dts-booking', time: new Date().toISOString() });
    if (p.key !== SETTINGS.SITE_KEY) return json_({ ok: false, error: 'Unauthorized' });
    if (p.action === 'slots') {
      if (!/^\d{4}-\d{2}-\d{2}$/.test(p.date || '')) return json_({ ok: false, error: 'Bad date' });
      return json_({ ok: true, date: p.date, booked: bookedTimesFor_(p.date) });
    }
    return json_({ ok: false, error: 'Unknown action' });
  } catch (err) { log_('ERROR', 'doGet: ' + err); return json_({ ok: false, error: String(err.message || err) }); }
}

/** POST JSON body {key,date,time,name,email,phone,notes,website,clientTimezone,page} -> {ok,id,meetLink,eventLink} */
function doPost(e) {
  let data = {};
  try { data = JSON.parse((e && e.postData && e.postData.contents) || '{}'); }
  catch (_) { return json_({ ok: false, error: 'Invalid JSON' }); }

  if (data.key !== SETTINGS.SITE_KEY) return json_({ ok: false, error: 'Unauthorized' });
  if (data.website) { log_('WARN', 'Honeypot tripped from ' + data.email); return json_({ ok: true, id: 'OK' }); } // silently drop bots

  const v = validate_(data);
  if (v) return json_({ ok: false, error: v });

  const lock = LockService.getScriptLock();
  try {
    lock.waitLock(20000);
    if (bookedTimesFor_(data.date).indexOf(data.time) !== -1) return json_({ ok: false, error: 'That slot is no longer available' });
    if (countBookingsBy_(data.email) >= SETTINGS.MAX_BOOKINGS_PER_EMAIL_PER_DAY) return json_({ ok: false, error: 'Too many bookings from this email today' });

    const id = 'DTS-' + Utilities.formatDate(new Date(), 'UTC', 'yyMMdd') + '-' + Math.random().toString(36).slice(2, 6).toUpperCase();
    const end = addMinutes_(data.time, SETTINGS.SLOT_MINUTES);
    const ev = createMeetEvent_(id, data, end);

    // 1) record first (source of truth), 2) then notify
    SpreadsheetApp.getActive().getSheetByName(SHEET_BOOKINGS).appendRow([
      id, new Date().toISOString(), data.date, data.time, end, SETTINGS.TIMEZONE, data.name, data.email, data.phone || '',
      data.notes || '', 'Google Meet', ev.meetLink, ev.eventId, 'Confirmed', data.clientTimezone || '', data.page || '',
    ]);
    SpreadsheetApp.flush();

    const errors = [];
    try { sendClientEmail_(id, data, end, ev); } catch (err) { errors.push('client email: ' + err); }
    try { sendAdminEmail_(id, data, end, ev); } catch (err) { errors.push('admin email: ' + err); }
    try { exportBookingsCsv(); } catch (err) { errors.push('csv: ' + err); }
    if (errors.length) log_('WARN', id + ' partial failures → ' + errors.join(' | '));
    log_('INFO', 'Booked ' + id + ' ' + data.date + ' ' + data.time + ' ' + data.email);

    return json_({ ok: true, id: id, meetLink: ev.meetLink, eventLink: ev.htmlLink, start: data.date + 'T' + data.time, end: data.date + 'T' + end, timezone: SETTINGS.TIMEZONE });
  } catch (err) {
    log_('ERROR', 'doPost: ' + (err.stack || err));
    return json_({ ok: false, error: 'Server error: ' + (err.message || err) });
  } finally { try { lock.releaseLock(); } catch (_) {} }
}

// ------------------------------ CORE HELPERS ------------------------------
function validate_(d) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(d.date || '')) return 'Please choose a valid date';
  if (!/^\d{2}:\d{2}$/.test(d.time || '')) return 'Please choose a valid time';
  d.name = String(d.name || '').trim().slice(0, 120);
  d.email = String(d.email || '').trim().toLowerCase().slice(0, 160);
  d.phone = String(d.phone || '').trim().slice(0, 40);
  d.notes = String(d.notes || '').trim().slice(0, 800);
  if (!d.name) return 'Name is required';
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(d.email)) return 'A valid email address is required';
  if (d.phone && !/^[+()\-.\s\d]{7,25}$/.test(d.phone)) return 'Phone number looks invalid';

  // slot must be on the grid, inside working hours / days, not in the past, not too far out
  const [h, m] = d.time.split(':').map(Number);
  const mins = h * 60 + m;
  if (mins < SETTINGS.START_HOUR * 60 || mins + SETTINGS.SLOT_MINUTES > SETTINGS.END_HOUR * 60 || (mins - SETTINGS.START_HOUR * 60) % SETTINGS.SLOT_MINUTES !== 0) return 'Time is outside business hours';
  const start = localToDate_(d.date, d.time);
  if (isNaN(start.getTime())) return 'Invalid date/time';
  if (SETTINGS.WORKING_DAYS.indexOf(Number(Utilities.formatDate(start, SETTINGS.TIMEZONE, 'u')) % 7) === -1) return 'We are closed on that day';
  const now = new Date();
  if (start.getTime() < now.getTime() + SETTINGS.MIN_NOTICE_HOURS * 3600e3) return 'That time is too soon — please pick a later slot';
  if (start.getTime() > now.getTime() + SETTINGS.MAX_DAYS_AHEAD * 86400e3) return 'That date is too far ahead';
  return '';
}

/** Converts "YYYY-MM-DD" + "HH:mm" in SETTINGS.TIMEZONE into a JS Date (handles daylight-saving correctly). */
function localToDate_(dateStr, timeStr) {
  const guess = new Date(dateStr + 'T' + timeStr + ':00Z');                     // pretend it's UTC
  const offsetMin = tzOffsetMinutes_(guess);                                    // zone offset at that moment
  const corrected = new Date(guess.getTime() - offsetMin * 60000);
  const offset2 = tzOffsetMinutes_(corrected);                                  // re-check across DST edges
  return offset2 === offsetMin ? corrected : new Date(guess.getTime() - offset2 * 60000);
}
function tzOffsetMinutes_(date) {
  const s = Utilities.formatDate(date, SETTINGS.TIMEZONE, 'Z'); // e.g. "-0600"
  const sign = s[0] === '-' ? -1 : 1;
  return sign * (Number(s.slice(1, 3)) * 60 + Number(s.slice(3, 5)));
}
function addMinutes_(hhmm, mins) {
  const [h, m] = hhmm.split(':').map(Number); const t = h * 60 + m + mins;
  return pad_(Math.floor(t / 60)) + ':' + pad_(t % 60);
}
const pad_ = (n) => String(n).padStart(2, '0');

/** Times already booked on a given date (from the sheet; cancelled rows are ignored). */
function bookedTimesFor_(dateStr) {
  const sh = SpreadsheetApp.getActive().getSheetByName(SHEET_BOOKINGS);
  if (!sh || sh.getLastRow() < 2) return [];
  const rows = sh.getRange(2, 1, sh.getLastRow() - 1, BOOKING_HEADERS.length).getValues();
  const out = [];
  rows.forEach((r) => {
    const d = r[2] instanceof Date ? Utilities.formatDate(r[2], SETTINGS.TIMEZONE, 'yyyy-MM-dd') : String(r[2]);
    const t = r[3] instanceof Date ? Utilities.formatDate(r[3], SETTINGS.TIMEZONE, 'HH:mm') : String(r[3]);
    if (d === dateStr && String(r[13]).toLowerCase() !== 'cancelled') out.push(t);
  });
  return out;
}
function countBookingsBy_(email) {
  const sh = SpreadsheetApp.getActive().getSheetByName(SHEET_BOOKINGS);
  if (!sh || sh.getLastRow() < 2) return 0;
  const today = Utilities.formatDate(new Date(), 'UTC', 'yyyy-MM-dd');
  return sh.getRange(2, 1, sh.getLastRow() - 1, BOOKING_HEADERS.length).getValues()
    .filter((r) => String(r[7]).toLowerCase() === email && String(r[1]).slice(0, 10) === today).length;
}

/** Creates the Calendar event with a Google Meet link (needs the "Google Calendar API" advanced service enabled). */
function createMeetEvent_(id, d, end) {
  const startIso = d.date + 'T' + d.time + ':00';
  const endIso = d.date + 'T' + end + ':00';
  const event = {
    summary: SETTINGS.APPOINTMENT_TYPE + ' — ' + d.name,
    description: 'Booking ID: ' + id + '\nClient: ' + d.name + '\nEmail: ' + d.email + '\nPhone: ' + (d.phone || '—') + '\nNotes: ' + (d.notes || '—') + '\n\nBooked via ' + SETTINGS.SITE_URL,
    start: { dateTime: startIso, timeZone: SETTINGS.TIMEZONE },
    end: { dateTime: endIso, timeZone: SETTINGS.TIMEZONE },
    conferenceData: { createRequest: { requestId: id, conferenceSolutionKey: { type: 'hangoutsMeet' } } },
    reminders: { useDefault: false, overrides: [{ method: 'email', minutes: 60 }, { method: 'popup', minutes: 10 }] },
    guestsCanInviteOthers: false, guestsCanSeeOtherGuests: false,
  };
  if (SETTINGS.ADD_CLIENT_AS_GUEST) event.attendees = [{ email: d.email, displayName: d.name }];
  const created = Calendar.Events.insert(event, SETTINGS.CALENDAR_ID, { conferenceDataVersion: 1, sendUpdates: 'none' });
  let meetLink = created.hangoutLink || '';
  if (!meetLink && created.conferenceData && created.conferenceData.entryPoints) {
    const ep = created.conferenceData.entryPoints.filter((x) => x.entryPointType === 'video')[0];
    if (ep) meetLink = ep.uri;
  }
  if (!meetLink) throw new Error('Meet link was not generated — check that the Calendar advanced service is enabled');
  return { eventId: created.id, htmlLink: created.htmlLink, meetLink: meetLink };
}

// ------------------------------ EMAILS ------------------------------
function niceDate_(dateStr) { return Utilities.formatDate(localToDate_(dateStr, '12:00'), SETTINGS.TIMEZONE, 'EEEE, MMMM d, yyyy'); }
function niceTime_(hhmm) { const [h, m] = hhmm.split(':').map(Number); return (((h + 11) % 12) + 1) + ':' + pad_(m) + (h >= 12 ? ' pm' : ' am'); }
function emailShell_(title, bodyHtml) {
  return '<div style="background:#FBF7EE;padding:28px 12px;font-family:Inter,Helvetica,Arial,sans-serif;color:#1C2627">' +
    '<div style="max-width:560px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 8px 30px rgba(0,0,0,.06)">' +
    '<div style="background:#2F5D3C;color:#F4E8CC;padding:22px 26px"><div style="font-size:22px;font-weight:700;letter-spacing:1px">DTS</div><div style="font-size:12px;letter-spacing:2px;text-transform:uppercase;opacity:.85">Doctor Therapy Services</div></div>' +
    '<div style="padding:26px"><h2 style="margin:0 0 12px;font-family:Georgia,serif;font-weight:600;color:#1C2627">' + title + '</h2>' + bodyHtml + '</div>' +
    '<div style="padding:16px 26px;background:#F3ECDD;font-size:12px;color:#6b7474">This message was sent by ' + SETTINGS.ORG_NAME + '. Not for emergencies — call 911 or 988 (U.S.).</div></div></div>';
}
function detailsTable_(id, d, end, ev) {
  const row = (k, v) => '<tr><td style="padding:8px 0;color:#6b7474;width:130px;vertical-align:top">' + k + '</td><td style="padding:8px 0;font-weight:600">' + v + '</td></tr>';
  return '<table style="width:100%;border-collapse:collapse;font-size:15px;border-top:1px solid #eee;border-bottom:1px solid #eee;margin:14px 0">' +
    row('Appointment', SETTINGS.APPOINTMENT_TYPE) + row('Date', niceDate_(d.date)) + row('Time', niceTime_(d.time) + ' – ' + niceTime_(end) + ' ' + SETTINGS.TIMEZONE_LABEL) +
    row('Video link', '<a href="' + ev.meetLink + '" style="color:#B8622B">' + ev.meetLink + '</a>') + row('Booking ID', id) + '</table>';
}
function sendClientEmail_(id, d, end, ev) {
  const html = emailShell_('Your consultation is confirmed',
    '<p>Hi ' + escapeHtml_(d.name.split(' ')[0]) + ',</p><p>Thank you for booking with ' + SETTINGS.ORG_NAME + '. Here are your appointment details:</p>' +
    detailsTable_(id, d, end, ev) +
    '<p style="text-align:center;margin:22px 0"><a href="' + ev.meetLink + '" style="background:#B8622B;color:#fff;text-decoration:none;padding:13px 26px;border-radius:999px;font-weight:600;display:inline-block">Join Google Meet</a></p>' +
    '<p style="font-size:14px;color:#3f4a4b">Join from a phone, tablet or computer — nothing to install. Need to reschedule? Simply reply to this email.</p>');
  MailApp.sendEmail({ to: d.email, subject: 'Confirmed: ' + SETTINGS.APPOINTMENT_TYPE + ' on ' + niceDate_(d.date) + ' at ' + niceTime_(d.time), htmlBody: html,
    name: SETTINGS.ORG_NAME, replyTo: replyTo_() });
}
function sendAdminEmail_(id, d, end, ev) {
  const admins = activeAdminEmails_();
  if (!admins.length) { log_('WARN', 'No active admins — admin email skipped'); return; }
  const html = emailShell_('New consultation booked',
    '<p>A new appointment was booked on the website.</p>' + detailsTable_(id, d, end, ev) +
    '<table style="width:100%;border-collapse:collapse;font-size:15px"><tr><td style="padding:6px 0;color:#6b7474;width:130px">Client</td><td style="padding:6px 0">' + escapeHtml_(d.name) + '</td></tr>' +
    '<tr><td style="padding:6px 0;color:#6b7474">Email</td><td style="padding:6px 0"><a href="mailto:' + d.email + '">' + d.email + '</a></td></tr>' +
    '<tr><td style="padding:6px 0;color:#6b7474">Phone</td><td style="padding:6px 0">' + (escapeHtml_(d.phone) || '—') + '</td></tr>' +
    '<tr><td style="padding:6px 0;color:#6b7474">Notes</td><td style="padding:6px 0">' + (escapeHtml_(d.notes) || '—') + '</td></tr>' +
    '<tr><td style="padding:6px 0;color:#6b7474">Client time zone</td><td style="padding:6px 0">' + escapeHtml_(d.clientTimezone || '—') + '</td></tr></table>' +
    '<p style="margin-top:18px"><a href="' + ev.htmlLink + '" style="color:#B8622B">Open in Google Calendar</a> · <a href="' + SpreadsheetApp.getActive().getUrl() + '" style="color:#B8622B">Open bookings sheet</a></p>');
  MailApp.sendEmail({ to: admins.join(','), subject: '[DTS] New booking: ' + d.name + ' — ' + niceDate_(d.date) + ' ' + niceTime_(d.time), htmlBody: html, name: 'DTS Bookings', replyTo: d.email });
}
function sendTestEmail() {
  const admins = activeAdminEmails_();
  MailApp.sendEmail({ to: admins.join(','), subject: '[DTS] Test email', htmlBody: emailShell_('Email works', '<p>If you can read this, admin notifications are configured correctly. Active admins: ' + admins.join(', ') + '</p>'), name: 'DTS Bookings' });
  SpreadsheetApp.getUi().alert('Test email sent to: ' + admins.join(', '));
}
function replyTo_() { return SETTINGS.REPLY_TO || activeAdminEmails_()[0] || Session.getEffectiveUser().getEmail(); }
function escapeHtml_(s) { return String(s || '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }

// ------------------------------ ADMINS ------------------------------
/** Active admin emails from the Admins tab. Add/remove admins by editing that tab. */
function activeAdminEmails_() {
  const sh = SpreadsheetApp.getActive().getSheetByName(SHEET_ADMINS);
  if (!sh || sh.getLastRow() < 2) return [SETTINGS.FIRST_ADMIN_EMAIL];
  return sh.getRange(2, 1, sh.getLastRow() - 1, 3).getValues()
    .filter((r) => r[0] && String(r[2]).toUpperCase() !== 'FALSE' && r[2] !== false)
    .map((r) => String(r[0]).trim().toLowerCase());
}
/** Shares the Sheet and the private Drive folder with active admins; removes editors that are no longer active (never the owner). */
function syncAdminAccess() {
  const ss = SpreadsheetApp.getActive();
  const admins = activeAdminEmails_();
  const owner = ss.getOwner() ? ss.getOwner().getEmail().toLowerCase() : '';
  const folder = getAdminFolder_();
  [ss, folder].forEach((res) => {
    const editors = res.getEditors().map((u) => u.getEmail().toLowerCase());
    admins.forEach((a) => { if (a !== owner && editors.indexOf(a) === -1) { try { res.addEditor(a); } catch (err) { log_('WARN', 'addEditor ' + a + ': ' + err); } } });
    editors.forEach((e) => { if (e && e !== owner && admins.indexOf(e) === -1) { try { res.removeEditor(e); } catch (err) { log_('WARN', 'removeEditor ' + e + ': ' + err); } } });
  });
  log_('INFO', 'syncAdminAccess: ' + admins.join(', '));
  try { SpreadsheetApp.getUi().alert('Access synced for: ' + admins.join(', ')); } catch (_) {}
}

// ------------------------------ CSV EXPORT ------------------------------
function getAdminFolder_() {
  const props = PropertiesService.getScriptProperties();
  const id = props.getProperty('ADMIN_FOLDER_ID');
  if (id) { try { return DriveApp.getFolderById(id); } catch (_) {} }
  const it = DriveApp.getFoldersByName(SETTINGS.ADMIN_FOLDER_NAME);
  const folder = it.hasNext() ? it.next() : DriveApp.createFolder(SETTINGS.ADMIN_FOLDER_NAME);
  props.setProperty('ADMIN_FOLDER_ID', folder.getId());
  return folder;
}
/** Writes the whole Bookings tab to DTS-bookings.csv inside the private admin folder (overwrites). */
function exportBookingsCsv() {
  const sh = SpreadsheetApp.getActive().getSheetByName(SHEET_BOOKINGS);
  const values = sh.getDataRange().getDisplayValues();
  const csv = values.map((r) => r.map((c) => '"' + String(c).replace(/"/g, '""') + '"').join(',')).join('\r\n');
  const folder = getAdminFolder_();
  const files = folder.getFilesByName(SETTINGS.CSV_FILE_NAME);
  if (files.hasNext()) files.next().setContent(csv);
  else folder.createFile(SETTINGS.CSV_FILE_NAME, csv, MimeType.CSV);
  try { SpreadsheetApp.getUi().alert('CSV updated: ' + SETTINGS.CSV_FILE_NAME + '\nFolder: ' + folder.getUrl()); } catch (_) {}
  return folder.getUrl();
}

// ------------------------------ UTIL ------------------------------
function json_(obj) { return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON); }
function log_(level, msg) {
  try { const sh = SpreadsheetApp.getActive().getSheetByName(SHEET_LOG); if (sh) sh.appendRow([new Date().toISOString(), level, String(msg).slice(0, 5000)]); } catch (_) {}
  console.log(level + ': ' + msg);
}

/** Optional: run from the editor to simulate a booking without the website (uses tomorrow 10:00). */
function testBooking() {
  let t = new Date(Date.now() + 2 * 86400e3);
  while (SETTINGS.WORKING_DAYS.indexOf(Number(Utilities.formatDate(t, SETTINGS.TIMEZONE, 'u')) % 7) === -1) t = new Date(t.getTime() + 86400e3);
  const d = Utilities.formatDate(t, SETTINGS.TIMEZONE, 'yyyy-MM-dd');
  const fake = { postData: { contents: JSON.stringify({ key: SETTINGS.SITE_KEY, date: d, time: '10:00', name: 'Test Client', email: Session.getEffectiveUser().getEmail(), phone: '+1 555 000 1111', notes: 'Test booking from Apps Script editor', clientTimezone: 'America/Denver' }) } };
  console.log(doPost(fake).getContent());
}
