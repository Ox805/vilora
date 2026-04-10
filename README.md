# Vilora — Strength Through Dialogue

**Last Updated:** 2026-04-10

An AI-powered mediation platform that helps people work through disagreements, conflicts, and misunderstandings with an impartial, expert mediator.

## Features

### Mediation
- **Impartial AI Mediator**: Neutral, unbiased facilitation powered by Claude
- **Personal Counseling Mode**: One-on-one conversations for individual guidance
- **Structured Intake**: Each party shares their perspective privately before the joint session
- **8 Mediation Frameworks**: Tailored mediation for relationships, family, workplace, roommates, neighbors, politics, business partnerships, and general disputes
- **Real-time Mediation**: Guided dialogue with de-escalation and reframing
- **Session Summaries**: AI-generated summaries with concerns, agreements, and next steps
- **Invite Links**: One party creates a session, the other joins via link
- **Session History**: Track past mediations with unread message counts

### AI Tools
- **Polish**: AI text cleanup for spelling and grammar without changing the user's voice
- **Frame Issue**: AI-assisted neutral framing of session topics
- **Vilora Council**: 5 specialized advisor personas analyze a question in parallel, peer-review each other, and produce a synthesized recommendation
- **User Memory**: Persistent insights about users carried across sessions to personalize future mediations

### Communication
- **Voice Input**: Browser speech-to-text on all text inputs
- **File Uploads**: Share documents and images in sessions (10MB limit, Google Cloud Storage)
- **Message Reactions**: 10 emoji reaction types on messages
- **Nudge System**: Remind inactive participants to return (rate-limited)
- **Email Notifications**: Session invites and activity alerts via SendGrid
- **SMS Notifications**: Text-based alerts and invites via Twilio
- **Phone Verification**: SMS-based verification with 6-digit codes

### Account Management
- **Email Verification**: Token-based signup verification (24h expiry)
- **Password Reset**: Secure token-based reset flow (1h expiry)
- **Notification Preferences**: Toggle email and SMS notifications
- **Display Name Management**: Update display name from settings

## Tech Stack

- **Backend**: Python with Flask
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **AI**: Anthropic Claude API for mediation engine
- **Authentication**: Flask-Login for user sessions

## Installation

1. Clone the repository:
   ```bash
   git clone git@github.com:Ox805/vilora.git
   cd vilora
   ```

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your ANTHROPIC_API_KEY
   ```

5. Run the application:
   ```bash
   python app.py
   ```

6. Open your browser to `http://localhost:5001`

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask session secret key | Random (auto-generated) |
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude | Required |
| `DATABASE_URL` | PostgreSQL connection string (production) | Uses SQLite locally |
| `BASE_URL` | Public URL for generated links | `https://www.vilora.io` |
| `SENDGRID_API_KEY` | SendGrid API key for email notifications | Optional |
| `NOTIFICATION_FROM_EMAIL` | Sender email for notifications | `support@maiatech.ai` |
| `NOTIFICATION_FROM_NAME` | Sender name for notifications | `Vilora` |
| `TWILIO_ACCOUNT_SID` | Twilio account SID for SMS | Optional |
| `TWILIO_AUTH_TOKEN` | Twilio auth token for SMS | Optional |
| `TWILIO_PHONE_NUMBER` | Twilio sender phone number | Optional |
| `GCS_CREDENTIALS_JSON` | Google Cloud Storage credentials JSON | Optional |
| `GCS_BUCKET_NAME` | GCS bucket for file uploads | `vilora-uploads` |

## Project Structure

```
vilora/
├── app.py                  # Flask server & API endpoints
├── notifications.py        # Email notifications via SendGrid
├── sms.py                  # SMS notifications via Twilio
├── storage.py              # File uploads via Google Cloud Storage
├── mediation/              # AI mediation engine
│   ├── engine.py           # Core mediation logic & Claude integration
│   └── frameworks.py       # Dispute-type-specific mediation frameworks
├── models/                 # Data models
│   └── database.py         # SQLite/PostgreSQL for sessions & messages
├── static/
│   ├── css/
│   │   └── style.css       # Main styling
│   └── js/
│       ├── api.js          # Shared API utilities
│       ├── polish.js        # AI text polish component
│       └── voice.js         # Speech-to-text input
├── templates/
│   ├── base.html           # Base layout template
│   ├── landing.html        # Landing page
│   ├── login.html          # Login/register page
│   ├── dashboard.html      # Session management dashboard
│   ├── session.html        # Mediation room
│   ├── settings.html       # User settings & preferences
│   ├── about_me.html       # User profile page
│   ├── invite_landing.html # Invite link landing page
│   ├── forgot_password.html # Password reset request
│   ├── reset_password.html # Password reset form
│   ├── verify_pending.html # Email verification pending
│   ├── verify_expired.html # Expired verification token
│   └── error.html          # Error page
├── tests/                  # Test suites
├── scripts/                # Development scripts
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
└── .gitignore              # Git ignore rules
```

## How It Works

### Group Mediation
1. **Create an account** and log in
2. **Start a new session** — describe the issue, choose a mediation type, share your perspective
3. **Send the invite link** to the other party
4. **They join and share their perspective** privately
5. **Mediation begins** — Vilora facilitates the conversation, reframes positions, and finds common ground
6. **Get a summary** with documented agreements and next steps

### Personal Counseling
1. **Create an account** and log in
2. **Start a personal session** — describe what you need guidance on
3. **Talk with Vilora** one-on-one for advice, perspective, or help thinking through a situation

## Mediation Types

| Type | Best For |
|------|----------|
| General | Any disagreement |
| Relationship | Couples and partners |
| Family | Siblings, parents, extended family |
| Workplace | Professional conflicts and team issues |
| Roommate | Shared living disputes |
| Political | Political and social issue discussions |
| Neighbor | Neighbor conflicts |
| Business | Business partnership disputes |

## License

MIT
