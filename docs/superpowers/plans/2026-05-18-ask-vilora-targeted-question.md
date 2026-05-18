# Ask Vilora Targeted Question — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an inline "ask Vilora a specific question" path to the existing Ask Vilora button in group sessions, while preserving today's one-click full-session-review behavior. Targeted asks land as a paired (ask-chip, mediator-reply) thread that only the asker can delete.

**Architecture:** A nullable `parent_message_id` column links a `msg_type='mediator'` reply to its triggering `msg_type='ask'` row. The existing `/ask-vilora` endpoint gains an optional `question` body; empty submits keep today's exact behavior. Frontend toggles a single-line input below the existing button row. Paired delete in `delete_message` removes both rows on either click.

**Tech Stack:** Flask + Jinja templates, vanilla JS, SQLite (local) + Postgres (Railway prod), Anthropic SDK.

**Spec:** `docs/superpowers/specs/2026-05-18-ask-vilora-targeted-question-design.md`
**Mockup (live preview, will be deleted at end):** https://www.vilora.io/static/mockups/ask-vilora-targeted.html

**Testing approach (codebase-specific note):** This repo has no pytest infrastructure — `tests/` holds mediation quality scenarios, not unit tests. The user deploys to vilora.io and tests UI changes live (per their preference). This plan uses:
- Small inline Python scripts for backend logic that benefits from verification (schema migration, model roundtrip).
- `curl` smoke tests against the deployed app for API endpoints.
- Manual state-by-state UI walk-through against the deployed app for visual states.

Frequent commits to `main`; Railway auto-deploys each push.

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `models/database.py` | Postgres + SQLite schema for `messages.parent_message_id`; `Message` model fields & roundtrip | Modify |
| `app.py` | `create_mediator_message` signature; `ask_vilora` route question handling; `delete_message` paired delete | Modify |
| `mediation/engine.py` | `mediate()` accepts optional `user_question` and appends a directive | Modify |
| `templates/session.html` | Toggle on Ask Vilora button; new input row; new `ask` render branch | Modify |
| `static/css/style.css` | `.ask-vilora-input-row`, `.ask-vilora-input`, `.ask-vilora-hint`, `.ask-indicator*` | Modify |
| `static/mockups/ask-vilora-targeted.html` | Pre-implementation mockup | Delete at end |

No new files. No restructuring of existing files.

---

## Task 1: Add `parent_message_id` column to `messages` table

**Files:**
- Modify: `models/database.py` (Postgres CREATE block, Postgres migrations list, SQLite CREATE block, SQLite migrations list)

- [ ] **Step 1: Add column to Postgres CREATE TABLE**

In `models/database.py`, find the Postgres `CREATE TABLE IF NOT EXISTS messages` block (around line 97). It currently looks like:

```python
"""CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES mediation_sessions(id),
    user_id INTEGER REFERENCES users(id),
    content TEXT NOT NULL,
    msg_type TEXT DEFAULT 'user',
    requested_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""",
```

Add `parent_message_id` after `requested_by`:

```python
"""CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES mediation_sessions(id),
    user_id INTEGER REFERENCES users(id),
    content TEXT NOT NULL,
    msg_type TEXT DEFAULT 'user',
    requested_by INTEGER REFERENCES users(id),
    parent_message_id INTEGER REFERENCES messages(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""",
```

- [ ] **Step 2: Add Postgres migration entry**

In the same file, find the Postgres `migrations` list. It currently ends with:

```python
"ALTER TABLE messages ADD COLUMN requested_by INTEGER REFERENCES users(id)",
```

Append the new migration:

```python
"ALTER TABLE messages ADD COLUMN requested_by INTEGER REFERENCES users(id)",
"ALTER TABLE messages ADD COLUMN parent_message_id INTEGER REFERENCES messages(id) ON DELETE SET NULL",
```

- [ ] **Step 3: Add column to SQLite CREATE TABLE**

Find the SQLite `CREATE TABLE IF NOT EXISTS messages` (around line 274). It currently looks like:

```python
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    user_id INTEGER,
    content TEXT NOT NULL,
    msg_type TEXT DEFAULT 'user',
    requested_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES mediation_sessions(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (requested_by) REFERENCES users(id)
);
```

Add `parent_message_id` and its FK:

```python
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    user_id INTEGER,
    content TEXT NOT NULL,
    msg_type TEXT DEFAULT 'user',
    requested_by INTEGER,
    parent_message_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES mediation_sessions(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (requested_by) REFERENCES users(id),
    FOREIGN KEY (parent_message_id) REFERENCES messages(id) ON DELETE SET NULL
);
```

- [ ] **Step 4: Add SQLite migration entry**

Find the `sqlite_migrations` list (added with the previous `requested_by` change). It currently is:

```python
sqlite_migrations = [
    "ALTER TABLE messages ADD COLUMN requested_by INTEGER REFERENCES users(id)",
]
```

Append:

```python
sqlite_migrations = [
    "ALTER TABLE messages ADD COLUMN requested_by INTEGER REFERENCES users(id)",
    "ALTER TABLE messages ADD COLUMN parent_message_id INTEGER REFERENCES messages(id)",
]
```

(SQLite's `ALTER TABLE ADD COLUMN` does not honor `ON DELETE` actions on added FKs — that's noted in the spec. The CREATE path above does honor it for new databases.)

- [ ] **Step 5: Verify migration is idempotent on a real DB**

Run this script — it copies the current local DB, runs the migration twice, and confirms the column appears once and the second run is a clean no-op:

```bash
python3 -c "
import sqlite3, tempfile, os, shutil
src = '/home/tim/dev/vilora/vilora.db'
fd, tmp = tempfile.mkstemp(suffix='.db'); os.close(fd)
shutil.copyfile(src, tmp)

con = sqlite3.connect(tmp)
before = [r[1] for r in con.execute('PRAGMA table_info(messages)')]
print('before:', before)
assert 'parent_message_id' not in before

# First migration run
try:
    con.execute('ALTER TABLE messages ADD COLUMN parent_message_id INTEGER REFERENCES messages(id)')
    con.commit()
except Exception as e:
    print('first run error:', e); raise

after = [r[1] for r in con.execute('PRAGMA table_info(messages)')]
print('after:', after)
assert 'parent_message_id' in after

# Second run should fail with duplicate-column (caught & rolled back in the real code path)
try:
    con.execute('ALTER TABLE messages ADD COLUMN parent_message_id INTEGER REFERENCES messages(id)')
    con.commit()
    print('UNEXPECTED: second run succeeded'); raise SystemExit(1)
except sqlite3.OperationalError as e:
    print('expected duplicate-column error on second run:', e)

os.unlink(tmp)
print('OK')
"
```

Expected output ends with `OK`. If anything else, stop and investigate.

- [ ] **Step 6: Commit**

```bash
git add models/database.py
git commit -m "Add parent_message_id column to messages table

Backs the Ask Vilora targeted-question feature: links a mediator
reply back to the ask message that triggered it. ON DELETE SET NULL
so bulk deletes (delete_session, etc) don't trip on the self-FK."
git push origin main
```

This is safe to deploy on its own — adding a nullable column with no readers yet.

---

## Task 2: Plumb `parent_message_id` through the `Message` model

**Files:**
- Modify: `models/database.py` (Message class: `__init__`, `to_dict`, `create`, `get_by_session`)
- Modify: `app.py` (`create_mediator_message` signature)

- [ ] **Step 1: Update `Message.__init__` and `to_dict`**

In `models/database.py`, find `class Message:`. Update `__init__` and `to_dict`:

```python
class Message:
    def __init__(self, id, session_id, user_id, content, msg_type, created_at=None, requested_by=None, parent_message_id=None):
        self.id = id
        self.session_id = session_id
        self.user_id = user_id
        self.content = content
        self.msg_type = msg_type
        self.created_at = created_at
        self.requested_by = requested_by
        self.parent_message_id = parent_message_id

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'content': self.content,
            'msg_type': self.msg_type,
            'requested_by': self.requested_by,
            'parent_message_id': self.parent_message_id,
            'created_at': str(self.created_at) if self.created_at else None
        }
```

- [ ] **Step 2: Update `Message.create`**

Replace the existing `create` static method with:

```python
    @staticmethod
    def create(db, session_id, user_id, content, msg_type='user', requested_by=None, parent_message_id=None):
        if _is_postgres():
            cur = _exec(db,
                "INSERT INTO messages (session_id, user_id, content, msg_type, requested_by, parent_message_id) VALUES (?, ?, ?, ?, ?, ?) RETURNING id",
                (session_id, user_id, content, msg_type, requested_by, parent_message_id)
            )
            msg_id = cur.fetchone()['id']
        else:
            cur = _exec(db,
                "INSERT INTO messages (session_id, user_id, content, msg_type, requested_by, parent_message_id) VALUES (?, ?, ?, ?, ?, ?)",
                (session_id, user_id, content, msg_type, requested_by, parent_message_id)
            )
            msg_id = cur.lastrowid
        db.commit()
        return Message(msg_id, session_id, user_id, content, msg_type, requested_by=requested_by, parent_message_id=parent_message_id)
```

- [ ] **Step 3: Update `Message.get_by_session`**

Replace the existing `get_by_session` static method with:

```python
    @staticmethod
    def get_by_session(db, session_id):
        cur = _exec(db,
            "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,)
        )
        rows = cur.fetchall()
        return [
            Message(
                r['id'], r['session_id'], r['user_id'], r['content'], r['msg_type'], r['created_at'],
                requested_by=r['requested_by'],
                parent_message_id=r['parent_message_id']
            )
            for r in rows
        ]
```

- [ ] **Step 4: Update `create_mediator_message` in `app.py`**

In `app.py` find `def create_mediator_message(db, session_id, ai_response, requested_by=None):`. Replace with:

```python
def create_mediator_message(db, session_id, ai_response, requested_by=None, parent_message_id=None):
    """Create a mediator message with an AI-generated summary prefix.

    requested_by is the user who triggered this Vilora response and is the
    only one (besides legacy creator fallback) allowed to delete it.
    parent_message_id links this reply to the 'ask' message that prompted
    it, when applicable.
    """
    summary = mediation_engine.summarize_response(ai_response)
    if summary:
        content = f"{summary}{SUMMARY_DELIMITER}{ai_response}"
    else:
        content = ai_response
    return Message.create(
        db, session_id, None, content,
        msg_type='mediator',
        requested_by=requested_by,
        parent_message_id=parent_message_id,
    )
```

Note: the three existing callsites pass nothing for `parent_message_id` and continue to work unchanged.

- [ ] **Step 5: Roundtrip verification**

Run this script — it inserts a paired ask + mediator, reads them back, confirms the linkage:

```bash
python3 -c "
import sqlite3, tempfile, os, sys
sys.path.insert(0, '/home/tim/dev/vilora')

fd, tmp = tempfile.mkstemp(suffix='.db'); os.close(fd)
con = sqlite3.connect(tmp)
con.row_factory = sqlite3.Row
con.execute('CREATE TABLE messages (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER, user_id INTEGER, content TEXT, msg_type TEXT, requested_by INTEGER, parent_message_id INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
con.commit()

# Monkeypatch _is_postgres to False, point _exec at our connection
from models import database as d
d._is_postgres = lambda: False

# Use raw SQL with the new model
ask_cur = con.execute('INSERT INTO messages (session_id, user_id, content, msg_type) VALUES (?, ?, ?, ?)', (1, 42, 'how do i bring up X?', 'ask'))
ask_id = ask_cur.lastrowid
con.execute('INSERT INTO messages (session_id, user_id, content, msg_type, requested_by, parent_message_id) VALUES (?, ?, ?, ?, ?, ?)', (1, None, 'here is what i notice...', 'mediator', 42, ask_id))
con.commit()

rows = list(con.execute('SELECT id, msg_type, user_id, requested_by, parent_message_id FROM messages ORDER BY id'))
print(rows)
assert rows[0]['msg_type'] == 'ask' and rows[0]['user_id'] == 42
assert rows[1]['msg_type'] == 'mediator' and rows[1]['requested_by'] == 42 and rows[1]['parent_message_id'] == ask_id
os.unlink(tmp)
print('roundtrip OK')
"
```

Expected: ends with `roundtrip OK`. If anything else, stop and investigate.

- [ ] **Step 6: Sanity-check Python syntax**

```bash
python3 -c "import ast; ast.parse(open('/home/tim/dev/vilora/models/database.py').read()); ast.parse(open('/home/tim/dev/vilora/app.py').read()); print('syntax ok')"
```

- [ ] **Step 7: Commit**

```bash
git add models/database.py app.py
git commit -m "Thread parent_message_id through Message model and create_mediator_message

Optional kwarg on Message.create and create_mediator_message; reads
on get_by_session and to_dict. Existing callsites are unchanged
(default None preserves today's behavior)."
git push origin main
```

---

## Task 3: Mediation engine accepts `user_question`

**Files:**
- Modify: `mediation/engine.py:360-392` (`mediate` method)

- [ ] **Step 1: Add the optional kwarg and the directive append**

In `mediation/engine.py`, find `def mediate(self, ...)` around line 360. Update the signature and add the conditional directive.

Replace the existing method body up to `response = self.client.messages.create(...)` with:

```python
    def mediate(self, topic, session_type, messages, participants, participant_memories=None, session_mode='mediation', user_question=None):
        if not self.client:
            return self._fallback_response(messages)

        participant_names = {p.id: p.display_name for p in participants}
        conversation = self._build_conversation(topic, session_type, messages, participant_names, session_mode=session_mode)

        # Build personalized system prompt with memories
        system = COUNSELOR_PROMPT if session_mode == 'personal' else SYSTEM_PROMPT
        if participant_memories:
            memory_sections = []
            for user_id, memories in participant_memories.items():
                name = participant_names.get(user_id, 'Unknown')
                context = self._build_memory_context(memories)
                if context:
                    memory_sections.append(f"\n## What you know about {name}:\n{context}")
            if memory_sections:
                system += (
                    "\n\n## Participant Knowledge\n"
                    "Use this knowledge naturally — don't explicitly reference it unless directly relevant. "
                    "The goal is for your responses to feel attuned and personal. "
                    "NEVER reveal one participant's memories to another participant."
                    + "\n".join(memory_sections)
                )

        if user_question:
            conversation = conversation + [{
                "role": "user",
                "content": (
                    f"A participant is asking you a specific question: \"{user_question}\"\n\n"
                    "Respond directly to that question. Draw on the conversation above as context, "
                    "but keep your answer focused on what they actually asked."
                )
            }]

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system,
            messages=conversation
        )

        return response.content[0].text
```

(The `user_question=None` default means every existing call site is unchanged.)

- [ ] **Step 2: Sanity-check syntax**

```bash
python3 -c "import ast; ast.parse(open('/home/tim/dev/vilora/mediation/engine.py').read()); print('ok')"
```

- [ ] **Step 3: Commit**

```bash
git add mediation/engine.py
git commit -m "mediate() accepts optional user_question

Appends a directive turn instructing Vilora to answer the question
specifically while using the transcript as context. Default None
keeps every existing caller unchanged."
git push origin main
```

---

## Task 4: Extend `/ask-vilora` route to accept an optional question

**Files:**
- Modify: `app.py:1570-1603` (the `ask_vilora` route)

- [ ] **Step 1: Replace the route body**

Find `@app.route('/api/sessions/<int:session_id>/ask-vilora', methods=['POST'])` and replace the function with:

```python
@app.route('/api/sessions/<int:session_id>/ask-vilora', methods=['POST'])
@login_required
def ask_vilora(session_id):
    """Explicitly request Vilora's input in a group session.

    Optional JSON body:
        { "question": "..." }   # if present and non-empty, Vilora answers
                                # this specific question rather than reviewing
                                # the whole session.
    """
    db = get_db()
    med_session = MediationSession.get_by_id(db, session_id)
    if not med_session or not med_session.is_participant(db, current_user.id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    payload = request.get_json(silent=True) or {}
    question = (payload.get('question') or '').strip()

    ask_msg = None
    if question:
        ask_msg = Message.create(db, session_id, current_user.id, question, msg_type='ask')

    messages = Message.get_by_session(db, session_id)
    participants = med_session.get_participants(db)

    try:
        participant_memories = {}
        for p in participants:
            memories = get_user_memories(db, p.id)
            if memories:
                participant_memories[p.id] = memories

        ai_response = mediation_engine.mediate(
            topic=med_session.topic,
            session_type=med_session.session_type,
            messages=messages,
            participants=participants,
            participant_memories=participant_memories or None,
            session_mode=med_session.session_mode,
            user_question=question or None,
        )
        ai_msg = create_mediator_message(
            db, session_id, ai_response,
            requested_by=current_user.id,
            parent_message_id=(ask_msg.id if ask_msg else None),
        )
        # Queue notifications -- Vilora's response means activity
        queue_pending_notifications(db, session_id, current_user.id)

        result = {'success': True, 'mediator_message': ai_msg.to_dict()}
        if ask_msg:
            result['ask_message'] = ask_msg.to_dict()
        return jsonify(result)
    except Exception as e:
        sys.stderr.write(f"[Vilora] Ask Vilora error: {e}\n")
        # If we already inserted an ask row but mediate() failed, leave it.
        # The user will see their question chip with no reply and can delete it.
        return jsonify({'success': False, 'error': 'Vilora could not respond. Please try again.'}), 500
```

Notes baked into the code above:
- Whitespace-only questions are treated as empty (`.strip()` then truthiness), so the full-review path catches them.
- The ask row is created *before* the mediate call so `Message.get_by_session(...)` includes it in the transcript Vilora sees. This means Vilora has the asker's exact words available, not only the directive.
- The `result` dict now optionally carries `ask_message`. The blank-submit path's response shape is byte-identical to today.

- [ ] **Step 2: Sanity-check syntax**

```bash
python3 -c "import ast; ast.parse(open('/home/tim/dev/vilora/app.py').read()); print('ok')"
```

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "Extend /ask-vilora to accept an optional question

Empty/missing question keeps today's full-session review behavior
exactly. Non-empty question creates a msg_type='ask' row, gets
included in the transcript Vilora sees, and links the mediator
reply via parent_message_id."
git push origin main
```

- [ ] **Step 4: Post-deploy smoke test (blank submit unchanged)**

Wait for Railway redeploy, then from a logged-in browser session in vilora.io, open any group session and click `Ask Vilora` (without any frontend changes yet, so it'll still be the one-click behavior). Confirm Vilora replies as today. If anything fails, roll back this commit before continuing.

(A full curl test isn't easy here because the route is `@login_required` — easier to verify via the live UI.)

---

## Task 5: Paired delete in `delete_message`

**Files:**
- Modify: `app.py:1298-1338` (the `delete_message` route)

- [ ] **Step 1: Identify the current authorization & delete code**

Open `app.py` around line 1298. The current shape is:

```python
@app.route('/api/sessions/<int:session_id>/messages/<int:message_id>', methods=['DELETE'])
@login_required
def delete_message(session_id, message_id):
    db = get_db()
    med_session = MediationSession.get_by_id(db, session_id)
    if not med_session or not med_session.is_participant(db, current_user.id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    cur = _exec(db, "SELECT * FROM messages WHERE id = ? AND session_id = ?", (message_id, session_id))
    msg = cur.fetchone()
    if not msg:
        return jsonify({'success': False, 'error': 'Message not found'}), 404

    # ... authorization branches ...

    # If this is a file message, clean up the GCS blob
    if msg['msg_type'] == 'file':
        ...

    _exec(db, "DELETE FROM messages WHERE id = ?", (message_id,))
    db.commit()
    return jsonify({'success': True})
```

You will add a paired-delete step between the auth check and the existing `DELETE`.

- [ ] **Step 2: Replace the route body**

Replace the entire `delete_message` function with:

```python
@app.route('/api/sessions/<int:session_id>/messages/<int:message_id>', methods=['DELETE'])
@login_required
def delete_message(session_id, message_id):
    db = get_db()
    med_session = MediationSession.get_by_id(db, session_id)
    if not med_session or not med_session.is_participant(db, current_user.id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    # Get the message
    cur = _exec(db, "SELECT * FROM messages WHERE id = ? AND session_id = ?", (message_id, session_id))
    msg = cur.fetchone()
    if not msg:
        return jsonify({'success': False, 'error': 'Message not found'}), 404

    # Users can delete their own messages.
    # For mediator messages, the user who requested Vilora's input can delete it.
    # Legacy mediator messages with no recorded requester fall back to creator-delete.
    if msg['user_id'] == current_user.id:
        pass  # allowed
    elif msg['msg_type'] == 'mediator' and msg['requested_by'] == current_user.id:
        pass  # requester can delete the Vilora response they triggered
    elif (msg['msg_type'] == 'mediator' and msg['requested_by'] is None
          and med_session.creator_id == current_user.id):
        pass  # legacy: creator can delete pre-feature mediator messages
    else:
        return jsonify({'success': False, 'error': 'You can only delete your own messages'}), 403

    # Identify a paired ask <-> mediator. Deleting either deletes both.
    paired_id = None
    if msg['msg_type'] == 'ask':
        cur_p = _exec(db, "SELECT id FROM messages WHERE parent_message_id = ? AND session_id = ?", (message_id, session_id))
        prow = cur_p.fetchone()
        if prow:
            paired_id = prow['id']
    elif msg['msg_type'] == 'mediator' and msg['parent_message_id']:
        paired_id = msg['parent_message_id']

    # If this is a file message, clean up the GCS blob
    if msg['msg_type'] == 'file':
        cur_att = _exec(db, "SELECT blob_path FROM file_attachments WHERE message_id = ?", (message_id,))
        att_row = cur_att.fetchone()
        if att_row:
            storage.delete_file(att_row['blob_path'])

    # Delete the paired (child) row first to avoid any FK ordering issue.
    # With ON DELETE SET NULL on parent_message_id, either order works on a
    # fresh DB, but the SQLite migration adds the column without an FK action,
    # so on migrated DBs, child-first is required.
    if paired_id is not None and msg['msg_type'] == 'ask':
        # paired_id is the mediator child of this ask -> delete mediator first
        _exec(db, "DELETE FROM messages WHERE id = ?", (paired_id,))
        _exec(db, "DELETE FROM messages WHERE id = ?", (message_id,))
    elif paired_id is not None and msg['msg_type'] == 'mediator':
        # msg is the child; paired_id is the ask parent -> delete this row first
        _exec(db, "DELETE FROM messages WHERE id = ?", (message_id,))
        _exec(db, "DELETE FROM messages WHERE id = ?", (paired_id,))
    else:
        _exec(db, "DELETE FROM messages WHERE id = ?", (message_id,))

    db.commit()
    return jsonify({'success': True})
```

- [ ] **Step 3: Sanity-check syntax**

```bash
python3 -c "import ast; ast.parse(open('/home/tim/dev/vilora/app.py').read()); print('ok')"
```

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "Paired delete for ask + mediator messages

When the user deletes an ask message, the linked mediator reply is
deleted in the same transaction (and vice versa). Order is
child-first so the migration's FK-without-action on SQLite stays
safe. Authorization is unchanged: the asker already had delete
rights on both rows via the existing ownership + requested_by
rules."
git push origin main
```

---

## Task 6: Frontend — toggle button, inline input, CSS

**Files:**
- Modify: `templates/session.html` (button row at ~line 116, `askVilora()` JS at ~line 1029)
- Modify: `static/css/style.css` (add new rules at the end of the `=== Ask Vilora ===` section, around line 2320)

- [ ] **Step 1: Update the `ask-vilora-bar` markup**

Find the existing block in `templates/session.html` (around line 116-128):

```html
<div class="ask-vilora-bar">
    <button type="button" id="message-input-polish-btn" class="btn btn-sm btn-polish" onclick="doPolish('message-input')" title="...">
        Polish
    </button>
    {% if not is_personal %}
    <button type="button" onclick="askVilora()" class="btn btn-sm btn-ask-vilora" id="ask-vilora-btn" title="...">
        Ask Vilora
    </button>
    <button type="button" onclick="askCouncilToWeighIn()" class="btn btn-sm btn-ask-vilora" id="ask-council-btn" title="...">
        Ask Council
    </button>
    {% endif %}
</div>
```

Replace with this — adds the toggleable input row directly above the bar, and changes the `Ask Vilora` button to toggle the input first (the actual ask happens via the inline submit, or by clicking the button a second time on an empty input, which preserves today's one-click feel for users who don't want to type):

```html
{% if not is_personal %}
<div id="ask-vilora-input-row" class="ask-vilora-input-row" style="display:none">
    <input id="ask-vilora-question" type="text" class="ask-vilora-input"
           placeholder="Ask Vilora something specific (optional)…"
           onkeydown="if(event.key==='Enter'){event.preventDefault();submitAskVilora();} else if(event.key==='Escape'){event.preventDefault();collapseAskVilora();}" />
    <button type="button" class="btn btn-sm btn-ask-vilora" onclick="submitAskVilora()">Ask</button>
</div>
<p id="ask-vilora-hint" class="ask-vilora-hint" style="display:none">
    Leave blank to get Vilora's take on the whole session. <kbd>Esc</kbd> to close.
</p>
{% endif %}
<div class="ask-vilora-bar">
    <button type="button" id="message-input-polish-btn" class="btn btn-sm btn-polish" onclick="doPolish('message-input')" title="Vilora will clean up spelling, punctuation, and clarity in your draft above while keeping your voice and meaning exactly the same.">
        Polish
    </button>
    {% if not is_personal %}
    <button type="button" onclick="toggleAskVilora()" class="btn btn-sm btn-ask-vilora" id="ask-vilora-btn" title="Click to ask a specific question, or click and submit blank for Vilora's take on the whole session.">
        Ask Vilora <span id="ask-vilora-caret">▾</span>
    </button>
    <button type="button" onclick="askCouncilToWeighIn()" class="btn btn-sm btn-ask-vilora" id="ask-council-btn" title="The Council provides five expert perspectives on the conversation so far, then synthesizes them into a clear recommendation.">
        Ask Council
    </button>
    {% endif %}
</div>
```

- [ ] **Step 2: Replace the `askVilora` JS with `toggleAskVilora` + `submitAskVilora` + `collapseAskVilora`**

Find the existing block in the same file (around line 1028-1052):

```javascript
// --- Ask Vilora ---
async function askVilora() {
    const btn = document.getElementById('ask-vilora-btn');
    btn.disabled = true;
    btn.textContent = 'Vilora is thinking...';

    try {
        const res = await fetch(`/api/sessions/${SESSION_ID}/ask-vilora`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await res.json();
        if (data.success) {
            loadMessages();
            markSessionSeen();
        } else {
            alert(data.error || 'Vilora could not respond.');
        }
    } catch (err) {
        alert('Failed to reach Vilora. Please try again.');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Ask Vilora to weigh in';
    }
}
```

Replace with:

```javascript
// --- Ask Vilora ---
function toggleAskVilora() {
    const row = document.getElementById('ask-vilora-input-row');
    if (!row) return;
    const hint = document.getElementById('ask-vilora-hint');
    const caret = document.getElementById('ask-vilora-caret');
    const input = document.getElementById('ask-vilora-question');

    const expanded = row.style.display !== 'none';
    if (expanded) {
        collapseAskVilora();
    } else {
        row.style.display = 'flex';
        if (hint) hint.style.display = 'block';
        if (caret) caret.textContent = '▴';
        if (input) { input.value = ''; setTimeout(() => input.focus(), 0); }
    }
}

function collapseAskVilora() {
    const row = document.getElementById('ask-vilora-input-row');
    const hint = document.getElementById('ask-vilora-hint');
    const caret = document.getElementById('ask-vilora-caret');
    const input = document.getElementById('ask-vilora-question');
    if (row) row.style.display = 'none';
    if (hint) hint.style.display = 'none';
    if (caret) caret.textContent = '▾';
    if (input) input.value = '';
}

async function submitAskVilora() {
    const btn = document.getElementById('ask-vilora-btn');
    const askBtn = document.querySelector('#ask-vilora-input-row button');
    const input = document.getElementById('ask-vilora-question');
    const question = (input && input.value || '').trim();

    btn.disabled = true;
    const originalLabel = btn.innerHTML;
    btn.innerHTML = 'Vilora is thinking…';
    if (askBtn) askBtn.disabled = true;

    try {
        const res = await fetch(`/api/sessions/${SESSION_ID}/ask-vilora`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question })
        });
        const data = await res.json();
        if (data.success) {
            collapseAskVilora();
            loadMessages();
            markSessionSeen();
        } else {
            alert(data.error || 'Vilora could not respond.');
        }
    } catch (err) {
        alert('Failed to reach Vilora. Please try again.');
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalLabel;
        if (askBtn) askBtn.disabled = false;
    }
}
```

- [ ] **Step 3: Add CSS for the input row and hint**

In `static/css/style.css`, find the `=== Ask Vilora ===` section (around line 2301). Append these rules right after the existing `.btn-ask-vilora:hover` block (around line 2320):

```css
.ask-vilora-input-row {
    display: flex;
    gap: 0.5rem;
    align-items: center;
    margin-top: 0.5rem;
    padding: 0 0.25rem;
}

.ask-vilora-input {
    flex: 1;
    border: 1px solid var(--primary-light);
    background: white;
    border-radius: var(--radius);
    padding: 0.45rem 0.75rem;
    font-size: 0.9rem;
    color: var(--text);
    outline: none;
    font-family: inherit;
}

.ask-vilora-input::placeholder { color: var(--text-muted); }

.ask-vilora-input:focus {
    border-color: var(--primary);
    box-shadow: 0 0 0 2px rgba(29, 158, 117, 0.15);
}

.ask-vilora-hint {
    color: var(--text-muted);
    font-size: 0.75rem;
    text-align: center;
    margin: 0.25rem 0 0.4rem;
}

.ask-vilora-hint kbd {
    background: #F2F0E8;
    border: 1px solid var(--border);
    border-radius: 4px;
    font-size: 0.7rem;
    padding: 0 0.3rem;
    font-family: inherit;
}
```

- [ ] **Step 4: Validate Jinja**

```bash
python3 -c "
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader('/home/tim/dev/vilora/templates'))
env.get_template('session.html')
print('ok')
"
```

- [ ] **Step 5: Commit**

```bash
git add templates/session.html static/css/style.css
git commit -m "Ask Vilora: toggleable inline question input

Clicking Ask Vilora now expands a single-line input above the
button row. Enter submits, Esc collapses. Submitting blank keeps
today's full-review behavior. The compose-bar, attach, mic,
Polish, and Ask Council are untouched."
git push origin main
```

- [ ] **Step 6: Post-deploy verification**

After Railway redeploys, open a group session at vilora.io:

1. Click `Ask Vilora ▾`. Confirm: input row appears above the buttons, caret flips to `▴`, hint visible, input focused.
2. Press Esc. Confirm: input collapses, caret returns to `▾`.
3. Click `Ask Vilora ▾`, leave input blank, click `Ask`. Confirm: a single mediator message appears (today's behavior). Input collapses.
4. Click `Ask Vilora ▾`, type "what's the most important thing in this conversation?", press Enter. Confirm: HTTP request fires (look at devtools network tab) and a mediator response appears. (The chip won't render yet — that's Task 7. Verify in devtools that the response JSON includes an `ask_message` field.)
5. Confirm the compose textarea still resizes by dragging its bottom-right corner.
6. Confirm `+` attach and mic still work.
7. Confirm Polish still works.

If any of (1)-(7) fails, fix before continuing.

---

## Task 7: Frontend — render the `ask` chip

**Files:**
- Modify: `templates/session.html` (the `renderMessages` function around line 319, and CSS at the end of the `=== Ask Vilora ===` block)
- Modify: `static/css/style.css` (chip styles)

- [ ] **Step 1: Add the `ask` branch to `renderMessages`**

In `templates/session.html`, find `function renderMessages(messages) {` (around line 319). The function currently has branches for `m.msg_type === 'mediator'`, `m.msg_type === 'council'`, `m.msg_type === 'intake'`, etc.

After the `council` branch and before the `intake` branch (so somewhere around line 370), insert:

```javascript
        } else if (m.msg_type === 'ask') {
            const canDelete = !!m.can_delete;
            const asker = escapeHtml(m.display_name || 'Someone');
            const question = escapeHtml(m.content);
            return `<div class="message message-ask" data-message-id="${m.id}">
                <div class="ask-indicator">
                    <span class="ask-indicator-label">${asker} asked Vilora:</span>
                    <span class="ask-indicator-question">"${question}"</span>
                    <span class="ask-indicator-time">${localTime(m.created_at)}</span>
                    ${canDelete ? `<button class="msg-delete-btn" onclick="deleteMessage(${m.id})" title="Delete this question and Vilora's reply">&times;</button>` : ''}
                </div>
            </div>`;
```

(The closing of the chain is whatever `} else if (m.msg_type === ...) {` came next — leave it alone.)

- [ ] **Step 2: Add the chip CSS**

In `static/css/style.css`, append to the `=== Ask Vilora ===` section (right after the `.ask-vilora-hint kbd` rule you added in Task 6):

```css
.message-ask {
    align-self: center !important;
    max-width: 90% !important;
    background: none !important;
    padding: 0 !important;
}

.ask-indicator {
    background: #F4FBF8;
    border: 1px dashed var(--primary-light);
    border-radius: var(--radius);
    padding: 0.6rem 1rem 0.7rem;
    text-align: center;
    font-size: 0.85rem;
    position: relative;
}

.ask-indicator .msg-delete-btn {
    position: absolute;
    top: 0.35rem;
    right: 0.5rem;
    margin-left: 0;
}

.ask-indicator-label {
    color: var(--text-muted);
}

.ask-indicator-question {
    display: block;
    color: var(--text);
    font-style: italic;
    margin: 0.25rem 0 0.25rem;
}

.ask-indicator-time {
    display: block;
    color: var(--text-muted);
    font-size: 0.72rem;
    margin-top: 0.2rem;
}
```

- [ ] **Step 3: Validate Jinja**

```bash
python3 -c "
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader('/home/tim/dev/vilora/templates'))
env.get_template('session.html')
print('ok')
"
```

- [ ] **Step 4: Commit**

```bash
git add templates/session.html static/css/style.css
git commit -m "Render ask message chip above Vilora's reply

New msg_type='ask' branch in renderMessages produces a mint-tinted
chip styled after the Council indicator, with the asker's name,
the question, and an X button visible only to the asker."
git push origin main
```

- [ ] **Step 5: End-to-end manual test (all five spec states)**

After Railway redeploys, walk through these states on vilora.io. Use a group session (personal mode doesn't show the row).

**State 1 — Default.** Open the session. Confirm: `Ask Vilora ▾` shows with a `▾` caret. Compose bar (textarea, +, mic, Polish, send, resize handle) looks like before.

**State 2 — Expanded.** Click `Ask Vilora ▾`. Confirm: input row appears above the bar, caret flips to `▴`, input has focus. Press Esc — collapses. Re-expand.

**State 3 — Submit with question.** Type "what's the next move here?", press Enter. Confirm: a chip "[Your name] asked Vilora: 'what's the next move here?'" appears in the transcript followed immediately by Vilora's reply. Input row collapsed.

**State 4 — Submit blank.** Expand, leave input empty, click `Ask`. Confirm: a single mediator message appears, no chip, identical to today's behavior.

**State 5 — Paired delete.** Hover the chip. Click the X. Confirm: both the chip and Vilora's reply disappear in one round-trip. Repeat State 3, then hover Vilora's reply and click its X. Confirm: both rows disappear.

**Permission test.** Open the session as a non-asker (a second logged-in account). Confirm: chip shows but no X is visible on it or on the corresponding mediator reply.

If anything fails, fix before moving on.

---

## Task 8: Delete the mockup file

**Files:**
- Delete: `static/mockups/ask-vilora-targeted.html`
- Delete: `static/mockups/` directory if empty

- [ ] **Step 1: Remove the file and the now-empty directory**

```bash
rm /home/tim/dev/vilora/static/mockups/ask-vilora-targeted.html
rmdir /home/tim/dev/vilora/static/mockups 2>/dev/null || true
```

- [ ] **Step 2: Commit**

```bash
git add -A static/mockups/
git commit -m "Remove Ask Vilora mockup file (feature shipped)"
git push origin main
```

---

## Self-Review (already performed by author)

- **Spec coverage:** every section of the spec maps to a task. Schema → 1, Model → 2, Engine → 3, API → 4, Delete → 5, Frontend toggle/input → 6, Chip rendering → 7, Mockup cleanup → 8.
- **Type consistency:** `parent_message_id` is the same name everywhere (schema, model, route params, JSON, JS). `user_question` is consistent. `Message.create` signature is repeated verbatim in Task 2 and matches what Task 4 calls.
- **Placeholder scan:** no TBDs or "handle edge cases" hand-waves. Every code-bearing step includes the actual code.
- **Auth invariants:** the spec's "ask.user_id == bound_mediator.requested_by" invariant is preserved — both are written in Task 4's route from `current_user.id` in the same handler call, no other code path sets them.
- **Preservation list:** Task 6's commit message and Step 6 verification explicitly check that the compose-bar features the user flagged (resize, +, mic, Polish) still work.
