# Email & SMS Notifications — Session Invites, Updates & Alerts

**Created:** March 30, 2026
**Last Updated:** April 17, 2026
**Status:** Implemented
**Dependencies:** SendGrid account, Twilio account (for SMS)
**Priority:** High — Enables invite delivery, engagement, and re-engagement without copy-paste
**Design Reference:** `developer-guides/architecture/design-reference.md`

---

## Problem Statement

Currently, the only way to invite someone to a mediation session is to copy a link and manually paste it into a text, email, or chat. This creates friction, especially for less technical users. There's also no way to notify participants when:
- Someone joins their session
- A new message is posted
- Vilora has chimed in with a mediation response
- A session summary is available

This leads to dead sessions where one party is waiting and the other doesn't know there's activity.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     NOTIFICATION SYSTEM                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  CHANNELS                                                       │
│  ├── Email (SendGrid API)                                       │
│  │   ├── Session invite (branded HTML template)                 │
│  │   ├── Participant joined notification                        │
│  │   ├── New message / Vilora response digest                   │
│  │   ├── Session summary available                              │
│  │   └── Password reset (migrate from Flask-Mail to SendGrid)  │
│  │                                                              │
│  └── SMS (Twilio API) — Optional Phase 2                       │
│      ├── Session invite (short link + brief message)            │
│      └── Activity alerts (configurable)                         │
│                                                                 │
│  INFRASTRUCTURE                                                 │
│  ├── notifications.py — Channel abstraction layer               │
│  ├── templates/email/ — Branded HTML email templates            │
│  ├── Notification preferences (per-user opt-in/out)             │
│  └── Rate limiting / digest batching (avoid spam)               │
│                                                                 │
│  UI INTEGRATION                                                 │
│  ├── Invite modal: email + optional phone input                 │
│  ├── Session room: "Invite" button opens send modal             │
│  ├── User settings: notification preferences                    │
│  └── Dashboard: notification indicators                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Email Invites via SendGrid

**Goal:** Replace copy-paste invite flow with a "Send Invite" form that emails a branded invitation directly from Vilora.

#### 1.1 SendGrid Integration

- Install `sendgrid` Python package (add to `requirements.txt`)
- Add environment variables:
  - `SENDGRID_API_KEY` — API key from SendGrid dashboard
  - `NOTIFICATION_FROM_EMAIL` — sender address (e.g., `notifications@vilora.ai`)
  - `NOTIFICATION_FROM_NAME` — sender display name (e.g., `Vilora`)
- Create `notifications.py` module with:
  - `send_email(to, subject, html_body, text_body=None)` — wrapper around SendGrid API
  - Error handling and logging
  - Dry-run mode for local dev (log instead of send)

#### 1.2 Branded Email Templates

Create HTML email templates that match Vilora's brand identity (see `design-reference.md`):

- **Session Invite**
  - Vilora icon mark in header
  - "{Creator name} has invited you to a mediation session on Vilora"
  - Topic preview
  - Brief explanation of what Vilora is (for first-time recipients)
  - Prominent "Join Session" CTA button (brand teal `#1D9E75`)
  - "What to expect" section — brief, reassuring copy about the process
  - Footer with Vilora tagline

- **Template standards:**
  - Inline CSS (email client compatibility)
  - Plain text fallback for every email
  - Mobile-responsive layout
  - Unsubscribe link (required by CAN-SPAM / SendGrid)

#### 1.3 Invite UI

- Add "Send Invite" button alongside the existing copy-link in the session room invite banner
- Clicking opens a modal with:
  - Email input field (required)
  - Optional personal message textarea (included in the email body)
  - "Send Invite" button
- API endpoint: `POST /api/sessions/<id>/invite`
  - Accepts `{ email, message? }`
  - Validates email format
  - Sends branded invite email with session join link
  - Returns success/error
- Show confirmation toast after sending
- Allow sending multiple invites (for multi-party mediations)

#### 1.4 Migrate Password Reset to SendGrid

- Replace current Flask-Mail SMTP implementation with SendGrid
- Remove Flask-Mail dependency and MAIL_* env vars
- Use the same `send_email()` function from `notifications.py`
- Create branded password reset email template

### Phase 2: Activity Notifications (Email)

**Goal:** Keep participants engaged by notifying them of session activity.

#### 2.1 Notification Events

| Event | Trigger | Recipient | Timing |
|-------|---------|-----------|--------|
| Participant joined | Someone joins via invite link | Session creator | Immediate |
| New message | A participant sends a message | Other participant(s) not currently active | Batched (5-min digest) |
| Vilora responded | Mediator chimes in | All participants not currently active | Batched with messages |
| Summary available | Summary is generated | All participants | Immediate |
| Session inactive | No messages for 48+ hours | All participants | Once |

#### 2.2 Active User Detection

- Track "last seen" timestamp per user per session (updated on message load/send)
- Only send notifications to users who haven't been active in the session for 5+ minutes
- Prevents notifying someone who is actively in the session

#### 2.3 Digest Batching

- Don't send an email for every single message — batch into digests
- After 5 minutes of inactivity from a participant, send one email summarizing new messages:
  - "{N} new messages in your mediation session: {topic}"
  - Preview of latest 2-3 messages
  - "Continue the conversation" CTA button
- Use a background task or simple timestamp check to avoid duplicate sends

#### 2.4 Database Changes

```sql
-- Track notification preferences
CREATE TABLE notification_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    email_invites BOOLEAN DEFAULT TRUE,
    email_activity BOOLEAN DEFAULT TRUE,
    sms_invites BOOLEAN DEFAULT FALSE,
    sms_activity BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
);

-- Track last seen for active user detection
ALTER TABLE session_participants ADD COLUMN last_seen_at TIMESTAMP;

-- Track sent notifications to avoid duplicates
CREATE TABLE notification_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    session_id INTEGER NOT NULL REFERENCES mediation_sessions(id),
    event_type TEXT NOT NULL,
    channel TEXT NOT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 2.5 User Settings UI

- Add notification preferences to user account settings (new page or modal)
- Toggle for each notification type:
  - Email invites (default: on)
  - Email activity updates (default: on)
  - SMS invites (default: off, Phase 3)
  - SMS activity (default: off, Phase 3)

### Phase 3: SMS Notifications via Twilio (Optional)

**Goal:** Allow invite and notification delivery via text message for users who prefer SMS.

#### 3.1 Twilio Integration

- Install `twilio` Python package
- Add environment variables:
  - `TWILIO_ACCOUNT_SID`
  - `TWILIO_AUTH_TOKEN`
  - `TWILIO_PHONE_NUMBER` — sending phone number
- Add to `notifications.py`:
  - `send_sms(to_phone, message)` — wrapper around Twilio API

#### 3.2 SMS Invite Flow

- Add optional phone number field to the invite modal
- SMS message format (keep under 160 chars):
  ```
  {Creator} invited you to a mediation session on Vilora: "{topic}".
  Join here: {short_link}
  ```
- Use a URL shortener or custom short link for the invite URL

#### 3.3 SMS Activity Alerts

- Same digest batching logic as email
- Shorter format: "{N} new messages in your Vilora session. Continue: {link}"
- Respect user preferences (opt-in only for SMS)

#### 3.4 Phone Number Storage

- Add `phone` column to users table (optional, encrypted at rest)
- Phone number input on user profile settings
- Phone verification flow (send code, confirm)

---

## Environment Variables

### Phase 1 (SendGrid)

| Variable | Description | Example |
|----------|-------------|---------|
| `SENDGRID_API_KEY` | SendGrid API key | `SG.xxxx` |
| `NOTIFICATION_FROM_EMAIL` | Sender email address | `notifications@vilora.ai` |
| `NOTIFICATION_FROM_NAME` | Sender display name | `Vilora` |

### Phase 3 (Twilio — Optional)

| Variable | Description | Example |
|----------|-------------|---------|
| `TWILIO_ACCOUNT_SID` | Twilio account SID | `ACxxxx` |
| `TWILIO_AUTH_TOKEN` | Twilio auth token | `xxxx` |
| `TWILIO_PHONE_NUMBER` | Twilio sending number | `+1234567890` |

---

## Success Criteria

| Criteria | Measurement |
|----------|-------------|
| Invite delivery works | Recipient receives branded email within 30 seconds |
| Invite conversion | Recipient can click link and land in session (with login/register) |
| Activity notifications reduce dead sessions | Sessions with notifications have higher 2nd-party response rate |
| Users can control notifications | Preferences UI works; opted-out users receive no notifications |
| No spam | Digest batching prevents more than 1 email per 5-minute window per session |
| SMS delivery (Phase 3) | SMS arrives within 60 seconds, link works |

---

## Security & Privacy Considerations

- Email addresses entered for invites are used only for that invite — not stored or added to marketing lists
- Invite emails do not reveal the session topic or perspectives — only that they've been invited
- SMS phone numbers are stored encrypted and only used for notifications the user opted into
- All notification emails include an unsubscribe mechanism
- Rate limit invite sends (max 5 per session per hour) to prevent abuse

---

## References

- **Design Reference:** `developer-guides/architecture/design-reference.md` — Brand colors, logo marks for email templates
- **Deployment Guide:** `developer-guides/architecture/railway-app-deployment-guide.md` — How to add env vars
- **Current Email Setup:** SendGrid (migrated from Flask-Mail/Gmail SMTP on April 1, 2026)
- **SendGrid Docs:** https://docs.sendgrid.com/for-developers/sending-email/api-getting-started
- **Twilio Docs:** https://www.twilio.com/docs/sms/quickstart/python

---

## SendGrid Setup Notes

- **Account:** Set up via Google Cloud Marketplace (not SendGrid directly). Login, billing handled through GCP.
- **API Key:** Stored in Railway env var `SENDGRID_API_KEY`. Generated from SendGrid dashboard > Settings > API Keys.
- **Current sender:** `support@maiatech.ai` — domain `maiatech.ai` authenticated in SendGrid.
- **Domain authentication DNS records (in GoDaddy for maiatech.ai):**
  - CNAME: `em1620` → `u54268949.wl200.sendgrid.net`
  - CNAME: `s1._domainkey` → `s1.domainkey.u54268949.wl200.sendgrid.net`
  - CNAME: `s2._domainkey` → `s2.domainkey.u54268949.wl200.sendgrid.net`
  - TXT: `_dmarc` → `v=DMARC1; p=none;`
- **Future:** When ready to send from `@vilora.ai`, add a new authenticated domain in SendGrid for `vilora.ai` and update `NOTIFICATION_FROM_EMAIL` env var. SendGrid supports multiple authenticated domains.
- **`edgeview.ai`** is also verified in the same SendGrid account (used by another project).

---

## Changelog

| Date | Change |
|------|--------|
| 2026-03-30 | Initial creation — email invites, activity notifications, SMS (phased) |
| 2026-04-01 | Phase 1 implemented — SendGrid integration, branded invite emails, password reset migrated from Flask-Mail |
| 2026-04-02 | SendGrid account set up via GCP Marketplace, maiatech.ai domain authentication in progress |
| 2026-04-08 | Status updated to Implemented |
| 2026-04-13 | Notification outage investigation began -- emails stopped being delivered |
| 2026-04-13 | Added `get_worker_db()` to fix DB connection leak in background thread |
| 2026-04-13 | Added `PYTHONUNBUFFERED=1` to Railway env vars (required for daemon thread log visibility) |
| 2026-04-13 | Added diagnostic logging throughout notification pipeline |
| 2026-04-13 | Added `/api/admin/notification-diagnostics` endpoint |
| 2026-04-17 | Confirmed notifications working end-to-end after full diagnosis |
| 2026-04-17 | Dashboard now polls every 30s for unread updates (was load-once only) |
| 2026-04-17 | Replaced 8px green dot with numbered unread badge |

---

## Implementation Summary

Full email notification system implemented via SendGrid: session invites, password reset (migrated from Flask-Mail), activity alerts, email verification, and nudges. Full SMS notification system implemented via Twilio: phone verification with 6-digit codes (10-minute expiry), activity alerts. Background notification worker runs as a daemon thread with 60-second polling interval. Frequency capping enforced: 60-minute quiet window per session, 4-hour per-session cap, 6 notifications per day. Notification preferences UI added to settings page with independent email/SMS toggles.

---

## Notification Outage: April 8-17, 2026

### Timeline

- **April 5-8:** Notifications working normally. Emails delivered for sessions 16, 18, 20.
- **April 8:** Last successful email notification (session 16 to user 9).
- **April 9:** Railway deployment restarted. Worker started, sent one queued email (session 21), then produced no further visible output.
- **April 12-13:** User reported not receiving email for session 21 despite 10+ hours of inactivity. Investigation began.
- **April 13:** Initial fixes deployed (DB connection, logging). Worker appeared healthy but found 0 pending notifications. Issue declared "instrumented" but not confirmed fixed.
- **April 16:** Message posted to session 16 (POST returned 200). No email sent. No queue log visible.
- **April 17:** Full diagnosis via `/api/admin/notification-diagnostics`. Confirmed session 16 is mediation mode with 2 participants. Deployed fix, user posted test message, notification queued, email delivered at 17:58 UTC.

### Root Causes

**1. `PYTHONUNBUFFERED=1` missing from Railway environment**

This was the primary issue blocking diagnosis. Without this env var, Python buffers stdout/stderr in non-interactive mode (containers). The gunicorn master process flushes output during startup, so boot-time messages appeared. But the daemon thread's `sys.stderr.write()` and `logging` output sat in an unflushed buffer indefinitely. This made the notification worker completely invisible in Railway deploy logs -- no heartbeats, no errors, no success messages. The worker could have been running fine, crashing every cycle, or dead, and there was no way to tell.

**Key lesson:** Always set `PYTHONUNBUFFERED=1` in Railway (or any containerized Python deployment) when using background threads.

**2. DB connection leak via Flask's `g` object**

The original `process_pending_notifications()` used `get_db()` inside `with app.app_context()`. `get_db()` stores connections in Flask's request-scoped `g` object. In a background thread:
- Each call created a new `app_context()` and a new DB connection
- When the context exited, `g` was torn down but the connection was NOT closed (no `teardown_appcontext` handler)
- Over days of running every 60 seconds, this leaked thousands of Postgres connections
- Eventually Postgres would reject new connections (`max_connections` exceeded)

**Fix:** Created `get_worker_db()` in `models/database.py` that creates a standalone connection not tied to Flask's `g`. The worker opens a connection, does its work, and closes it in a `finally` block every cycle.

**3. Silent exception swallowing in `queue_pending_notifications`**

The original inner exception handler was:
```python
except Exception:
    db.rollback()
```

No logging. If the INSERT into `pending_notifications` failed for any reason (connection issue, constraint violation, transaction state), the error was silently swallowed. The notification was never queued and there was no trace of the failure.

**Fix:** Added `logger.error()` to all exception handlers in the notification pipeline.

**4. Dashboard never refreshed unread counts**

`loadSessions()` was called once on page load and never again. If a message arrived while the user was on the dashboard, the unread badge would not appear until a manual page refresh. Users perceived this as "in-app notifications not working."

**Fix:** Added `setInterval(loadSessions, 30000)` to poll every 30 seconds.

**5. Unread indicator too subtle**

The original indicator was an 8px green dot next to the session type badge -- easy to miss.

**Fix:** Replaced with a numbered badge (white text on green pill showing the count, e.g., "3") and added a green background tint to session cards with unread messages.

### What Made This Hard to Diagnose

1. **No observability into the worker.** Without `PYTHONUNBUFFERED`, the daemon thread was a black box. The worker could run for days with zero log output.
2. **Railway deploy log retention is limited.** Even after fixing the buffering, verbose worker logs ("Connecting.../Connected..." every 60 seconds) filled Railway's log retention and pushed out the actual notification events. This made it appear that notifications were never queued when they may have been.
3. **Multiple interacting failure modes.** The buffering issue, DB leak, silent exceptions, and dashboard polling were all contributing simultaneously. Fixing one didn't visibly improve things because the others masked it.
4. **60-minute processing delay.** The notification system intentionally waits 60 minutes before sending. This meant every test required waiting an hour for results, making iterative debugging very slow.
5. **`last_seen_at` skip logic.** If the user visits the session at any point between message posting and the 60-minute processing window, the notification is silently cancelled. This is working as designed but makes testing tricky -- you must stay out of the session for a full hour.

### Diagnostic Tools Added

**`/api/admin/notification-diagnostics`** (login required) returns:
- `worker_state`: cycle count, last run timestamp, last error, last result
- `pending_notifications`: all currently queued notifications
- `recent_notification_log`: last 20 sent notifications with user details
- `sessions`: all sessions with mode, participant count, `last_seen_at`, latest message timestamp

**Logging throughout the pipeline:**
- `[Notify] Queued: session=X target_user=Y sender=Z` -- when notification is inserted
- `[Notify] FAILED to queue: ...` -- when INSERT fails
- `[Notify] Processing N pending notification(s)` -- when worker finds work
- `[Notify] Skipped ... visited since trigger` -- when user already saw it
- `[Notify] Sending email: ...` / `Email sent successfully` / `Email send FAILED`
- `[Notify] Skipped email: daily cap / session cap / email_enabled=False`

### Checklist for Future Notification Issues

If notifications stop working again:

1. **Check `/api/admin/notification-diagnostics`** (while logged in). Look at:
   - `worker_state.cycle` -- is it advancing? If stuck at 0, worker never started.
   - `worker_state.last_run` -- is it recent? If stale, worker thread died.
   - `worker_state.last_error` -- any crash message?
   - `pending_notifications` -- are notifications queued but not processed?
   - `recent_notification_log` -- when was the last email sent?

2. **Check Railway deploy logs** (`railway logs --filter "Notify"`). Look for:
   - "Queued" entries when messages are posted
   - "Processing" entries from the worker
   - "Skipped" entries explaining why notifications were not sent
   - Error/crash entries

3. **Check the session mode.** Personal-mode sessions (`session_mode = 'personal'`) never queue notifications. This is by design.

4. **Check `PYTHONUNBUFFERED=1`** is set in Railway env vars. Without it, daemon thread output is invisible.

5. **Check `SENDGRID_API_KEY`** is set. Without it, emails log to stderr instead of sending (graceful degradation, but no actual delivery).

6. **Remember the 60-minute delay.** Notifications are not sent until 60 minutes after `triggered_at`. If the user visits the session during that window, the notification is cancelled. Each new message resets the 60-minute clock.

7. **Check frequency caps.** Max 1 email per 4 hours per session, max 6 emails per 24 hours per user. Check `notification_log` timestamps to see if caps were hit.
