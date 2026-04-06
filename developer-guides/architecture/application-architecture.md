# Vilora Application Architecture

**Date Created:** 2026-04-02
**Date Updated:** 2026-04-02

## Overview

Vilora is an AI-powered mediation and counseling platform that helps people work through disagreements, conflicts, and personal challenges with an impartial AI facilitator. It supports two modes: multi-party mediation (with invite links) and one-on-one personal counseling.

**Live URL:** https://www.vilora.ai
**Alternate URL:** https://www.vilora.io (also active)
**Domain Registrar:** GoDaddy (vilora.ai, vilora.io)
**Tagline:** Strength through dialogue

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3, Flask |
| Authentication | Flask-Login, Werkzeug (password hashing) |
| Database (local) | SQLite |
| Database (prod) | PostgreSQL (Railway add-on) |
| Frontend | Vanilla JavaScript, HTML5 (Jinja2 templates), CSS3 |
| AI | Anthropic Claude API (`claude-sonnet-4-20250514`) |
| Email | SendGrid API (branded HTML emails) |
| Hosting | Railway (auto-deploys from GitHub on push to main) |
| WSGI Server | Gunicorn |
| Font | Jost (Google Fonts, weights 300/400/500) |
| Source Control | GitHub (`Ox805/vilora`) |

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser (Frontend)                       │
│  ┌──────────────┐  ┌──────────┐  ┌────────────────────────────┐  │
│  │  Templates   │  │ style.css│  │  JavaScript                │  │
│  │  (Jinja2)    │  │          │  │  - api.js (auth/logout)    │  │
│  │  - base.html │  │          │  │  - voice.js (speech input) │  │
│  │  - session   │  │          │  │  - inline scripts per page │  │
│  │  - dashboard │  │          │  │                            │  │
│  │  - about_me  │  │          │  │                            │  │
│  └──────────────┘  └──────────┘  └───────────┬────────────────┘  │
│                                               │                  │
└───────────────────────────────────────────────┼──────────────────┘
                                                │ HTTP/JSON
┌───────────────────────────────────────────────┼──────────────────┐
│                      Flask Server (app.py)     │                  │
│  ┌────────────────────────────────────────────┴───────────────┐  │
│  │                     API Endpoints                          │  │
│  │  Auth: /api/login, /api/register, /api/logout              │  │
│  │  Password: /api/forgot-password, /api/reset-password       │  │
│  │  Sessions: /api/sessions (GET/POST), /api/sessions/:id     │  │
│  │  Messages: /api/sessions/:id/messages (GET/POST)           │  │
│  │  Invite: /api/sessions/:id/invite                          │  │
│  │  Participants: /api/sessions/:id/participants              │  │
│  │  Summary: /api/sessions/:id/summary                        │  │
│  │  Framing: /api/frame                                       │  │
│  │  Memories: /api/user/memories (GET/POST/PUT/DELETE)         │  │
│  └────────────────────────────────────────────┬───────────────┘  │
│                                                │                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌┴────────────────┐ │
│  │ Mediation Engine │  │  Notifications   │  │    Database     │ │
│  │ (Claude API)     │  │  (SendGrid)      │  │ (SQLite/PG)    │ │
│  │ - mediate()      │  │  - invite email  │  │ - users        │ │
│  │ - welcome()      │  │  - pw reset      │  │ - sessions     │ │
│  │ - frame()        │  │                  │  │ - messages     │ │
│  │ - summarize()    │  │                  │  │ - memories     │ │
│  │ - extract_mem()  │  │                  │  │ - summaries    │ │
│  │ - should_resp()  │  │                  │  │ - pw_resets    │ │
│  │ - generate_title │  │                  │  │                │ │
│  └──────────────────┘  └──────────────────┘  └────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
vilora/
├── app.py                          # Flask server, all routes, session management
├── Procfile                        # Gunicorn entry point for Railway
├── requirements.txt                # Python dependencies
├── notifications.py                # SendGrid email wrapper (invite, password reset)
├── mediation/                      # AI mediation engine
│   ├── __init__.py
│   ├── engine.py                   # MediationEngine class (Claude API integration)
│   └── frameworks.py               # Dispute-type-specific prompt context
├── models/                         # Data models
│   ├── __init__.py
│   └── database.py                 # SQLite/PostgreSQL dual-mode DB, User, Session, Message
├── static/
│   ├── css/
│   │   └── style.css               # All application styles
│   ├── js/
│   │   ├── api.js                  # Shared API utilities (logout)
│   │   └── voice.js                # Web Speech API voice input
│   └── img/
│       ├── favicon.svg             # Vilora icon mark (SVG)
│       └── email-logo.png          # Horizontal lockup for email templates
├── templates/
│   ├── base.html                   # Base layout (navbar, footer, head tags)
│   ├── landing.html                # Public landing page
│   ├── login.html                  # Login/register (tabbed)
│   ├── forgot_password.html        # Forgot password email form
│   ├── reset_password.html         # Reset password form (token-validated)
│   ├── dashboard.html              # Session list, new session creation flows
│   ├── session.html                # Mediation/counseling room (chat interface)
│   ├── about_me.html               # User memory viewer, onboarding questionnaire
│   ├── settings.html               # User preferences
│   └── error.html                  # Error page
├── scripts/
│   └── test_mediation.py           # Simulates a full mediation between test users
├── tests/
│   └── __init__.py
├── developer-guides/
│   ├── architecture/
│   │   ├── application-architecture.md    # This file
│   │   ├── design-reference.md            # Brand identity, colors, typography, logo specs
│   │   └── railway-app-deployment-guide.md # Deployment & auth system setup guide
│   └── prompts/
│       ├── EMAIL_AND_SMS_NOTIFICATIONS_PROMPT.md  # Email/SMS notification system spec
│       └── USER_MEMORY_AND_PERSONALIZATION_PROMPT.md # User memory & personalization spec
├── CLAUDE.md                       # Claude Code permissions
├── .env                            # Local env vars (gitignored)
└── .gitignore
```

## Backend Components

### Flask Server (`app.py`)

The main entry point that:
- Serves all HTML pages via Jinja2 templates
- Provides REST API endpoints for all functionality
- Manages authentication via Flask-Login
- Coordinates between the mediation engine, database, and notification system

### Mediation Engine (`mediation/engine.py`)

`MediationEngine` class — all AI interactions go through this module.

| Method | Purpose |
|--------|---------|
| `frame(raw_text, user_memories)` | Parses free-form user input into structured session fields (topic, type, perspective). Returns JSON. |
| `generate_title(text)` | Creates a concise session title from long user input (for personal sessions). |
| `welcome(topic, ..., session_mode)` | Generates initial response when a session is created. Mediation mode reminds about invites; personal mode responds warmly. |
| `should_respond(topic, messages, participants, session_mode)` | Decides if Vilora should chime in. Always responds in personal mode. In mediation mode, uses heuristics + AI judgment based on conversation state. |
| `mediate(topic, ..., participant_memories, session_mode)` | Generates a mediator/counselor response. Injects user memories into the system prompt for personalization. Uses `SYSTEM_PROMPT` for mediation, `COUNSELOR_PROMPT` for personal. |
| `summarize(topic, messages, participants)` | Generates a structured session summary (concerns, agreements, unresolved issues, next steps). |
| `extract_memories(user_name, ..., existing_memories)` | Post-session AI extraction of user insights (profile, communication style, patterns, preferences). Returns JSON array. |
| `_build_memory_context(user_memories)` | Formats memories for inclusion in system prompts. |
| `_build_conversation(topic, ..., session_mode)` | Constructs the Claude API message history from session messages. |

**System Prompts:**
- `SYSTEM_PROMPT` — Mediation mode: impartial facilitator, reframing, de-escalation, structured progress
- `COUNSELOR_PROMPT` — Personal mode: warm advisor, honest guidance, practical wisdom, like a thoughtful friend
- `SHOULD_RESPOND_PROMPT` — Decision prompt for when to chime in during mediation

### Mediation Frameworks (`mediation/frameworks.py`)

Provides additional system prompt context tailored to specific dispute types:

| Type | Focus |
|------|-------|
| `general` | Any disagreement |
| `relationship` | Attachment needs, communication patterns, bids for connection |
| `family` | Generational patterns, cultural expectations, long history |
| `workplace` | Professional boundaries, power dynamics, HR awareness |
| `roommate` | Shared living, daily friction, boundary negotiation |
| `political` | Respect for values, finding common ground, avoiding debate traps |
| `neighbor` | Property concerns, community norms, practical solutions |
| `business` | Financial stakes, contractual obligations, future relationship |

### Notifications (`notifications.py`)

SendGrid-based email system with branded HTML templates.

| Function | Purpose |
|----------|---------|
| `send_email(to, subject, html, text)` | Low-level SendGrid wrapper. Falls back to logging when `SENDGRID_API_KEY` is not set. |
| `send_invite_email(to, creator, topic, link, message)` | Branded session invite with topic preview, personal note, "Join the conversation" CTA, and "What to expect" section. |
| `send_password_reset_email(to, name, link)` | Branded password reset with "Reset Password" CTA. |

**Email templates** use inline CSS for compatibility, include the Vilora logo as a hosted PNG (`/static/img/email-logo.png`), and have plain text fallbacks.

**Sender:** `support@maiatech.ai` (domain authenticated in SendGrid via GCP Marketplace). See `EMAIL_AND_SMS_NOTIFICATIONS_PROMPT.md` for setup notes.

### Database (`models/database.py`)

Dual-mode database supporting both SQLite (local dev) and PostgreSQL (Railway production). Auto-detects based on `DATABASE_URL` env var.

**Helper functions:**
- `_is_postgres()` — checks if PostgreSQL is configured
- `_cursor(db)` — returns dict-cursor for both DB types
- `_exec(db, sql, params)` — executes queries, converting `?` to `%s` for PostgreSQL
- `db_init()` — creates all tables (separate SQL for SQLite vs PostgreSQL)

**Tables:**

| Table | Purpose |
|-------|---------|
| `users` | User accounts (email, display_name, password_hash) |
| `mediation_sessions` | Sessions with topic, type, mode (mediation/personal), invite_code, status |
| `session_participants` | Many-to-many: which users are in which sessions |
| `messages` | Chat messages with msg_type (user/mediator/intake) |
| `agreements` | Documented agreements from sessions |
| `password_resets` | Token-based password reset (1-hour expiry, single use) |
| `session_summaries` | Cached AI summaries (keyed by session_id + message_count) |
| `user_memories` | AI-extracted and user-provided personal context (category, content, confidence, active) |

**Models:**
- `User(UserMixin)` — Flask-Login compatible user model with password hashing
- `MediationSession` — Session model with `_from_row()` for consistent construction
- `Message` — Chat message model

## Session Modes

### Mediation Mode (`session_mode='mediation'`)
- Multi-party: creator invites other party via email or link
- Uses `SYSTEM_PROMPT` (impartial facilitator)
- `should_respond` uses AI judgment to decide when to chime in
- Invite banner shown in session room
- Participant status indicator (waiting/joined)
- Welcome modal for invited participants

### Personal Mode (`session_mode='personal'`)
- One-on-one with Vilora, no other participants
- Uses `COUNSELOR_PROMPT` (warm advisor)
- Vilora always responds to every message
- No invite banner or participant status
- Topic auto-generates a concise title via `generate_title()`

## Session Creation Flows

Three paths from the dashboard "New Session" button:

1. **Help me frame this** — User writes freely in one textarea → Vilora parses into topic, type, and perspective via `/api/frame` → pre-filled form for review
2. **I know what I want to say** — Direct to the full session form
3. **Talk to Vilora one-on-one** — Single textarea for personal sessions

All three support **tone chips** — selectable tags that influence how Vilora approaches the conversation (e.g., "Find common ground," "Keep things calm," "Devil's advocate").

## User Memory System

Vilora learns about users over time to provide personalized mediation and counseling.

**Memory categories:** profile, communication, history, pattern, preference

**How memories are created:**
- **AI extraction:** After a session summary is generated, Vilora analyzes the transcript and extracts insights about each participant
- **Onboarding:** Guided 5-step questionnaire (age, relationships, work, conflict style, values)
- **Manual:** Users can add memories directly from the "About Me" page

**How memories are used:**
- Injected into the system prompt during mediation and framing
- Each participant's memories are loaded separately and never shared with other participants

**User control:**
- "About Me" page shows all memories grouped by category
- Users can edit, delete, or add memories
- AI-detected memories are labeled with confidence scores

## API Endpoints

### Authentication
| Method | Path | Description |
|--------|------|-------------|
| GET | `/login` | Login/register page |
| POST | `/api/login` | Login (returns redirect URL for pending joins) |
| POST | `/api/register` | Create account |
| POST | `/api/logout` | Logout |
| GET | `/forgot-password` | Forgot password page |
| POST | `/api/forgot-password` | Send reset email via SendGrid |
| GET | `/reset-password/<token>` | Reset password page (validates token) |
| POST | `/api/reset-password` | Submit new password |

### Sessions
| Method | Path | Description |
|--------|------|-------------|
| GET | `/dashboard` | Session list page |
| GET | `/api/sessions` | List user's sessions |
| POST | `/api/sessions` | Create session (accepts `mode: 'personal'` or `'mediation'`) |
| DELETE | `/api/sessions/:id` | Delete session (creator only, cascades to messages/summaries/memories) |
| GET | `/join/<code>` | Join via invite link (saves pending join through login flow) |
| POST | `/api/sessions/:id/join` | Submit intake perspective |
| POST | `/api/sessions/:id/invite` | Send branded email invite via SendGrid |

### Mediation Room
| Method | Path | Description |
|--------|------|-------------|
| GET | `/session/:id` | Session room page |
| GET | `/api/sessions/:id/messages` | Get messages (includes display_name and is_self flag) |
| POST | `/api/sessions/:id/messages` | Send message (triggers `should_respond` → `mediate` if appropriate) |
| GET | `/api/sessions/:id/participants` | Get participant list |
| GET | `/api/sessions/:id/summary` | Get/generate summary (cached by message count) |

### Framing & Memory
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/frame` | AI framing assistant (returns structured JSON: topic, type, perspective, tips) |
| GET | `/api/user/memories` | List active memories for current user |
| POST | `/api/user/memories` | Add a memory manually |
| PUT | `/api/user/memories/:id` | Edit a memory |
| DELETE | `/api/user/memories/:id` | Deactivate a memory |

### Pages
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Landing page (redirects to dashboard if logged in) |
| GET | `/about-me` | Memory viewer and onboarding |
| GET | `/settings` | User preferences |

## Frontend Architecture

The frontend uses server-rendered Jinja2 templates with inline JavaScript for interactivity. No build step or framework.

**Key patterns:**
- `base.html` provides navbar (with inline SVG logo), footer, Google Fonts, favicon, og tags
- Each page extends `base.html` and includes its own `<script>` block
- API calls use `fetch()` with JSON request/response
- Modals are `<div class="modal">` elements toggled via `style.display`
- Polling: session room polls messages and participants every 5 seconds
- Voice input: Web Speech API via `voice.js` (continuous recognition, mic toggle button)
- Auto-scroll: only scrolls to bottom if user is near bottom (within 150px)
- Timestamps: server stores UTC, browser converts to local time via `localTime()` helper

**CSS architecture:** Single `style.css` file with CSS custom properties for the brand palette. See `design-reference.md` for color values and typography.

## Environment Variables

### Required (Production)
| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string (auto-set by Railway Postgres add-on) |
| `SECRET_KEY` | Flask session encryption key |
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude |
| `SENDGRID_API_KEY` | SendGrid API key for email delivery |

### Optional
| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Server port | `5001` |
| `NOTIFICATION_FROM_EMAIL` | Sender email address | `support@maiatech.ai` |
| `NOTIFICATION_FROM_NAME` | Sender display name | `Vilora` |

### Local Development
Create a `.env` file (gitignored) with:
```
ANTHROPIC_API_KEY=sk-ant-...
SECRET_KEY=dev-secret
```
SendGrid and DATABASE_URL are optional locally — emails log to console, SQLite is used for data.

## Deployment

- **Hosting:** Railway (auto-deploys from GitHub `main` branch)
- **Database:** Railway PostgreSQL add-on
- **WSGI:** Gunicorn via `Procfile` (`web: gunicorn app:app --access-logfile - --error-logfile - --log-level info`)
- **Env vars:** Set via `railway variables set KEY=value` (Railway CLI)
- **Domain:** `www.vilora.ai` (CNAME to Railway), `vilora.ai` forwards via GoDaddy 301
- **SSL:** Automatic via Railway

See `railway-app-deployment-guide.md` for detailed setup steps.

## Brand & Design

See `design-reference.md` for the complete brand specification including:
- Logo variants (primary mark, horizontal lockup, icon mark)
- Icon mark SVG path data and viewBox
- Color palette (Teal `#1D9E75`, Deep `#0F6E56`, Dark `#085041`, Light `#5DCAA5`, Pale `#E1F5EE`)
- Typography (Jost, weights 300/400/500)
- UI component styles (buttons, message bubbles, cards)

Brand source file: `C:\Users\grayt\My Drive\projects\vilora\vilora-brand.svg`

## Testing

**Simulation script:** `scripts/test_mediation.py`
- Creates test users (Alice and Bob), runs a full mediation session, and generates a summary
- Usage: `python scripts/test_mediation.py [base_url]`
- Defaults to `http://localhost:5001`, pass Railway URL for production testing

**Fix-titles utility:** `python app.py fix-titles`
- Retroactively generates short titles for personal sessions with long topic text

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Dual SQLite/PostgreSQL | SQLite for zero-config local dev, PostgreSQL for Railway production. `_exec()` adapter handles `?` vs `%s` and cursor differences. |
| Inline JS over framework | Keeps the stack simple, no build step, fast iteration. Each page owns its interactivity. |
| AI-gated mediation responses | Vilora doesn't respond to every message in mediation mode — uses `should_respond()` with heuristics + AI judgment to chime in at natural moments. Always responds in personal mode. |
| Memory extraction on summary | Memories are extracted when summaries are generated (user-initiated), not after every message. Avoids excessive API calls while still learning. |
| Cached summaries | Summaries are cached by `(session_id, message_count)`. Re-requesting with no new messages returns the cache. |
| SendGrid over SMTP | More reliable delivery, branded templates, no SMTP configuration complexity. Migrated from Flask-Mail/Gmail SMTP. |
| Session mode field | `session_mode` column distinguishes mediation vs personal sessions, allowing different system prompts, UI, and response behavior. |

## Planned Features

See the prompts directory for detailed specs:
- **Email & SMS Notifications** (`EMAIL_AND_SMS_NOTIFICATIONS_PROMPT.md`) — Activity digests, join notifications, Twilio SMS (Phase 2-3)
- **User Memory & Personalization** (`USER_MEMORY_AND_PERSONALIZATION_PROMPT.md`) — Cross-session pattern detection, relationship memory, proactive insights (Phase 3-5)

## Text-to-Speech (Read Aloud)

### Overview

Every message in the session chat has a speaker icon that reads the message aloud using the browser's Web Speech API (`window.speechSynthesis`). Users can control playback (play, pause, stop) and change speed. Speed changes mid-playback resume from the current position rather than restarting from the beginning.

### Architecture

All TTS code lives in `templates/session.html` in the `// --- Text-to-Speech ---` section. No backend involvement -- it's entirely client-side.

**Key variables:**
- `SPEAK_SPEEDS` -- array of available rate values (0.5 to 2.0)
- `currentSpeedIndex` -- index into SPEAK_SPEEDS for the selected rate
- `currentSpeakText` -- full text of the message being read
- `currentSpeakMsgId` -- message ID (also used by polling guard to prevent re-render during playback)
- `speechState` -- one of: `'idle'`, `'playing'`, `'paused'`, `'finished'`
- `activeUtterance` -- reference to the current `SpeechSynthesisUtterance` object
- `spokenCharIndex` -- character position tracked via `onboundary` event, used for mid-playback speed changes

**Key functions:**
- `speakMessage(messageId, btnEl)` -- entry point when speaker icon is clicked. Toggles controls on/off.
- `doSpeak(text, messageId, isResume)` -- creates and speaks an utterance. The ONLY function that calls `speechSynthesis.speak()`.
- `pickSpeed(speedIndex, messageId)` -- called when a speed button is clicked. If playing, resumes from current position at new speed.
- `killSpeech()` -- nulls callbacks on active utterance, calls `cancel()`, sets state to idle.
- `buildControlsHtml(messageId)` -- generates the play/pause/stop + speed button HTML.

### Critical Implementation Rules (Lessons Learned)

These rules were discovered through extensive debugging on April 5, 2026. Violating any of them will break speed controls in Chrome.

1. **`speechSynthesis.speak()` must be called synchronously from a user gesture (click handler).** Chrome silently ignores `speak()` calls from inside `setTimeout`, `requestAnimationFrame`, or Promises. Never wrap the speak call in any async mechanism.

2. **`doSpeak()` must be the ONLY function that calls `speechSynthesis.speak()`.** Having multiple code paths that call `speak()` makes it impossible to reason about the engine state.

3. **Do NOT call `speechSynthesis.cancel()` unless there is an active utterance.** Calling `cancel()` on an idle engine can put Chrome's speech synthesis into a broken state where subsequent `speak()` calls ignore the `rate` property. The `killSpeech()` function guards this: it only calls `cancel()` when `activeUtterance` is not null.

4. **Do NOT use dummy utterances to "reset" the engine.** Patterns like `speak(new SpeechSynthesisUtterance(''))` followed by `cancel()` make the rate-ignoring bug worse, not better.

5. **Do NOT set `utterance.voice` explicitly.** On some systems, setting the voice can interfere with rate handling. Let the browser use its default voice.

6. **Null out `onend`/`onerror` callbacks before calling `cancel()`.** Chrome fires `onend` asynchronously after `cancel()`. If the callback is still attached, it will overwrite `speechState` and corrupt the UI. `killSpeech()` nulls callbacks first: `activeUtterance.onend = null; activeUtterance.onerror = null;`

7. **Use the `onboundary` event to track spoken position.** `utterance.onboundary` fires for each word with `e.charIndex`. Store this in `spokenCharIndex`. When changing speed mid-playback, use `currentSpeakText.substring(spokenCharIndex)` to resume from the current position.

8. **Speed button visibility is filtered by screen size.** Desktop shows 0.75x through 1.75x. Mobile (480px and below) shows 0.75x through 1.5x. The full speed array still exists for internal use.

### The Chrome `cancel()` + `rate` Bug

Chrome has a long-standing bug where calling `speechSynthesis.cancel()` can cause subsequent utterances to ignore the `rate` property. The utterance plays at the default rate (1.0) regardless of what `rate` is set to, even though inspecting the object shows the correct value.

**What triggers it:** Calling `cancel()` when nothing is playing, calling `cancel()` multiple times, or calling `speak()` too quickly after `cancel()`.

**What fixes it:** Only calling `cancel()` when there's an active utterance (rule #3 above), and calling `speak()` synchronously in the same call stack (rule #1).

**How to verify rate works:** Open the browser console on any page and paste:
```javascript
speechSynthesis.cancel();
const u = new SpeechSynthesisUtterance("Testing at two times speed");
u.rate = 2;
speechSynthesis.speak(u);
```
If this plays at 2x speed, the browser supports rate changes. If Vilora's speed controls don't work but this console test does, one of the rules above is being violated.

## Changelog

| Date | Change |
|------|--------|
| 2026-03-29 | Initial project setup, Flask app, mediation engine, session management |
| 2026-03-29 | Railway deployment, custom domain (vilora.io), password reset |
| 2026-03-30 | Brand integration (logo, colors, Jost font), test simulation script |
| 2026-03-30 | Session UX improvements (invite link, participant status, delete, summary caching) |
| 2026-03-31 | User memory system (extraction, CRUD, About Me page, onboarding) |
| 2026-03-31 | One-on-one personal counseling mode with dedicated system prompt |
| 2026-04-01 | Tone chips, voice input, session title generation |
| 2026-04-01 | vilora.ai domain setup, SendGrid email integration |
| 2026-04-02 | Architecture documentation |
