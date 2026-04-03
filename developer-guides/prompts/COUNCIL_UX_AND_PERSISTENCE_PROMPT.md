# Council UX, Persistence, and Shared Access

**Created:** April 2, 2026
**Status:** Planning
**Dependencies:** Council engine (implemented), session infrastructure
**Priority:** High. Council is a key differentiator but currently hard to understand and results are ephemeral.
**References:** `VILORA_COUNCIL_PROMPT.md` (original Council spec), `application-architecture.md`

---

## Problem Statement

The Council is one of Vilora's most powerful features, but it has several UX gaps:

1. **Users don't understand how it works.** There's no explanation of the 5 advisors, the peer review process, or how to interpret results. Users click the button and get a wall of text without context.

2. **Results are ephemeral.** Council results exist only in the browser. If you refresh, they're gone. There's no way to revisit past Council sessions.

3. **Results are private.** Only the person who requested the Council can see the results. In a group session, other participants have no idea the Council was consulted, what was asked, or what it recommended.

4. **No way to act on results.** After reading the synthesis, there's no clear path to share it with the group, save it, or follow up with deeper questions.

---

## Implementation Plan

### Feature 1: "How It Works" Explainer

**Goal:** Help users understand the Council before they use it, and understand the results after.

#### 1.1 Explainer in the Council Modal

Add a collapsible "How does this work?" section at the top of the Council modal (both session and dashboard versions):

```
▸ How does this work?

  The Council gives you 5 different expert perspectives on any question:

  The Contrarian — looks for what could go wrong or what you might be overlooking
  The First Principles Thinker — strips away assumptions and asks what you're really trying to solve
  The Expansionist — finds opportunities and upside you might be missing
  The Outsider — sees your situation with completely fresh eyes, no insider bias
  The Executor — focuses on what you should actually do next, concretely

  After all 5 respond independently, they anonymously review each other's
  blind spots. Then a synthesis pulls everything together into a clear
  recommendation with one concrete next step.

  The whole process takes about 30-60 seconds.
```

- Collapsed by default (users who already know can skip it)
- Uses a `<details>` element for native collapse behavior
- Styled consistently with the rest of the modal

#### 1.2 Advisor Descriptions in Results

When displaying individual advisor responses in the results panel, add a one-line description under each advisor name:

| Advisor | Description |
|---------|-------------|
| The Contrarian | Looks for risks, flaws, and what could go wrong |
| The First Principles Thinker | Questions assumptions and reframes the real problem |
| The Expansionist | Finds upside, adjacent opportunities, and bigger possibilities |
| The Outsider | Fresh eyes with no insider bias or assumed context |
| The Executor | Focuses on concrete next steps and actionability |

These descriptions appear as subtitle text in the collapsible advisor sections:

```
▸ The Contrarian
  Looks for risks, flaws, and what could go wrong
```

---

### Feature 2: Council Persistence (Database Storage)

**Goal:** Store Council results so they can be revisited and shared.

#### 2.1 Database Schema

```sql
CREATE TABLE IF NOT EXISTS council_results (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES mediation_sessions(id),  -- nullable for dashboard council
    requested_by INTEGER NOT NULL REFERENCES users(id),
    question TEXT NOT NULL,
    context TEXT,
    advisors JSON NOT NULL,        -- array of {name, response}
    review TEXT NOT NULL,          -- peer review text
    synthesis TEXT NOT NULL,       -- chairman synthesis text
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Notes:**
- `session_id` is nullable because Council can be run from the dashboard without a session
- `advisors` stored as JSON (PostgreSQL native JSON, SQLite stores as text)
- Results are immutable (no edits, no deletes by users)

#### 2.2 Storage Flow

After the Council background thread completes:
1. Store the full result in `council_results`
2. If within a session, also create a special message in the `messages` table:
   - `msg_type = 'council'`
   - `content` = JSON with `council_result_id` and `question`
   - `user_id` = the requesting user's ID

#### 2.3 Retrieval API

- `GET /api/council/results/<result_id>` — returns full Council result (advisors, review, synthesis)
- Only accessible to session participants (if session-linked) or the requesting user (if dashboard)

---

### Feature 3: Shared Access in Group Sessions

**Goal:** All session participants can see when the Council was consulted and view the results.

#### 3.1 Chat Timeline Indicator

When a Council result is created within a session, a special message appears in the chat timeline:

```
┌─────────────────────────────────────────────────┐
│  🏛  Tim asked the Council:                      │
│  "Should we expand to the European market?"      │
│                                           [View] │
└─────────────────────────────────────────────────┘
```

**Design:**
- Styled differently from user/mediator/intake messages (centered, muted, informational)
- Shows who requested it and what they asked
- "View" button opens the full Council results in the side panel
- Appears in chronological order with other messages

#### 3.2 Message Rendering

In `renderMessages()`, add handling for `msg_type === 'council'`:

```javascript
} else if (m.msg_type === 'council') {
    const data = JSON.parse(m.content);
    return `<div class="message message-council">
        <div class="council-indicator">
            <span class="council-indicator-label">
                ${escapeHtml(m.display_name)} asked the Council:
            </span>
            <span class="council-indicator-question">"${escapeHtml(data.question)}"</span>
            <button class="btn btn-sm" onclick="viewCouncilResult(${data.council_result_id})">View</button>
        </div>
    </div>`;
}
```

#### 3.3 View Council Result

`viewCouncilResult(resultId)` fetches the full result from the API and displays it in the existing Council side panel, same as when results first appear.

#### 3.4 Multiple Council Results

A session can have multiple Council requests from different participants. Each one appears as a separate indicator in the chat timeline. The side panel shows one result at a time.

---

### Feature 4: Acting on Council Results

**Goal:** Give users clear paths to use the Council's output.

#### 4.1 "Share with group" Action

In the Council results panel, add a "Share with group" button that posts the synthesis to the session chat as a regular message from the user:

- Only available in group sessions
- Posts a formatted version of the synthesis (not the full advisor responses)
- Attributed to the user who shares it ("Tim shared the Council's recommendation:")
- Other participants see it as a regular message and can respond to it

#### 4.2 "Ask a follow-up" Action

In the Council results panel, add an "Ask a follow-up" button that:

- Opens the Council modal pre-filled with the previous question
- Automatically includes the prior Council result as additional context
- Lets the user refine their question or ask about a specific advisor's point
- The new Council run references the previous one for continuity

#### 4.3 "Copy" Action

A simple "Copy to clipboard" button on the synthesis section that copies the synthesis text for use outside Vilora (email, docs, etc.).

---

### Feature 5: Council Settings (Future Phase)

**Goal:** Let users customize the Council to their needs.

#### 5.1 Advisor Toggle

In Settings, let users:
- Toggle individual advisors on/off (minimum 3 must be active)
- See descriptions of each advisor's role
- Reset to defaults

#### 5.2 Advisor Intensity

Optional slider or toggle per advisor:
- **Standard** (default) — balanced analysis
- **Aggressive** — pushes harder (e.g., Contrarian becomes more skeptical, Executor becomes more demanding about specifics)

#### 5.3 Custom Advisors (Future)

Allow users to define their own advisor personas:
- Name, description, and system prompt
- Save and reuse across sessions
- Share advisor configurations

#### 5.4 Pre-built Council Configurations

Domain-specific advisor sets:
- **Startup Council:** Contrarian, Market Analyst, Technical Feasibility, Customer Advocate, Investor
- **Career Council:** Risk Assessor, Values Alignment, Long-term Thinker, Practical Advisor, Industry Insider
- **Creative Council:** Critic, Audience Member, Innovator, Traditionalist, Producer
- **Investment Council:** Bull Case, Bear Case, Technical Analyst, Risk Manager, Macro Strategist

---

## UI Specifications

### Council Indicator in Chat (Feature 3)

```css
.message-council {
    /* Centered, not left/right aligned like other messages */
    align-self: center;
    max-width: 90%;
    background: none;
    padding: 0;
}

.council-indicator {
    background: #F7F5F0;  /* subtle warm gray, distinct from messages */
    border: 1px dashed var(--border);
    border-radius: var(--radius);
    padding: 0.75rem 1rem;
    text-align: center;
    font-size: 0.85rem;
}

.council-indicator-label {
    color: var(--text-muted);
}

.council-indicator-question {
    display: block;
    color: var(--text);
    margin: 0.25rem 0 0.5rem;
    font-style: italic;
}
```

### Advisor Descriptions in Results

```css
.council-advisor-desc {
    font-size: 0.75rem;
    color: var(--text-muted);
    font-weight: 400;
    margin-left: 0.25rem;
}
```

### Action Buttons in Results Panel

```
┌──────────────────────────────────────────────────┐
│  Council Results                          [Close] │
├──────────────────────────────────────────────────┤
│                                                   │
│  Synthesis & Recommendation                       │
│  ┌─────────────────────────────────────────────┐  │
│  │ ... synthesis content ...                   │  │
│  │                                             │  │
│  │ [Share with group] [Ask a follow-up] [Copy] │  │
│  └─────────────────────────────────────────────┘  │
│                                                   │
│  Peer Review                                      │
│  ...                                              │
│                                                   │
│  Individual Advisor Perspectives                  │
│  ▸ The Contrarian                                 │
│    Looks for risks, flaws, and what could go wrong│
│  ▸ The First Principles Thinker                   │
│    Questions assumptions and reframes the problem │
│  ...                                              │
└──────────────────────────────────────────────────┘
```

---

## Implementation Order

| Phase | Features | Effort |
|-------|----------|--------|
| 1 | Explainer in modal + advisor descriptions in results | Small |
| 2 | Database persistence + retrieval API | Medium |
| 3 | Chat timeline indicator + shared viewing | Medium |
| 4 | Share with group + copy + follow-up actions | Small |
| 5 | Council settings (toggle advisors, intensity) | Medium |
| 6 | Custom advisors + pre-built configurations | Large (future) |

Recommended: Build phases 1-4 together as they're interconnected. Phase 5-6 can come later.

---

## Success Criteria

| Criteria | Measurement |
|----------|-------------|
| Users understand what the Council does before using it | Explainer is visible, collapse rate indicates awareness |
| Council results persist across page refreshes | Results retrievable from database |
| All session participants can view Council results | Chat indicator visible, View button works for all |
| Users act on Council results | Share/copy/follow-up buttons are used |
| Council usage increases with better UX | More Council requests per user over time |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-04-02 | Initial creation. Explainer, persistence, shared access, actions, and settings. |
