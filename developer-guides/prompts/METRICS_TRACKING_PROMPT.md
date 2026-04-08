# Vilora Metrics Tracking Implementation Prompt

## Context

Vilora is an AI-powered mediation and collaboration platform. We need automated tracking of key metrics to measure whether the product is delivering value. Metrics must be **behavioral and objective** -- derived from user actions, not self-reported feelings.

## Current Data Available

The database already tracks:
- `messages` — every message with `session_id`, `user_id`, `msg_type` ('user'/'mediator'), `created_at`
- `mediation_sessions` — `creator_id`, `topic`, `session_type`, `status` (currently always 'active'), `created_at`
- `session_participants` — `session_id`, `user_id`, `joined_at`
- `session_last_seen` — `session_id`, `user_id`, `last_seen_at` (updated on every view)
- `message_reactions` — `message_id`, `user_id`, `reaction` (like/dislike/love/laugh/surprised/sad/fire/question/emphasis), `created_at`
- `nudge_log` — `session_id`, `nudger_id`, `target`, `created_at`
- `notification_log` — `session_id`, `user_id`, `channel` (email/sms), `created_at`
- `session_invites` — `session_id`, `inviter_id`, `status`, `created_at`
- `session_summaries` — `session_id`, `message_count`, `summary`, `created_at`
- `users` — `email`, `display_name`, `created_at`

Database is SQLite via SQLAlchemy. Models are in `models/database.py`. Routes are in `app.py` (Flask).

## What To Build

### 1. Session Lifecycle (prerequisite for everything else)

Sessions currently have no end state. Add:
- `ended_at` (TIMESTAMP, nullable) to `mediation_sessions`
- `outcome` (TEXT, nullable) to `mediation_sessions` — one of: `'resolved'`, `'stalled'`, `'abandoned'`, `'ongoing'`

**Auto-detection rules:**
- `stalled` — no messages from any participant in 72+ hours, at least 3 messages exist
- `abandoned` — no messages from any participant in 72+ hours, fewer than 3 messages exist
- `resolved` — session explicitly closed by a participant (add a "close session" action), OR AI mediator detects agreement language in final messages
- `ongoing` — default state, active conversation

Add a periodic task (or extend the existing notification background worker in `app.py`) that runs every hour to auto-classify stalled/abandoned sessions.

### 2. Core Metrics Table

Create a `session_metrics` table that is computed/refreshed whenever a session is viewed or when the background worker runs:

```
session_metrics:
  session_id (FK, UNIQUE)
  
  # Engagement
  total_messages (INT) — count of user messages (exclude mediator)
  participant_count (INT) — number of unique participants who sent at least 1 message
  messages_per_participant_avg (REAL) — total_messages / participant_count
  participation_balance (REAL) — 0.0 to 1.0, where 1.0 = perfectly balanced
    Formula: 1 - Gini coefficient of message counts per participant
    Example: 2 participants with 10 and 10 messages = 1.0 (perfect)
             2 participants with 19 and 1 messages = 0.1 (dominated)
  
  # Timing
  first_message_at (TIMESTAMP)
  last_message_at (TIMESTAMP)
  duration_minutes (INT) — time from first to last message
  avg_response_time_minutes (REAL) — average gap between consecutive messages from different participants
  invite_to_join_minutes (REAL) — average time from invite sent to participant joining
  
  # Engagement Quality
  stall_count (INT) — number of gaps > 24 hours between messages
  nudge_count (INT) — total nudges sent in this session
  organic_engagement (BOOLEAN) — True if no nudges were needed
  reaction_count (INT) — total reactions
  positive_reaction_ratio (REAL) — (like + love + fire + laugh) / total reactions
  
  # Outcome
  outcome (TEXT) — resolved/stalled/abandoned/ongoing
  
  updated_at (TIMESTAMP)
```

### 3. User Metrics Table

Create a `user_metrics` table, refreshed daily by the background worker:

```
user_metrics:
  user_id (FK, UNIQUE)
  
  # Activity
  sessions_created (INT)
  sessions_participated (INT)
  total_messages_sent (INT)
  
  # Retention
  first_session_at (TIMESTAMP)
  last_active_at (TIMESTAMP)
  return_rate (REAL) — sessions_participated / sessions_invited (0.0 to 1.0)
  is_repeat_user (BOOLEAN) — participated in 2+ sessions
  
  # Engagement
  avg_messages_per_session (REAL)
  avg_response_time_minutes (REAL)
  invitations_sent (INT) — how many people this user invited to sessions
  
  updated_at (TIMESTAMP)
```

### 4. Platform-Level Metrics Endpoint

Create `GET /api/admin/metrics` (admin-only, protected) that returns aggregate stats:

```json
{
  "period": "last_30_days",
  "sessions": {
    "total_created": 45,
    "total_completed": 30,
    "resolution_rate": 0.67,
    "stall_rate": 0.18,
    "abandonment_rate": 0.15,
    "avg_duration_minutes": 240,
    "avg_messages_per_session": 18,
    "avg_participation_balance": 0.72
  },
  "users": {
    "total_registered": 120,
    "active_last_30_days": 45,
    "repeat_user_rate": 0.35,
    "avg_sessions_per_user": 1.8,
    "invitation_acceptance_rate": 0.60
  },
  "engagement": {
    "avg_response_time_minutes": 15,
    "organic_engagement_rate": 0.55,
    "avg_reactions_per_session": 4.2,
    "positive_reaction_ratio": 0.78
  }
}
```

Support `?period=last_7_days|last_30_days|last_90_days|all_time` query parameter.

### 5. Session Close Flow

Add a way for participants to close a session:
- Add a "Close Session" button in the session UI
- When clicked, show a brief modal: "How would you describe the outcome?" with options:
  - "We reached an agreement" -> outcome = 'resolved'
  - "We're taking a break" -> outcome = 'paused' (don't auto-classify as stalled)
  - "We're done for now" -> outcome = 'closed'
- `POST /api/sessions/<session_id>/close` with `{ outcome: "resolved" }`
- Sets `ended_at` to current timestamp and `outcome` to the selected value
- This is the ONE place we ask for subjective input, and it's a single tap, not a survey

### 6. Participation Balance Calculation

The Gini coefficient for participation balance:

```python
def calc_participation_balance(message_counts: list[int]) -> float:
    """
    Returns 0.0 (one person dominated) to 1.0 (perfectly balanced).
    message_counts: list of message counts per participant, e.g. [12, 8, 10]
    """
    if not message_counts or sum(message_counts) == 0:
        return 0.0
    n = len(message_counts)
    if n == 1:
        return 1.0  # solo session, trivially balanced
    sorted_counts = sorted(message_counts)
    total = sum(sorted_counts)
    cumulative = 0
    gini_sum = 0
    for i, count in enumerate(sorted_counts):
        cumulative += count
        gini_sum += cumulative
    gini = (2 * gini_sum) / (n * total) - (n + 1) / n
    return round(1 - gini, 3)  # invert so 1.0 = balanced
```

### 7. Background Worker Extension

The existing background worker in `app.py` (the notification thread) should be extended to run metric calculations. Add a function that runs every hour:

1. Scan sessions with no messages in 72+ hours -> auto-classify as stalled/abandoned
2. Recompute `session_metrics` for any session with activity since last computation
3. Recompute `user_metrics` for any user with activity since last computation

Keep it lightweight -- only recompute what changed.

## Implementation Constraints

- SQLite database (no complex window functions, keep queries simple)
- Flask app with SQLAlchemy ORM
- No external analytics services -- everything self-contained
- Background worker already exists as a daemon thread in `app.py`
- Keep the admin endpoint simple -- no charting library needed yet, just JSON
- All new tables need proper migration (add columns/tables without breaking existing data)
- Do NOT add any user-facing surveys or feedback forms beyond the session close modal

## Files To Modify

- `models/database.py` — add new tables and columns
- `app.py` — add admin endpoint, session close endpoint, extend background worker
- `templates/session.html` — add "Close Session" button and outcome modal
- `static/css/style.css` — style the close session modal

## What NOT To Do

- Do not add Google Analytics or any third-party tracking
- Do not add cookies or tracking pixels
- Do not track individual message content in metrics (privacy)
- Do not build a full admin dashboard UI yet -- JSON endpoint is sufficient
- Do not add post-session surveys or rating prompts
- Do not use em dashes in any user-facing copy
