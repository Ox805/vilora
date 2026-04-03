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
4. User clicks link, token validated, verified=TRUE
5. User can now fully access Vilora

Pre-verification access:
- User CAN log in and see the dashboard
- User CANNOT create sessions, send messages, or access any AI features
- A banner prompts them to check their email and verify
- "Resend verification" button available
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
4. Log the user in (they can access limited features)
5. Return success with `{ verified: false }` flag

#### 3.2 Verification Banner

On all authenticated pages, if `email_verified` is false, show a persistent banner:

```
Your email hasn't been verified yet. Please check your inbox for a verification link.
[Resend verification email]
```

**Styling:**
- Yellow/warning background, not dismissable
- Fixed at top of the page (below navbar)
- "Resend" button available (rate limited to once per 5 minutes)

#### 3.3 Feature Gating

Unverified users can:
- Log in
- View the dashboard (empty)
- Access the About Me page
- Access Settings
- Verify their email

Unverified users CANNOT:
- Create sessions
- Send messages
- Use Council
- Use Polish
- Send invites/nudges
- Access the framing assistant

**Implementation:** Add a decorator or check:

```python
def verified_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.email_verified:
            return jsonify({'success': False, 'error': 'Please verify your email first.'}), 403
        return f(*args, **kwargs)
    return decorated
```

Apply to: session creation, message sending, council, polish, frame, invite, nudge endpoints.

#### 3.4 Resend Verification

```
POST /api/resend-verification
```

- Rate limited: once per 5 minutes
- Generates a new token (invalidates the old one)
- Sends a new verification email
- Returns success

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

### Verification Banner

```css
.verification-banner {
    background: #FEFCBF;  /* warm yellow */
    border-bottom: 1px solid #ECC94B;
    padding: 0.75rem 1rem;
    text-align: center;
    font-size: 0.9rem;
    color: #744210;
}
```

Placement: between navbar and main content in `base.html`, conditionally rendered:

```html
{% if current_user.is_authenticated and not current_user.email_verified %}
<div class="verification-banner">
    Your email hasn't been verified yet. Check your inbox for a verification link.
    <button onclick="resendVerification()" class="btn btn-sm" id="resend-btn">Resend</button>
</div>
{% endif %}
```

### Verification Success Page

Simple page with:
- Vilora logo
- "Your email has been verified!"
- "You're all set to start using Vilora."
- "Go to Dashboard" button

### Verification Error Page

- Vilora logo
- "This verification link has expired" (or "is invalid")
- "Resend verification email" button
- "Back to login" link

---

## Success Criteria

| Criteria | Measurement |
|----------|-------------|
| New users receive verification email within 30 seconds | SendGrid delivery time |
| Verification link works correctly | Click link, account verified |
| Unverified users see banner on all pages | Visual inspection |
| Unverified users cannot create sessions | API returns 403 |
| Invite-based registrations auto-verify | No verification email sent for invite joins |
| Resend works with rate limiting | Can resend, but not more than once per 5 minutes |
| Existing users are not affected | All current users marked as verified |

---

## Implementation Order

1. Database migration (add columns, mark existing users as verified)
2. Verification email template in `notifications.py`
3. Registration flow changes (send verification on register)
4. Verification endpoint (`GET /verify-email/<token>`)
5. Verification banner in `base.html`
6. Feature gating (`verified_required` decorator)
7. Resend endpoint with rate limiting
8. Invite auto-verification
9. Testing

---

## Changelog

| Date | Change |
|------|--------|
| 2026-04-03 | Initial creation. Full email verification spec with invite auto-verify. |
