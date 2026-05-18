# Ask Vilora — targeted questions

**Status:** Approved design, not yet implemented
**Date:** 2026-05-18
**Mockup:** [`static/mockups/ask-vilora-targeted.html`](../../../static/mockups/ask-vilora-targeted.html)

## Goal

Let a participant in a group session ask Vilora a specific question, while keeping today's one-click "Ask Vilora to review the whole session" path exactly as it is. The change should be discoverable but not noisy, should not disrupt the compose bar, and should follow patterns we've already established for Council asks and per-message delete.

## Non-goals (preserved exactly as today)

These exist today and the design must not touch them:

- The compose `<textarea id="message-input">` — placeholder, keyboard behavior (Ctrl+Enter submits), and user-draggable resize (via `.compose-bar-main { resize: vertical }`).
- The `+` attach button and `uploadFile()` flow.
- The mic button that `static/js/voice.js` auto-attaches to every `<textarea>`.
- The `Polish` button and `static/js/polish.js`.
- The `Ask Council` button and its modal flow.
- The existing one-click `Ask Vilora` full-review behavior when the new input is left blank.
- The per-message delete rules shipped previously (`requested_by` on mediator messages; only the requester can delete; legacy creator-delete fallback for NULL `requested_by`).

## UX flow

Five states, matching the [mockup](../../../static/mockups/ask-vilora-targeted.html):

1. **Default.** The existing `ask-vilora-bar` button row is unchanged except that `Ask Vilora` gets a trailing `▾` caret indicating it can expand.
2. **Expanded.** Clicking the button reveals, just above the `ask-vilora-bar` row, a single-line `<input type="text">` with placeholder "Ask Vilora something specific (optional)…", an inline `Ask` submit, and a muted hint line: "Leave blank to get Vilora's take on the whole session. <kbd>Esc</kbd> to close." The input gets focus immediately. The button flips to `▴`.
3. **Submit with text.** The input's value is posted to `/api/sessions/<id>/ask-vilora`. The transcript receives two new rows in order:
    - A chip-styled "ask" message (`msg_type='ask'`), authored by the asker, showing the question text.
    - The mediator's reply (`msg_type='mediator'`, `parent_message_id` = the ask's id, `requested_by` = the asker).
4. **Submit blank.** Identical to today: a single `msg_type='mediator'` message appears, no chip.
5. **Delete by asker.** The chip and the reply each show an `×` on hover for the asker only. Clicking either deletes both rows in one request (paired delete).

## Visibility

- Only group sessions show the `ask-vilora-bar` (existing `{% if not is_personal %}` gate). Targeted asks inherit the same gate. Personal sessions are unaffected.
- The chip is visible to all session participants, like the Council indicator.

## Architecture

### Storage

Add a single nullable column to `messages`:

| column | type | purpose |
|---|---|---|
| `parent_message_id` | INTEGER, nullable, FK → `messages(id)` `ON DELETE SET NULL` | On a mediator message, points to the `ask` row that triggered it. Null for unbound mediator messages (welcome, auto-response in personal, blank-submit full review). |

`ON DELETE SET NULL` matters for two reasons. (1) `delete_session` issues `DELETE FROM messages WHERE session_id = ?`, which deletes parent and child rows in the same statement; without `SET NULL` the FK can fire mid-statement depending on engine order. (2) If a future code path deletes an `ask` without going through `delete_message`'s paired-delete, the mediator reply survives as a standalone message rather than orphaning a constraint violation.

A targeted ask is therefore a pair of message rows:

```
messages (msg_type='ask',      user_id=asker,  content=question_text)
                                    ^
                                    │ FK parent_message_id
messages (msg_type='mediator', user_id=NULL,  content=ai_response,
                                requested_by=asker,
                                parent_message_id=<id of the ask>)
```

We considered embedding the question in the mediator's `content` as a JSON prefix to avoid a schema change. Rejected: it would couple two distinct concerns (the user's prompt vs. Vilora's reply) into a single row, complicate rendering and reactions, and make paired-delete more brittle.

### API

Extend the existing endpoint rather than add a new one:

```
POST /api/sessions/<int:session_id>/ask-vilora
Body: { "question": "" }   // optional; absent or "" → full-session review (current behavior)
```

Handler:

1. If `question` is non-empty, insert an `ask` message: `Message.create(db, session_id, current_user.id, question, msg_type='ask')`.
2. Call `mediation_engine.mediate(..., user_question=question or None)`. New optional `user_question` kwarg — when present, the engine appends a clear directive to the system/user prompt: "[Asker name] is asking: '[question]'. Respond directly to that question, drawing on the conversation above as context." When absent, behavior is bit-for-bit identical to today.
3. Create the mediator message via `create_mediator_message(..., requested_by=current_user.id, parent_message_id=<ask.id or None>)`.
4. Return both messages in the response so the client can render without waiting for the next poll: `{ "success": true, "ask_message": {...}, "mediator_message": {...} }`. The existing single-`mediator_message` shape stays for the blank-submit path so older clients still work.

Considered: a new `/ask-vilora-question` endpoint. Rejected: duplicates session loading, participant/memory loading, and error handling for no clear benefit.

### Delete behavior

`delete_message` route gets one new rule: a **paired delete**.

- If the target row is `msg_type='ask'`: find any `mediator` row whose `parent_message_id` equals this row's id; **delete the mediator first**, then the ask. (Order matters only if the FK is set to RESTRICT; with `ON DELETE SET NULL` either order works, but child-first stays cleanest.)
- If the target row is `msg_type='mediator'` with non-null `parent_message_id`: delete the mediator first, then the referenced `ask` row.

Authorization works without changes:

- An `ask` row has `user_id = asker`, so the existing "delete your own message" rule already lets the asker delete it.
- The mediator row already has `requested_by = asker`, so the requester-can-delete rule shipped in `b490838` covers it.
- A non-asker has neither path and gets the existing 403.

Invariant: `ask.user_id == bound_mediator.requested_by`. Both are written from `current_user.id` in the same handler call; the design has no code path that updates either field after creation, so they can't diverge.

### Frontend

**`templates/session.html`**

- The static `Ask Vilora` button becomes a toggle. New state lives in a JS variable; no server round-trip required to expand/collapse.
- New container (initially `display:none`) directly above the `ask-vilora-bar`, containing the input, submit, and hint. Rendered only on group sessions (same `{% if not is_personal %}` gate).
- New `renderMessages` branch for `m.msg_type === 'ask'`:
    - Renders a chip styled like `.council-indicator` (or a forked `.ask-indicator` if we want it visually distinct — see Open questions below).
    - Shows `display_name` + question text + timestamp.
    - Shows the `×` button when `m.can_delete` is true (server-computed, same field used for mediator deletes).
- Mediator-message rendering needs no change. Because the `ask` row is inserted just before the mediator row by timestamp, ordinary message-ordering puts them adjacent automatically.
- `askVilora()` JS:
    - Reads the input value.
    - POSTs `{ question: value }` to `/ask-vilora`.
    - On success, calls `loadMessages()` and `markSessionSeen()` as today.
    - Clears the input and collapses the expand state.
- Enter on the input submits; Esc collapses and clears.

**`app.py:get_messages`**

- The existing per-message `can_delete` flag (computed in the handler that returns `/messages`) needs one extension: for an `ask` row, it's `True` iff `m.user_id == current_user.id`. This is already covered by the existing `if m.user_id == current_user.id: d['can_delete'] = True` branch — no code change needed beyond making sure `ask` messages flow through the same loop.

**`static/css/style.css`**

- New `.ask-vilora-input-row`, `.ask-vilora-input`, `.ask-vilora-hint` rules — see the mockup for visual targets.
- New `.ask-indicator` (or extension of `.council-indicator`) — same chip pattern, with a soft mint background so it reads as Vilora-flavored rather than Council-flavored.

### Mediation engine

`mediation/engine.py:mediate` gains an optional `user_question: str | None = None` kwarg. When set, the prompt construction appends a final user turn (or a system suffix; implementation detail to be decided in the plan) that names the asker and quotes the question, directing the model to answer it specifically while still drawing on the transcript. When `None`, control flow is unchanged — same prompt, same output shape.

## Database migration

Mirrors the `requested_by` migration shipped in `b490838`:

- Postgres: add `parent_message_id INTEGER REFERENCES messages(id) ON DELETE SET NULL` to the `messages` CREATE TABLE block. Add `"ALTER TABLE messages ADD COLUMN parent_message_id INTEGER REFERENCES messages(id) ON DELETE SET NULL"` to the `migrations` list.
- SQLite: add `parent_message_id INTEGER` with `FOREIGN KEY (parent_message_id) REFERENCES messages(id) ON DELETE SET NULL` to the CREATE TABLE block. Append the same ALTER to the `sqlite_migrations` list. Idempotent — duplicate-column errors are swallowed. (Note: SQLite's `ALTER TABLE ADD COLUMN` cannot attach a referential action to an existing-column FK; the migration adds the column with no FK, which is acceptable since existing rows all have `NULL` for it and new rows are written by the create path that sets the value explicitly. New databases get the proper FK from the CREATE TABLE.)

The `Message` model gains `parent_message_id` in `__init__`, `to_dict`, `create`, and `get_by_session`. Default is `None`. `create_mediator_message` gets an optional `parent_message_id` parameter that is `None` for the three existing callsites (welcome, personal-mode auto-response, blank-submit full review).

## What gets touched (file list)

- `models/database.py` — schema + model.
- `app.py` — `create_mediator_message` signature, `ask_vilora` route, `delete_message` paired-delete rule, `get_messages` (incidental — `ask` rows flow through the existing enrichment loop).
- `mediation/engine.py` — `mediate()` accepts optional `user_question`.
- `templates/session.html` — toggle on Ask Vilora button, new input row, new `ask` render branch in `renderMessages`.
- `static/css/style.css` — input row + chip styles.

What does NOT get touched: compose-bar HTML/CSS, voice.js, polish.js, file upload code, Ask Council code, personal-mode flow.

## Testing approach

- **Manual, per state:**
    - State 1: button row looks unchanged with the new caret.
    - State 2: click expands input; Esc collapses; Enter submits.
    - State 3: question chip + Vilora reply both land; chip shows asker + question.
    - State 4: blank submit produces a single mediator message (today's behavior).
    - State 5: asker hover shows X on both rows; clicking either deletes both; non-asker sees no X.
- **Auth boundary:** non-asker DELETE of an ask row → 403. Non-asker DELETE of the bound mediator row → 403.
- **Migration idempotency:** run app twice against an existing local SQLite DB; column added once, second startup is a clean no-op.
- **Backward compat:** existing mediator messages with `parent_message_id IS NULL` continue to render and delete exactly as today (creator-delete fallback still works because the previous design preserved that path).

## Open questions

These don't block the design; flagging for the implementation plan:

1. **Chip styling.** Reuse `.council-indicator` verbatim, or fork to `.ask-indicator` with a mint background to differentiate from Council? Mockup uses a forked mint variant; can flip to match Council exactly with a one-line CSS change.
2. **Prompt directive wording.** "[Asker] is asking: '…'. Respond directly to that question, drawing on the conversation above as context." — wording can be refined when we wire up the engine and watch a few real responses.
3. **Empty-string vs. whitespace-only question.** Treat whitespace-only as empty (full-review fallthrough). To be enforced server-side with a `.strip()`.
4. **Rate limiting.** Today's `Ask Vilora` is unthrottled. Out of scope for this design; flag if user feedback shows abuse.

## Out of scope

- Persisting draft text in the input across page reloads.
- Differentiated loading states between targeted and full-review (a single "Vilora is thinking…" works for both).
- Letting other participants react to or reply to the chip directly.
- Personal-mode targeted asks (personal mode has Vilora auto-responding already; no `Ask Vilora` button to extend).
