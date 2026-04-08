# Session Activity Notifications

**Created:** April 4, 2026
**Last Updated:** April 8, 2026
**Status:** Implemented
**Dependencies:** SendGrid email infrastructure (implemented), user settings page (implemented), session/messages system (implemented)
**Priority:** High. Group sessions lose momentum when participants don't know there's new activity. This is the #1 engagement gap.
**References:** `notifications.py` (email sending), `templates/settings.html` (user preferences), `models/database.py` (schema), `app.py` (API routes)

---

## Problem Statement

In group mediation sessions, participants have no way to know when the other party has contributed. The only option today is manual nudges (limited to 4 per person, intended for "come back" reminders, not activity alerts). This creates a pattern where:

1. Person A shares their perspective and closes the tab
2. Person B responds 20 minutes later, then also closes the tab
3. Person A has no idea Person B responded. The conversation stalls.
4. Hours or days later, someone manually nudges, or the conversation dies

Vilora needs an automated, respectful notification system that brings people back when the conversation moves forward, without creating noise or pressure in what is already a sensitive context.

---

## Design Principles

1. **Gentle, not urgent.** Mediation is not Slack. Notifications should feel like "the door is open" not "you have 3 unread messages!!!" The tone must match Vilora's calm, supportive voice.

2. **Batched, not per-message.** Never send a notification for every single message. Wait for a quiet period, then send one notification summarizing that there's new activity.

3. **Private.** Never include message content in email or SMS notifications. The other party's words belong in the session, not in a notification preview that might appear on a lock screen.

4. **User-controlled.** Both email and SMS notifications must be individually toggleable in Settings. Users should never feel trapped by notifications they didn't ask for.

5. **Respectful frequency.** Hard caps on notification frequency prevent any scenario where a heated back-and-forth generates a flood of alerts.

---

## Implementation Plan

### 1. Database Schema Changes

#### 1.1 Notification Preferences Table

Create a new `notification_preferences` table rather than overloading `user_memories`:

```sql
CREATE TABLE IF NOT EXISTS notification_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    email_enabled INTEGER DEFAULT 1,
    sms_enabled INTEGER DEFAULT 0,
    phone_number TEXT,
    phone_verified INTEGER DEFAULT 0,
    phone_verification_code TEXT,
    phone_verification_sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

- `email_enabled` defaults to ON (1). Users can turn it off.
- `sms_enabled` defaults to OFF (0). Users must opt in and verify their phone first.
- `phone_number` stored in E.164 format (e.g., `+15551234567`).
- `phone_verified` must be 1 before any SMS is sent.
- `phone_verification_code` is a 6-digit code, cleared after successful verification.

PostgreSQL version uses `SERIAL PRIMARY KEY` and `BOOLEAN` instead of `INTEGER` for boolean fields.

#### 1.2 Activity Tracking Table

Track when each user last viewed each session, so we know what's "new":

```sql
CREATE TABLE IF NOT EXISTS session_last_seen (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES mediation_sessions(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(session_id, user_id)
);
```

Updated every time a user loads messages for a session (on the `GET /api/sessions/<id>/messages` endpoint). Use `INSERT ... ON CONFLICT UPDATE` (SQLite) or `INSERT ... ON CONFLICT ... DO UPDATE` (PostgreSQL).

#### 1.3 Notification Log Table

Prevent duplicate/excessive notifications:

```sql
CREATE TABLE IF NOT EXISTS notification_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    channel TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES mediation_sessions(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

- `channel` is `'email'` or `'sms'`.
- Query this table before sending to enforce frequency caps.

---

### 2. Email Notifications (Smart Digest)

#### 2.1 Trigger Logic

When a message is sent in a group session (`POST /api/sessions/<id>/messages` or `POST /api/sessions/<id>/ask-vilora`), check whether other participants need to be notified:

```
For each other participant in the session:
    1. Skip if participant is "active" (last_seen_at within the last 2 minutes)
    2. Skip if email_enabled is false
    3. Skip if we already sent them an email notification for this session
       in the last 3 hours
    4. Otherwise, schedule a notification with a 15-minute delay
```

The 15-minute delay serves two purposes:
- It batches rapid exchanges into one notification
- It avoids notifying about a message that the participant might see on their own

#### 2.2 Delayed Sending Implementation

**Option A (Recommended for simplicity): Check-on-poll approach**

Instead of background job queues, use a lightweight approach:

- When a message is sent, record the timestamp in a `pending_notifications` table:

```sql
CREATE TABLE IF NOT EXISTS pending_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    target_user_id INTEGER NOT NULL,
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(session_id, target_user_id)
);
```

- Add a periodic check (every 60 seconds) via a simple endpoint or background thread that:
  1. Queries `pending_notifications` where `triggered_at < NOW() - 15 minutes`
  2. For each, checks if the user has since visited the session (compare `last_seen_at` with `triggered_at`). If they have, delete the pending notification -- they already saw it.
  3. For remaining, checks frequency caps and notification preferences
  4. Sends the email, logs it to `notification_log`, deletes from `pending_notifications`

- This can be triggered by a simple `setInterval` in a background thread started on app boot, or by a lightweight cron-style endpoint.

**Option B: Synchronous with delay baked into the message endpoint**

Simpler but less precise: when a message is sent, immediately check if the other participant hasn't been active in 15+ minutes and hasn't been notified in 3+ hours. If both true, send the email right then. No delay/batching, but catches the common case (person left, other person responds later).

Choose Option A for better UX, Option B for faster implementation.

#### 2.3 Email Template

Add `send_activity_email()` to `notifications.py`:

**Subject line:** `New activity in your Vilora session`

**Body:**

```
Hi [Name],

There's been new activity in your session about "[Topic]".

[Other person's name] has shared some thoughts, and the
conversation is ready for your input whenever you are.

No rush -- take your time and respond when you're ready.

[View Session button -> link to session]
```

**Key rules:**
- Never include message content or preview text
- Never say how many messages (avoids pressure)
- Always include "no rush" or similar language
- Keep it brief -- one paragraph max
- Use the same branded template as existing emails (logo, green CTA button, footer)

#### 2.4 Frequency Caps

| Rule | Limit |
|------|-------|
| Minimum time between email notifications for the same session | 3 hours |
| Maximum email notifications per session per day | 4 |
| Maximum total email notifications per user per day (across all sessions) | 8 |
| Never notify if user was active in session within last 2 minutes | -- |

---

### 3. SMS Notifications

#### 3.1 SMS Provider

Use **Twilio** for SMS delivery:

- `TWILIO_ACCOUNT_SID` environment variable
- `TWILIO_AUTH_TOKEN` environment variable
- `TWILIO_PHONE_NUMBER` environment variable (the "from" number)

Add `twilio` to `requirements.txt`.

Create `sms.py` (or add to `notifications.py`):

```python
def send_sms(to_number, body):
    """Send an SMS via Twilio. Returns True on success."""
    from twilio.rest import Client
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
    from_number = os.environ.get('TWILIO_PHONE_NUMBER')

    if not all([account_sid, auth_token, from_number]):
        sys.stderr.write(f"[Vilora] Twilio not configured. SMS to {to_number}: {body}\n")
        return False

    client = Client(account_sid, auth_token)
    message = client.messages.create(
        body=body,
        from_=from_number,
        to=to_number
    )
    return message.status in ('queued', 'sent')
```

#### 3.2 Phone Number Verification Flow

Before any SMS can be sent, the user must verify their phone number. This prevents abuse and ensures deliverability.

**Step 1: User enters phone number in Settings**

The Settings page shows a phone number input (see Section 5). On submit:

```
POST /api/user/notification-preferences
Body: { "sms_enabled": true, "phone_number": "+15551234567" }
```

Server:
1. Validates phone number format (E.164)
2. Generates a random 6-digit verification code
3. Stores the code and `phone_verification_sent_at` in `notification_preferences`
4. Sends SMS: `"Your Vilora verification code is: 123456. It expires in 10 minutes."`
5. Sets `phone_verified = false`, `sms_enabled = false` (not enabled until verified)
6. Returns `{ "success": true, "verification_required": true }`

**Step 2: User enters verification code**

```
POST /api/user/verify-phone
Body: { "code": "123456" }
```

Server:
1. Checks code matches `phone_verification_code`
2. Checks `phone_verification_sent_at` is within 10 minutes
3. If valid: sets `phone_verified = true`, `sms_enabled = true`, clears the code
4. If invalid: returns error, allows retry (max 5 attempts, then require new code)

**Step 3: User can now receive SMS notifications**

If the user later changes their phone number, verification resets and they must re-verify.

#### 3.3 SMS Activity Notification

**Message text (keep under 160 characters for single SMS segment):**

```
Vilora: New activity in your session about "[Topic]". Open when you're ready: [short link]
```

- Use a URL shortener or a short redirect route (e.g., `/s/<session_id>`) to keep the URL short
- Never include message content
- Keep the tone consistent with email: informative, not urgent

#### 3.4 SMS Frequency Caps

SMS is more intrusive than email, so caps are tighter:

| Rule | Limit |
|------|-------|
| Minimum time between SMS for the same session | 6 hours |
| Maximum SMS per session per day | 2 |
| Maximum total SMS per user per day (across all sessions) | 4 |
| Never send SMS if user was active in session within last 5 minutes | -- |

#### 3.5 SMS follows email logic

SMS notifications use the same trigger logic as email (Section 2.1) but with its own frequency caps and the additional requirement that `sms_enabled = true` AND `phone_verified = true`. Both email and SMS can fire for the same activity event (they're independent channels).

---

### 4. Dashboard Unread Indicators

As a lightweight complement to push notifications, show unread status on the dashboard.

#### 4.1 Unread Badge on Session Cards

In `templates/dashboard.html`, when rendering session cards, compare the session's latest message timestamp against the user's `last_seen_at` for that session.

The `GET /api/sessions` endpoint (or a new endpoint) should return an `has_unread` boolean and optionally `unread_count` for each session.

```json
{
    "sessions": [
        {
            "id": 5,
            "topic": "Apartment noise issue",
            "has_unread": true,
            "unread_count": 3,
            ...
        }
    ]
}
```

#### 4.2 Visual Treatment

On session cards with unread activity:
- Show a small green dot indicator next to the session title
- Optionally show "3 new messages" in subtle text below the topic
- The dot/count clears when the user opens the session (which updates `last_seen_at`)

CSS:

```css
.session-unread-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--primary);
    margin-left: 0.5rem;
    vertical-align: middle;
}

.session-unread-count {
    font-size: 0.8rem;
    color: var(--primary);
    margin-top: 0.25rem;
}
```

---

### 5. Settings Page: Notification Preferences

Add a new section to `templates/settings.html` for notification controls, placed at the top of the settings sections (before "What I'm usually looking for") since notification preferences are more immediately actionable.

#### 5.1 UI Design

```
Notifications
How would you like to know when there's new activity in your sessions?

[Toggle] Email notifications
  You'll receive an email when there's new activity in a session you're
  part of. We won't send more than a few per day.
  [Currently sent to: user@example.com]

[Toggle] Text message notifications                           [OFF by default]
  Get a text when there's new activity. Standard messaging rates apply.

  [When toggled ON and no verified number:]
  Phone number: [+1 ___ ___ ____]  [Send Code]

  [After code sent:]
  Enter verification code: [______]  [Verify]

  [After verified:]
  Verified: (555) 123-4567  [Change number]
```

#### 5.2 Toggle Behavior

- **Email toggle ON->OFF:** Immediately saves. Shows brief confirmation.
- **Email toggle OFF->ON:** Immediately saves. No verification needed (email is already verified from signup).
- **SMS toggle OFF->ON:** If no verified phone number, opens the phone number input. Does not enable SMS until verification completes.
- **SMS toggle ON->OFF:** Immediately saves. Phone number is retained (not deleted) so they can re-enable without re-verifying.
- **Change number:** Resets verification. SMS disabled until new number is verified.

#### 5.3 API Endpoints

```
GET  /api/user/notification-preferences
     Returns: { email_enabled, sms_enabled, phone_number (masked), phone_verified }

PUT  /api/user/notification-preferences
     Body: { email_enabled?, sms_enabled?, phone_number? }
     - If phone_number changes, triggers verification flow
     - sms_enabled can only be set to true if phone_verified is true

POST /api/user/verify-phone
     Body: { code }
     - Validates 6-digit code, enables SMS if valid

POST /api/user/resend-phone-code
     - Regenerates and resends verification code
     - Rate limited: 1 per 60 seconds
```

#### 5.4 Phone Number Display

Always mask the phone number in API responses and UI after verification:
- Stored: `+15551234567`
- Displayed: `(555) ***-4567` (show only last 4 digits)

---

### 6. Update `last_seen_at` Tracking

Modify the existing `GET /api/sessions/<session_id>/messages` endpoint in `app.py` to update the user's `last_seen_at` on every call:

```python
# After fetching messages, update last_seen
if _is_postgres():
    _exec(db, """
        INSERT INTO session_last_seen (session_id, user_id, last_seen_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT (session_id, user_id)
        DO UPDATE SET last_seen_at = CURRENT_TIMESTAMP
    """, (session_id, current_user.id))
else:
    _exec(db, """
        INSERT INTO session_last_seen (session_id, user_id, last_seen_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(session_id, user_id)
        DO UPDATE SET last_seen_at = CURRENT_TIMESTAMP
    """, (session_id, current_user.id))
db.commit()
```

Since the client polls every 5 seconds, this gives near-real-time "last active" data. The notification system uses this to avoid notifying users who are currently in the session.

---

### 7. Background Notification Worker

Add a background thread that processes pending notifications. Start it on app boot:

```python
import threading
import time

def notification_worker(app):
    """Background thread that sends pending notifications."""
    while True:
        time.sleep(60)  # Check every 60 seconds
        with app.app_context():
            db = get_db()
            # 1. Find pending notifications older than 15 minutes
            # 2. Check if user has visited since (compare last_seen_at)
            # 3. Check frequency caps
            # 4. Check notification preferences
            # 5. Send email and/or SMS
            # 6. Log to notification_log
            # 7. Delete from pending_notifications

# In app startup:
if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN'):
    worker = threading.Thread(target=notification_worker, args=(app,), daemon=True)
    worker.start()
```

The `WERKZEUG_RUN_MAIN` check prevents the worker from running twice in Flask's debug reloader.

---

### 8. Native App Considerations

A native mobile app (iOS/Android) would be the ideal long-term solution for the "when to check back" problem. Here's how it fits into the notification strategy:

#### 8.1 Why Native Matters for Notifications

- **Push notifications** are the gold standard for mobile re-engagement. They appear on the lock screen, in the notification center, and can be grouped, silenced, or scheduled by the OS. Unlike email (which competes with hundreds of other messages) or SMS (which feels intrusive and costs money per message), push notifications are free, instant, and expected by users.

- **Presence detection** becomes trivial. The app can report when it's foregrounded, giving accurate "is the user currently viewing this session?" data without relying on polling heuristics.

- **Badge counts** on the app icon (the red circle with a number) provide passive awareness without any interruption at all. A user glances at their phone, sees "2" on the Vilora icon, and knows there's activity waiting.

- **Rich notifications** on iOS/Android can include action buttons ("View Session", "Mute for today") directly in the notification, reducing friction to zero.

#### 8.2 Architecture: How a Native App Would Work

The current Vilora backend is already API-driven (all interactions go through `/api/` endpoints), which means a native app could use the exact same API. The notification system would extend as follows:

**Push notification service:**
- Use **Firebase Cloud Messaging (FCM)** for both iOS and Android
- When a user logs in on the native app, register their device token with the server
- Add a `device_tokens` table:

```sql
CREATE TABLE IF NOT EXISTS device_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token TEXT NOT NULL UNIQUE,
    platform TEXT NOT NULL,  -- 'ios', 'android'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

- The background notification worker (Section 7) would add a third channel: after checking email and SMS preferences, also check for registered device tokens and send push notifications via FCM.
- Push notifications would have their own toggle in Settings (default ON for native app users).

**App framework options:**
- **React Native** or **Flutter** for cross-platform (iOS + Android from one codebase). Given Vilora's relatively simple UI (chat interface, dashboard, settings), either would work well.
- **Progressive Web App (PWA)** as an intermediate step: wrap the existing web app with a service worker for offline support and Web Push API for notifications. This is significantly less work than a full native app and provides push notifications on Android (iOS Safari added Web Push support in iOS 16.4+, though it requires the user to "Add to Home Screen" first). PWA could serve as a bridge while a native app is developed.

#### 8.3 How Native App Changes the Notification Strategy

With a native app, the notification hierarchy becomes:

| Channel | Best for | Default | Cost |
|---------|----------|---------|------|
| Push notification (native app) | Real-time, low-friction re-engagement | ON (if app installed) | Free |
| Email digest | Users without the app, or as a fallback | ON | Free (SendGrid) |
| SMS | Users who specifically opt in, no app | OFF | ~$0.01/msg (Twilio) |

Push notifications would largely replace the need for email and SMS for users who have the app installed. The email and SMS systems remain important for:
- Users who haven't installed the app
- Users who have push notifications disabled at the OS level
- First-time invitees who don't have a Vilora account yet (email invite flow)

#### 8.4 PWA as a Near-Term Step

Before investing in a full native app, a PWA approach could deliver 80% of the notification value:

1. Add a `manifest.json` and service worker to the existing web app
2. Prompt users to "Add to Home Screen" (gives app-like icon and full-screen experience)
3. Implement Web Push API for push notifications (works on Chrome, Firefox, Edge, Safari 16.4+)
4. Add a `push_subscriptions` table similar to `device_tokens`
5. The notification worker sends web push in addition to email/SMS

This requires no app store submission, no new codebase, and no React Native/Flutter learning curve. The main limitation is iOS: Web Push only works if the user has added the site to their home screen, and the prompting UX for that is clunky compared to a native app install flow.

#### 8.5 Recommendation

**Short term (now):** Build email + SMS notifications as described in this prompt. These work for all users regardless of device or app installation.

**Medium term (next quarter):** Add PWA support with Web Push notifications. Low effort, covers Android well, provides a stepping stone for iOS.

**Long term (when user base justifies it):** Build a native app with FCM push notifications. This becomes the primary notification channel, with email as fallback for non-app users and SMS as an opt-in premium channel.

---

### 9. Files to Modify

| File | Changes |
|------|---------|
| `models/database.py` | Add `notification_preferences`, `session_last_seen`, `notification_log`, `pending_notifications` tables to `db_init()` |
| `app.py` | Add notification preference endpoints, phone verification endpoints, update `GET /messages` to track `last_seen_at`, add pending notification logic to message send, start background worker |
| `notifications.py` | Add `send_activity_email()` template |
| `sms.py` (new) | Twilio SMS sending: `send_sms()`, `send_verification_sms()`, `send_activity_sms()` |
| `templates/settings.html` | Add notification preferences section with toggles, phone input, verification flow |
| `templates/dashboard.html` | Add unread dot/count indicators to session cards |
| `static/css/style.css` | Styles for notification toggles, phone verification UI, unread indicators |
| `requirements.txt` | Add `twilio` package |

### 10. Environment Variables Required

| Variable | Purpose | Required |
|----------|---------|----------|
| `SENDGRID_API_KEY` | Email delivery (already configured) | Yes (existing) |
| `TWILIO_ACCOUNT_SID` | SMS delivery | Only if SMS enabled |
| `TWILIO_AUTH_TOKEN` | SMS authentication | Only if SMS enabled |
| `TWILIO_PHONE_NUMBER` | SMS sender number | Only if SMS enabled |

SMS functionality should degrade gracefully if Twilio is not configured (log to stderr like SendGrid does, disable SMS toggle in Settings UI).

---

## Implementation Summary

Background notification worker implemented as a daemon thread in app.py, polling every 60 seconds. Email activity alerts sent via SendGrid ("New activity in your Vilora session") with branded template, no message content included. SMS activity alerts sent via Twilio (kept under 160 chars). Frequency capping enforced: 60-minute quiet window per session, 4-hour per-session cap, 6 notifications per day. Generation counter used to prevent race conditions in the notification worker. Notification preferences added to settings page with independent email/SMS toggles. Dashboard unread indicators implemented: green dot and "X new messages" count on session cards. last_seen_at tracking updated per user per session on every message fetch.
