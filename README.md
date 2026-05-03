# Vilora — Strength Through Dialogue

**Last Updated:** 2026-05-03

AI-powered mediation, collaboration, brainstorming, and decision-making. Vilora is a conversational platform that helps people think more clearly, work through tough conversations, and reach better outcomes — alone, with another person, or as a group.

Whether you're working through a disagreement, exploring ideas, making a tough decision, planning something complex, or just need a sounding board, Vilora facilitates the conversation, surfaces what matters, and helps you reach clarity.

## Three Ways to Use Vilora

### 1. Group Sessions
Invite one or more people into a shared conversation that Vilora facilitates. Pick a session purpose to shape how Vilora shows up:

| Purpose | Best For |
|---------|----------|
| Mediation | Disagreements, conflicts, and misunderstandings |
| Brainstorming | Generating and building on ideas as a group |
| Decision-making | Weighing options and reaching a choice together |
| Planning | Coordinating a project, event, or shared next steps |
| General discussion | Open-ended conversation that benefits from structure |

Each participant can share their perspective privately during intake, then the joint session begins with shared context.

### 2. One-on-One with Vilora
A private conversation with just you and Vilora. Use it for advice, to think through a decision, brainstorm ideas, prepare for a difficult conversation, or just talk something out with a sounding board. Tone chips let you steer how Vilora engages: quick advice, deep exploration, devil's advocate, action plan, encouragement, and more.

### 3. The Vilora Council
Five specialized advisor personas analyze your question in parallel from different angles, peer-review each other's blind spots, then deliver a synthesized recommendation with a concrete next step. Available standalone from the dashboard or invokable mid-conversation.

## Features

### Conversation
- **Session Purposes**: Mediation, brainstorming, decision-making, planning, or general discussion — each shapes how Vilora facilitates
- **Tone Chips**: Steer Vilora's style per session (quick advice, devil's advocate, just listen, action plan, expand my perspective, give me the facts, be encouraging, and more)
- **Mediation Frameworks**: 8 specialized framings for relationships, family, workplace, roommates, neighbors, politics, business partnerships, and general disputes
- **Structured Intake**: Each party shares their perspective privately before the joint session
- **Session Summaries**: AI-generated summaries with concerns, agreements, and next steps
- **Invite Links**: Share a link or send via email/SMS to bring others in
- **Session History**: Track past sessions with unread message counts and quick re-entry

### AI Tools
- **Vilora Council**: 5 advisor personas analyze a question in parallel, peer-review each other, and produce a synthesized recommendation
- **Polish**: AI text cleanup for spelling and grammar without changing the user's voice
- **Frame Issue**: AI-assisted neutral framing of session topics
- **User Memory**: Persistent insights about users carried across sessions to personalize future conversations
- **Expert Knowledge**: Ask Vilora for facts, research, or context mid-conversation on any topic

### Composition & Messaging
- **Compose Bar**: Multi-line input with a toolbar for bullet lists, bold, underline, voice, and polish
- **Voice Input**: Browser speech-to-text on all text inputs
- **File Uploads**: Share documents, images, and markdown files in sessions (10MB limit, Google Cloud Storage)
- **Markdown Formatting**: Bold, underline, and bullet lists rendered in messages
- **Message Reactions**: 10 emoji reaction types on messages
- **Nudge System**: Remind inactive participants to return (rate-limited)

### Notifications
- **Email Notifications**: Session invites and activity alerts via SendGrid
- **SMS Notifications**: Text-based alerts and invites via Twilio
- **Phone Verification**: SMS-based verification with 6-digit codes
- **Dashboard Polling**: Live unread counts on the dashboard

### Account Management
- **Email Verification**: Token-based signup verification (24h expiry)
- **Password Reset**: Secure token-based reset flow (1h expiry)
- **Notification Preferences**: Toggle email and SMS notifications
- **Display Name Management**: Update display name from settings

## Tech Stack

- **Backend**: Python with Flask
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **AI**: Anthropic Claude API for the conversation engine and Council
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
├── mediation/              # AI conversation engine
│   ├── engine.py           # Core engine, Claude integration, Council
│   └── frameworks.py       # Purpose- and dispute-type-specific framings
├── models/                 # Data models
│   └── database.py         # SQLite/PostgreSQL for sessions & messages
├── static/
│   ├── css/
│   │   └── style.css       # Main styling
│   └── js/
│       ├── api.js          # Shared API utilities
│       ├── polish.js       # AI text polish component
│       └── voice.js        # Speech-to-text input
├── templates/
│   ├── base.html           # Base layout template
│   ├── landing.html        # Landing page
│   ├── login.html          # Login/register page
│   ├── dashboard.html      # Dashboard, session chooser, Council launcher
│   ├── session.html        # Conversation room (compose bar, messages)
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

### Group Session
1. **Create an account** and log in
2. **Start a group session** — pick a purpose (mediation, brainstorm, decision, planning, or general), describe the topic, and let Vilora help you frame it
3. **Send the invite link** (or email/SMS) to the other participants
4. **They join and share their perspective** privately during intake
5. **The joint session begins** — Vilora facilitates the conversation, keeps it on track, and helps the group reach clarity
6. **Get a summary** with key points, agreements, and next steps

### One-on-One with Vilora
1. **Create an account** and log in
2. **Start a personal session** — describe what's on your mind
3. **Pick a tone** (or several) to steer how Vilora engages
4. **Talk it through** — get advice, brainstorm, think a decision out loud, or prepare for a real-world conversation

### The Vilora Council
1. **Ask the Council** from the dashboard or mid-conversation
2. **5 advisors respond in parallel** from different angles
3. **They peer-review each other** and surface blind spots
4. **You receive a synthesized recommendation** with a concrete next step

## Mediation Frameworks

When the session purpose is Mediation, Vilora applies a framework tailored to the relationship type:

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
