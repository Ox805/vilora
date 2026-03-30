# Email & SMS Notifications — Session Invites, Updates & Alerts

**Created:** March 30, 2026
**Status:** Planning
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
- **Current Email Setup:** Password reset currently uses Flask-Mail with Gmail SMTP; Phase 1.4 migrates to SendGrid
- **SendGrid Docs:** https://docs.sendgrid.com/for-developers/sending-email/api-getting-started
- **Twilio Docs:** https://www.twilio.com/docs/sms/quickstart/python

---

## Changelog

| Date | Change |
|------|--------|
| 2026-03-30 | Initial creation — email invites, activity notifications, SMS (phased) |
