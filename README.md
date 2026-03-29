# Vilora — Strength Through Dialogue

An AI-powered mediation platform that helps people work through disagreements, conflicts, and misunderstandings with an impartial, expert mediator.

## Features

- **Impartial AI Mediator**: Neutral, unbiased facilitation powered by Claude
- **Structured Intake**: Each party shares their perspective privately before the joint session
- **Multiple Frameworks**: Tailored mediation for relationships, family, workplace, politics, and more
- **Real-time Mediation**: Guided dialogue with de-escalation and reframing
- **Session Summaries**: AI-generated summaries with agreements and next steps
- **Invite Links**: One party creates a session, the other joins via link
- **Session History**: Track past mediations and agreements

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

## Project Structure

```
vilora/
├── app.py                  # Flask server & API endpoints
├── mediation/              # AI mediation engine
│   ├── engine.py           # Core mediation logic & Claude integration
│   └── frameworks.py       # Dispute-type-specific mediation frameworks
├── models/                 # Data models
│   └── database.py         # SQLite/PostgreSQL for sessions & messages
├── static/
│   ├── css/
│   │   └── style.css       # Main styling
│   └── js/
│       └── api.js          # Shared API utilities
├── templates/
│   ├── base.html           # Base layout template
│   ├── landing.html        # Landing page
│   ├── login.html          # Login/register page
│   ├── dashboard.html      # Session management dashboard
│   ├── session.html        # Mediation room
│   └── error.html          # Error page
├── tests/                  # Test suites
├── scripts/                # Development scripts
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
└── .gitignore              # Git ignore rules
```

## How It Works

1. **Create an account** and log in
2. **Start a new session** — describe the issue, choose a mediation type, share your perspective
3. **Send the invite link** to the other party
4. **They join and share their perspective** privately
5. **Mediation begins** — Vilora facilitates the conversation, reframes positions, and finds common ground
6. **Get a summary** with documented agreements and next steps

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
