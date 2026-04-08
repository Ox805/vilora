# Emoji Reactions on Chat Messages

**Created:** April 3, 2026
**Last Updated:** April 8, 2026
**Status:** Implemented
**Dependencies:** Messages system (implemented), session infrastructure
**Priority:** Medium. Adds lightweight engagement and expression without requiring users to compose a full reply.
**References:** `models/database.py` (Message model), `templates/session.html` (message rendering), `static/css/style.css`

---

## Problem Statement

Currently, the only way to respond to a message in Vilora is to write a new message. This creates friction for lightweight acknowledgment ("I hear you", "I agree", "that resonated with me"). In mediation contexts, non-verbal cues matter -- a simple reaction can signal empathy, agreement, or lightness without derailing the conversation flow.

---

## Reaction Set

Use a fixed set of common reactions (not a full emoji picker). These are universal, appropriate for mediation contexts, and easy to render:

| Reaction | Emoji | Meaning |
|----------|-------|---------|
| Like     | 👍    | Agreement / acknowledgment |
| Dislike  | 👎    | Disagreement |
| Love     | ❤️    | Empathy / deep agreement |
| Laugh    | 😂    | Humor / lightheartedness |
| Surprised| 😮    | Surprise / "I didn't know that" |
| Sad      | 😢    | Sympathy / understanding pain |

Store reactions using short string keys: `like`, `dislike`, `love`, `laugh`, `surprised`, `sad`.

---

## Implementation Plan

### 1. Database Schema

Create a `message_reactions` table:

```sql
CREATE TABLE IF NOT EXISTS message_reactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    reaction TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(message_id, user_id, reaction)
);
```

Key constraints:
- One reaction of each type per user per message (the UNIQUE constraint). A user can add both a 👍 and a ❤️ to the same message, but cannot add two 👍s.
- `ON DELETE CASCADE` so reactions are cleaned up when a message is deleted.

Add this table creation to the `init_db()` function in `models/database.py` alongside the existing table definitions (around line 85).

### 2. Model Layer

Add a `MessageReaction` class to `models/database.py`:

```python
class MessageReaction:
    VALID_REACTIONS = {'like', 'dislike', 'love', 'laugh', 'surprised', 'sad'}

    EMOJI_MAP = {
        'like': '\U0001f44d',
        'dislike': '\U0001f44e',
        'love': '\u2764\ufe0f',
        'laugh': '\U0001f602',
        'surprised': '\U0001f62e',
        'sad': '\U0001f622',
    }

    def __init__(self, id, message_id, user_id, reaction, created_at=None):
        self.id = id
        self.message_id = message_id
        self.user_id = user_id
        self.reaction = reaction
        self.created_at = created_at

    @classmethod
    def toggle(cls, message_id, user_id, reaction):
        """Add reaction if it doesn't exist, remove if it does. Returns (action, reaction)."""
        if reaction not in cls.VALID_REACTIONS:
            raise ValueError(f"Invalid reaction: {reaction}")
        # Check if already exists
        existing = db.execute(
            "SELECT id FROM message_reactions WHERE message_id=? AND user_id=? AND reaction=?",
            (message_id, user_id, reaction)
        ).fetchone()
        if existing:
            db.execute("DELETE FROM message_reactions WHERE id=?", (existing['id'],))
            db.commit()
            return ('removed', reaction)
        else:
            db.execute(
                "INSERT INTO message_reactions (message_id, user_id, reaction) VALUES (?, ?, ?)",
                (message_id, user_id, reaction)
            )
            db.commit()
            return ('added', reaction)

    @classmethod
    def get_for_message(cls, message_id):
        """Returns reaction summary: {reaction_key: {count, user_ids}}"""
        rows = db.execute(
            "SELECT reaction, user_id FROM message_reactions WHERE message_id=?",
            (message_id,)
        ).fetchall()
        summary = {}
        for row in rows:
            r = row['reaction']
            if r not in summary:
                summary[r] = {'count': 0, 'user_ids': []}
            summary[r]['count'] += 1
            summary[r]['user_ids'].append(row['user_id'])
        return summary

    @classmethod
    def get_for_messages(cls, message_ids):
        """Bulk fetch reactions for multiple messages. Returns {message_id: {reaction: {count, user_ids}}}"""
        if not message_ids:
            return {}
        placeholders = ','.join('?' * len(message_ids))
        rows = db.execute(
            f"SELECT message_id, reaction, user_id FROM message_reactions WHERE message_id IN ({placeholders})",
            message_ids
        ).fetchall()
        result = {}
        for row in rows:
            mid = row['message_id']
            r = row['reaction']
            if mid not in result:
                result[mid] = {}
            if r not in result[mid]:
                result[mid][r] = {'count': 0, 'user_ids': []}
            result[mid][r]['count'] += 1
            result[mid][r]['user_ids'].append(row['user_id'])
        return result
```

### 3. API Endpoints

Add to `app.py`:

#### 3.1 Toggle Reaction

```
POST /api/sessions/<session_id>/messages/<message_id>/reactions
Body: { "reaction": "like" }
Response: { "success": true, "action": "added"|"removed", "reactions": { ...updated summary } }
```

- Verify the user is a participant in the session
- Verify the message belongs to the session
- Call `MessageReaction.toggle()`
- Return the updated reaction summary for that message

#### 3.2 Include Reactions in Message List

Modify the existing `GET /api/sessions/<session_id>/messages` endpoint to include reactions in each message object:

```json
{
    "id": 42,
    "content": "I understand your frustration",
    "msg_type": "user",
    "display_name": "Alice",
    "reactions": {
        "like": { "count": 2, "user_ids": [1, 3], "includes_self": true },
        "love": { "count": 1, "user_ids": [2], "includes_self": false }
    }
}
```

Use `MessageReaction.get_for_messages()` with all message IDs in a single query to avoid N+1 queries. Add the `includes_self` boolean on the server side by checking if `current_user.id` is in `user_ids`.

### 4. Frontend: Reaction Display

In `templates/session.html`, update the `renderMessages()` function to add a reaction bar below each message's content.

#### 4.1 Reaction Display (below message content)

For each message, render existing reactions as small pill badges:

```html
<div class="reaction-bar">
    <button class="reaction-pill active" onclick="toggleReaction(42, 'like')" title="You, Alice">
        👍 2
    </button>
    <button class="reaction-pill" onclick="toggleReaction(42, 'love')">
        ❤️ 1
    </button>
    <button class="reaction-add-btn" onclick="showReactionPicker(42, this)">
        <svg><!-- small + or smiley icon --></svg>
    </button>
</div>
```

- Only show reaction pills for reactions that have count > 0
- Add `active` class if `includes_self` is true (the current user has reacted with this)
- Always show a small "add reaction" button (smiley face with +) at the end of the bar
- The `title` attribute on each pill should list the display names of users who reacted (for tooltip on hover)

#### 4.2 Reaction Picker (on click of + button)

Show a small floating picker with all 6 reaction options:

```html
<div class="reaction-picker">
    <button onclick="toggleReaction(42, 'like')">👍</button>
    <button onclick="toggleReaction(42, 'dislike')">👎</button>
    <button onclick="toggleReaction(42, 'love')">❤️</button>
    <button onclick="toggleReaction(42, 'laugh')">😂</button>
    <button onclick="toggleReaction(42, 'surprised')">😮</button>
    <button onclick="toggleReaction(42, 'sad')">😢</button>
</div>
```

- Position the picker relative to the "add reaction" button
- Close the picker when clicking outside of it or after selecting a reaction
- On self-messages (right-aligned), position the picker to the left so it doesn't overflow off-screen

#### 4.3 JavaScript

```javascript
const REACTION_EMOJIS = {
    like: '👍', dislike: '👎', love: '❤️',
    laugh: '😂', surprised: '😮', sad: '😢'
};

async function toggleReaction(messageId, reaction) {
    closeReactionPicker();
    const res = await fetch(`/api/sessions/${SESSION_ID}/messages/${messageId}/reactions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reaction })
    });
    const data = await res.json();
    if (data.success) {
        // Update the reaction bar for this specific message in-place
        // without re-rendering all messages (to avoid scroll jump)
        updateReactionBar(messageId, data.reactions);
    }
}

function showReactionPicker(messageId, buttonEl) {
    // Close any existing picker first
    closeReactionPicker();
    // Create and position picker relative to buttonEl
    // ...
}

function closeReactionPicker() {
    const existing = document.querySelector('.reaction-picker');
    if (existing) existing.remove();
}

function updateReactionBar(messageId, reactions) {
    // Find the message element by data-message-id attribute
    // Re-render just the reaction-bar div inside it
}
```

Important: Update `renderMessages()` to set `data-message-id` on each message div so reactions can be updated in-place without a full re-render.

### 5. CSS Styling

Add to `static/css/style.css`:

```css
/* Reaction bar - sits below message content */
.reaction-bar {
    display: flex;
    flex-wrap: wrap;
    gap: 0.25rem;
    margin-top: 0.35rem;
    align-items: center;
}

/* Individual reaction pill */
.reaction-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.2rem;
    padding: 0.15rem 0.45rem;
    border-radius: 1rem;
    border: 1px solid var(--border);
    background: var(--bg-card);
    font-size: 0.75rem;
    cursor: pointer;
    transition: background 0.15s, border-color 0.15s;
    line-height: 1.3;
}

.reaction-pill:hover {
    background: var(--bg-main);
    border-color: var(--primary);
}

/* Highlighted when current user has this reaction */
.reaction-pill.active {
    background: #E6F4F1;
    border-color: var(--primary);
}

/* Self-messages have white text, so reaction pills need different treatment */
.message-self .reaction-pill {
    background: rgba(255, 255, 255, 0.15);
    border-color: rgba(255, 255, 255, 0.3);
    color: white;
}

.message-self .reaction-pill:hover {
    background: rgba(255, 255, 255, 0.25);
}

.message-self .reaction-pill.active {
    background: rgba(255, 255, 255, 0.3);
    border-color: rgba(255, 255, 255, 0.5);
}

/* Add-reaction button (smiley +) */
.reaction-add-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.5rem;
    height: 1.5rem;
    border-radius: 50%;
    border: 1px dashed var(--border);
    background: none;
    cursor: pointer;
    opacity: 0;
    transition: opacity 0.15s;
    font-size: 0.7rem;
    color: var(--text-muted);
}

.message:hover .reaction-add-btn,
.reaction-bar:has(.reaction-pill) .reaction-add-btn {
    opacity: 1;
}

.message-self .reaction-add-btn {
    border-color: rgba(255, 255, 255, 0.3);
    color: rgba(255, 255, 255, 0.7);
}

/* Reaction picker popup */
.reaction-picker {
    position: absolute;
    display: flex;
    gap: 0.2rem;
    padding: 0.35rem 0.5rem;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 1.5rem;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
    z-index: 100;
}

.reaction-picker button {
    background: none;
    border: none;
    font-size: 1.2rem;
    cursor: pointer;
    padding: 0.2rem 0.3rem;
    border-radius: 0.5rem;
    transition: background 0.1s, transform 0.1s;
}

.reaction-picker button:hover {
    background: var(--bg-main);
    transform: scale(1.2);
}
```

### 6. Mobile Considerations

- The "add reaction" button should always be visible on mobile (touch devices have no hover). Use the same pattern as message delete buttons (see existing mobile CSS).
- The reaction picker should be positioned carefully on small screens to avoid overflow. Consider centering it above/below the message on screens under 600px.
- Reaction pills should be large enough to tap (minimum 32px touch target).
- Add appropriate mobile overrides:

```css
@media (max-width: 600px) {
    .reaction-add-btn {
        opacity: 1;  /* Always visible on mobile */
    }

    .reaction-pill {
        padding: 0.25rem 0.5rem;
        font-size: 0.8rem;
    }

    .reaction-picker {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        justify-content: center;
        border-radius: 1rem 1rem 0 0;
        padding: 0.75rem;
        gap: 0.5rem;
    }

    .reaction-picker button {
        font-size: 1.5rem;
        padding: 0.4rem 0.6rem;
    }
}
```

### 7. Behavior Rules

1. **All message types can receive reactions** except `council` messages (which are system indicators, not real messages).
2. **Users can react to their own messages.** This is standard behavior in all chat apps.
3. **Toggling:** Clicking a reaction you already added removes it. Clicking a different reaction adds it (users can have multiple different reactions on one message).
4. **Polling compatibility:** The existing 5-second polling already calls `GET /messages` which will now include reactions. Reactions update automatically on poll. When a user toggles a reaction, update the UI optimistically (immediately) rather than waiting for the next poll.
5. **No reactions on deleted messages.** The `ON DELETE CASCADE` handles cleanup. The UI should not show reaction controls on messages that are being deleted.
6. **Mediator messages can receive reactions.** Users should be able to react to Vilora's responses.

### 8. Files to Modify

| File | Changes |
|------|---------|
| `models/database.py` | Add `message_reactions` table to `init_db()`, add `MessageReaction` class |
| `app.py` | Add `POST .../reactions` endpoint, modify `GET .../messages` to include reactions |
| `templates/session.html` | Update `renderMessages()`, add reaction picker JS, add `toggleReaction()` |
| `static/css/style.css` | Add reaction bar, pill, picker, and mobile styles |

No new files needed. No new dependencies.

---

## Implementation Summary

10 reaction types implemented: like, dislike, love, laugh, surprised, sad, haha, emphasis, question, and fire. Reactions toggle on/off per user per message. Reaction bar displayed below messages showing emoji pills with counts. Emoji picker renders as a bottom sheet on mobile and inline on desktop. message_reactions database table with unique constraint on (message_id, user_id, reaction). Real-time reaction counts included in message rendering via bulk fetch (get_for_messages). Reactions update in-place without full message re-render.
