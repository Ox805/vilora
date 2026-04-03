# Email Verification on Registration

**Created:** April 3, 2026
**Status:** Planning
**Dependencies:** SendGrid (implemented), user authentication (implemented)
**Priority:** High. Prevents fake accounts, spam, and ensures nudge/invite emails reach real inboxes.
**References:** `application-architecture.md`, `EMAIL_AND_SMS_NOTIFICATIONS_PROMPT.md`

---

## Problem Statement

Currently, anyone can register with any email address and immediately access all Vilora features. There is no verification that the user actually owns the email they registered with. This creates several problems:

1. **Fake accounts** can be created with made-up emails, cluttering the system
2. **Typos in emails** go undetected, meaning password resets and nudges will never reach the user
3. **Impersonation** is possible by registering with someone else's email
4. **Deliverability risk** with SendGrid. Sending to invalid/unverified addresses increases bounce rates, which can damage the sender reputation for `support@maiatech.ai`
5. **Invite flow gap**: When someone receives an invite and registers, we should confirm they own the email the invite was sent to

---

## Architecture Overview

```
Registration Flow (New):

1. User submits email + password + display name
2. Account created with verified=FALSE
3. Verification email sent via SendGrid with a secure token link
4. User is NOT logged in. Redirected to a "Verify your email" page.
5. User clicks link in email, token validated, verified=TRUE
6. User is logged in and redirected to dashboard

Pre-verification access (hard block):
- User CANNOT log in or access any authenticated pages
- "Verify your email" page shows with a "Resend" button
- Public pages remain accessible: homepage, login, invite landing

Exception: Invite-based registration auto-verifies (see Phase 4)
```

---

## Implementation Plan

### Phase 1: Database Changes

#### 1.1 Add `verified` Column to Users Table

```sql
-- PostgreSQL
ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN verification_token TEXT;
ALTER TABLE users ADD COLUMN verification_sent_at TIMESTAMP;

-- SQLite
ALTER TABLE users ADD COLUMN email_verified INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN verification_token TEXT;
ALTER TABLE users ADD COLUMN verification_sent_at TIMESTAMP;
```

**Migration note:** Existing users should be marked as verified (`email_verified = TRUE`) since they've already been using the platform. New registrations start unverified.

#### 1.2 Add to `db_init` Statements

Add the columns in both PostgreSQL and SQLite init paths, plus a migration for existing deployments:

```python
# Migration
migrations = [
    "ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT FALSE",
    "ALTER TABLE users ADD COLUMN verification_token TEXT",
    "ALTER TABLE users ADD COLUMN verification_sent_at TIMESTAMP",
    "UPDATE users SET email_verified = TRUE WHERE email_verified IS NULL",  # existing users
]
```

### Phase 2: Verification Email

#### 2.1 Email Template

Add `send_verification_email()` to `notifications.py`:

**Subject:** Verify your email for Vilora

**Body:**
- Vilora logo
- "Welcome to Vilora! Please verify your email to get started."
- Prominent "Verify my email" CTA button (brand teal)
- "Or copy this link: {verification_url}"
- "This link expires in 24 hours."
- Footer with tagline

**Token format:** `secrets.token_urlsafe(32)`, stored in `verification_token` column. Expires after 24 hours (check `verification_sent_at`).

#### 2.2 Verification Endpoint

```
GET /verify-email/<token>
```

- Looks up user by `verification_token`
- Checks `verification_sent_at` is within 24 hours
- Sets `email_verified = TRUE`, clears `verification_token`
- Redirects to dashboard with a success message
- If token is invalid/expired, shows error page with "Resend verification" link

### Phase 3: Registration Flow Changes

#### 3.1 Update Registration API

`POST /api/register`:
1. Create user with `email_verified = FALSE`
2. Generate verification token, store in DB
3. Send verification email
4. Do NOT log the user in
5. Return `{ success: true, needs_verification: true }`

#### 3.2 Update Login API

`POST /api/login`:
1. Validate credentials as normal
2. If `email_verified` is false, do NOT log in
3. Return `{ success: false, needs_verification: true, error: 'Please verify your email first.' }`
4. Frontend redirects to the verification pending page

#### 3.3 Verification Pending Page

`GET /verify-pending`

A dedicated page shown after registration and when unverified users try to log in:

- Vilora logo
- "Check your email to get started"
- "We sent a verification link to [email]. Click the link to verify your account and start using Vilora."
- "Resend verification email" button (rate limited to once per 5 minutes)
- "Back to login" link
- "Didn't receive it? Check your spam folder."

**Note:** The email address is passed via query parameter or session, not stored client-side.

#### 3.4 Resend Verification

```
POST /api/resend-verification
```

- Accepts `{ email }`
- Rate limited: once per 5 minutes (check `verification_sent_at`)
- Generates a new token (invalidates the old one)
- Sends a new verification email
- Always returns success (no email enumeration)

### Phase 4: Invite Flow Integration

#### 4.1 Auto-Verify on Invite Join

When a user registers via an invite link and the invite was sent to their email:
- Automatically mark them as verified (the invite proves email ownership)
- Skip the verification email entirely
- They go straight into the session

**Logic:**
```python
# In register endpoint, after creating user:
pending_join = session.get('pending_join')
if pending_join:
    med_session = MediationSession.get_by_invite_code(db, pending_join)
    if med_session:
        # Check if this email was invited
        invite = db.execute("SELECT * FROM session_invites WHERE session_id = ? AND email = ?",
                           (med_session.id, email)).fetchone()
        if invite:
            # Auto-verify: the invite proves they own this email
            user.email_verified = True
```

#### 4.2 Existing User Joins via Invite

If an already-verified user clicks an invite link, no change needed. If an unverified user clicks an invite link that matches their email, auto-verify them.

### Phase 5: Edge Cases

#### 5.1 Email Change

If/when email change is supported in the future:
- Changing email resets `email_verified` to false
- Sends a new verification email to the new address
- Old email remains active until new one is verified

#### 5.2 Multiple Verification Requests

- Each "Resend" generates a new token, invalidating the previous one
- Only the most recent token works
- Rate limited to prevent abuse

#### 5.3 Expired Tokens

- Tokens expire after 24 hours
- Clicking an expired link shows a clear message: "This verification link has expired."
- "Resend verification" button on the error page
- User can also resend from the dashboard banner

#### 5.4 Already Verified

- Clicking a verification link when already verified shows: "Your email is already verified." with a link to the dashboard
- No error, just a friendly confirmation

---

## Environment Variables

No new environment variables needed. Uses existing SendGrid setup.

---

## Security Considerations

- Verification tokens are cryptographically random (`secrets.token_urlsafe(32)`)
- Tokens expire after 24 hours
- Tokens are single-use (cleared after verification)
- Rate limiting on resend prevents abuse
- Auto-verification via invite requires exact email match
- No information leakage: registration always succeeds regardless of whether email exists (same as current behavior)

---

## UI Specifications

### Verification Pending Page (`/verify-pending`)

Centered card layout (similar to login page):
- Vilora logo at top
- "Check your email to get started"
- "We sent a verification link to **[email]**."
- "Click the link to verify your account and start using Vilora."
- [Resend verification email] button
- "Didn't receive it? Check your spam folder."
- "Back to login" link

### Verification Success Page (`/verify-email/<token>` on success)

Simple centered page:
- Vilora logo
- "Your email has been verified!"
- "You're all set to start using Vilora."
- [Go to Dashboard] button (logs user in automatically)

### Verification Error Page (`/verify-email/<token>` on failure)

- Vilora logo
- "This verification link has expired" (or "is invalid")
- [Resend verification email] button
- "Back to login" link

---

## Success Criteria

| Criteria | Measurement |
|----------|-------------|
| New users receive verification email within 30 seconds | SendGrid delivery time |
| Verification link works correctly | Click link, account verified, auto-logged in |
| Unverified users cannot log in | Login returns needs_verification, redirects to pending page |
| Unverified users cannot access any authenticated pages | All @login_required pages blocked |
| Invite-based registrations auto-verify | No verification email sent for invite joins |
| Resend works with rate limiting | Can resend, but not more than once per 5 minutes |
| Existing users are not affected | All current users marked as verified |

---

## Implementation Order

1. Database migration (add columns, mark existing users as verified)
2. Verification email template in `notifications.py`
3. Registration flow changes (send verification, don't log in)
4. Login flow changes (block unverified users)
5. Verification pending page (`/verify-pending`)
6. Verification endpoint (`GET /verify-email/<token>`, auto-login on success)
7. Resend endpoint with rate limiting
8. Invite auto-verification
9. Testing

---

## Changelog

| Date | Change |
|------|--------|
| 2026-04-03 | Initial creation. Full email verification spec with invite auto-verify. |
