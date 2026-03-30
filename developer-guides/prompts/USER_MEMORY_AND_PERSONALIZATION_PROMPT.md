# User Memory & Personalization — Vilora Learns Who You Are

**Created:** March 30, 2026
**Status:** Planning
**Dependencies:** None (can begin independently)
**Priority:** High — Core differentiator; transforms Vilora from a tool into a trusted advisor
**Design Reference:** `developer-guides/architecture/design-reference.md`

---

## Problem Statement

Today, every Vilora session starts from zero. Vilora knows nothing about the user — their communication style, their values, their history, their relationships, what matters to them, or what they've worked through before. Every interaction feels like meeting a new mediator for the first time.

This is the opposite of what makes mediation effective in the real world. The best mediators, therapists, and advisors are effective precisely because they *know* you — they remember what you've struggled with, what triggers you, what your values are, how you communicate under stress, and what resolution looks like for you specifically.

**The vision:** Over time, users should feel like Vilora genuinely knows them — the way a trusted family member, close friend, or longtime therapist would. Not in a surveillance way, but in a "you really get me" way that makes the mediation more insightful, the framing more attuned, and the guidance more personally relevant.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                   USER MEMORY SYSTEM                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  MEMORY TYPES                                                   │
│  ├── Profile — Who they are (role, relationships, values)       │
│  ├── Communication Style — How they express themselves          │
│  ├── History — What they've mediated and what happened          │
│  ├── Patterns — Recurring themes, triggers, growth areas        │
│  └── Preferences — How they want Vilora to interact             │
│                                                                 │
│  MEMORY SOURCES                                                 │
│  ├── Session transcripts (post-session extraction)              │
│  ├── Intake perspectives (what they share upfront)              │
│  ├── Framing interactions (how they describe issues)            │
│  ├── Explicit user input (profile, preferences)                 │
│  └── Cross-session patterns (AI-detected over time)             │
│                                                                 │
│  MEMORY CONSUMERS                                               │
│  ├── Mediation engine (personalized facilitation)               │
│  ├── Framing assistant (attuned suggestions)                    │
│  ├── Welcome messages (warm, personal greetings)                │
│  ├── Session summaries (context-aware insights)                 │
│  └── Proactive check-ins (follow-up on past sessions)           │
│                                                                 │
│  PRIVACY & CONTROL                                              │
│  ├── User can view all memories Vilora has about them           │
│  ├── User can edit or delete any memory                         │
│  ├── User can pause memory collection                           │
│  ├── Memories are never shared with other participants          │
│  └── Clear data retention and deletion policies                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## What Vilora Should Learn (Memory Categories)

### 1. Profile Context

Things that help Vilora understand who the user is and what world they live in.

- **Relationships:** "Has a partner named Sarah," "Has two kids (ages 8 and 12)," "Works with a business partner named James"
- **Life context:** "Works in finance, long hours," "Recently moved to a new city," "Caretaker for aging parent"
- **Values:** "Family time is very important," "Values fairness and directness," "Conflict-averse, tends to avoid confrontation"
- **Cultural context:** "Appreciates direct communication," "Prefers a gentle, indirect approach"

*These are explicitly shared or clearly implied by the user. Vilora should never infer sensitive attributes (race, religion, politics, health) unless the user directly shares them.*

### 2. Communication Style

How the user expresses themselves and what works for them.

- **Expression patterns:** "Tends to write long, detailed messages," "Uses humor to deflect tension," "Gets to the point quickly"
- **Emotional patterns:** "Gets defensive when they feel blamed," "Shuts down when overwhelmed," "Opens up more after being validated"
- **Preferred Vilora tone:** "Responds well to warmth," "Prefers Vilora to be more direct," "Likes when Vilora uses metaphors"

### 3. Session History & Outcomes

What they've worked through and what happened.

- **Past topics:** "Mediated household chores with partner (March 2026) — reached agreement on shared calendar"
- **Resolutions:** "Agreed to weekly check-ins with roommate about noise"
- **Unresolved:** "Workplace conflict with manager — session ended without clear resolution"
- **Follow-up:** "Chore agreement lasted 2 weeks then fell apart — user mentioned in next session"

### 4. Patterns & Growth

Recurring themes that Vilora notices across sessions.

- **Recurring themes:** "Fairness and feeling unheard come up frequently," "Boundary-setting is a common challenge"
- **Growth:** "Has gotten better at using I-statements since first session," "More willing to hear the other side compared to early sessions"
- **Triggers:** "Feels strongly when contributions are minimized," "Reacts to perceived dismissiveness"

### 5. Preferences

How they want Vilora to behave.

- **Interaction style:** "Prefers Vilora to check in less frequently during sessions," "Likes detailed summaries," "Wants Vilora to be more challenging, not just supportive"
- **Privacy:** "Doesn't want Vilora to reference past sessions unless asked," "Comfortable with Vilora bringing up patterns"

---

## Implementation Plan

### Phase 1: Memory Infrastructure & Post-Session Extraction

**Goal:** Build the memory storage system and begin learning from completed sessions.

#### 1.1 Database Schema

```sql
CREATE TABLE user_memories (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    category TEXT NOT NULL,           -- profile, communication, history, pattern, preference
    content TEXT NOT NULL,            -- the memory itself (natural language)
    source_type TEXT NOT NULL,        -- session, intake, framing, explicit, ai_detected
    source_session_id INTEGER,        -- which session it came from (nullable)
    confidence REAL DEFAULT 1.0,      -- how confident Vilora is (0.0–1.0)
    active BOOLEAN DEFAULT TRUE,      -- user can deactivate without deleting
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_memories_user ON user_memories(user_id, active);
CREATE INDEX idx_user_memories_category ON user_memories(user_id, category);
```

#### 1.2 Memory Extraction Engine

After a session ends (or when summary is generated), run an AI extraction pass:

- Input: full session transcript + existing memories for this user
- Prompt Claude to extract new memories in each category
- Compare against existing memories — update if refined, skip if duplicate
- Store with `source_type='session'` and link to the session

**Extraction prompt strategy:**
```
Given this mediation session transcript and the user's existing memory profile,
extract any NEW insights about this user. Only extract things that would be
genuinely useful for future mediations. Do not extract trivial details.

For each memory, provide:
- category (profile/communication/history/pattern/preference)
- content (the insight, in natural language)
- confidence (0.0-1.0, how clearly this was demonstrated)

Existing memories (do not duplicate):
{existing_memories}

Session transcript:
{transcript}
```

#### 1.3 Memory Retrieval API

- `GET /api/user/memories` — returns all active memories for the current user
- Grouped by category for display
- Used internally by the mediation engine to build personalized context

### Phase 2: Personalized Mediation

**Goal:** Inject user memory into Vilora's mediation responses so they feel personal and attuned.

#### 2.1 Memory-Augmented System Prompt

When mediating, include relevant memories in the system prompt:

```
## What you know about {user_name}:

**About them:** {profile memories}
**Communication style:** {communication memories}
**Past mediations:** {history memories}
**Patterns you've noticed:** {pattern memories}
**Their preferences for how you interact:** {preference memories}

Use this knowledge naturally — don't explicitly reference it unless
it's directly relevant. The goal is for your responses to feel attuned
and personal, like a mediator who genuinely knows this person.
Never reveal one participant's memories to the other participant.
```

#### 2.2 Memory-Aware Framing

When the user clicks "Help me frame this," include their profile in the framing prompt:

- "This user values directness — keep the framing straightforward"
- "This user has mediated a similar issue before (chore division, March 2026) — acknowledge their experience"
- "This user tends to minimize their own feelings — gently encourage them to name what they need"

#### 2.3 Personalized Welcome Messages

When a returning user creates a new session:

- Reference progress: "Welcome back. I remember you worked through the household chores issue — how has that been going?"
- Acknowledge growth: "I've noticed you've gotten more comfortable expressing your needs directly — that's great progress."
- Connect themes: "This sounds related to the boundary-setting challenges we've explored before."

*Only do this when it feels natural and helpful, not forced. The user can disable this in preferences.*

### Phase 3: Explicit Memory Input & User Control

**Goal:** Let users tell Vilora about themselves directly, and give them full control over what Vilora remembers.

#### 3.1 "About Me" Profile Page

A dedicated page where users can:

- Write a free-form bio/context ("tell Vilora about yourself")
- See all memories Vilora has extracted, organized by category
- Edit any memory's content
- Deactivate or delete individual memories
- Toggle "pause memory collection" (stops AI extraction, keeps existing)

#### 3.2 In-Session Memory Controls

- User can say "remember that..." or "don't remember this" during sessions
- Vilora acknowledges and acts accordingly
- "Forget" commands immediately deactivate the relevant memory

#### 3.3 Onboarding Memory Prompt

For new users, after their first session, offer an optional "Help Vilora get to know you" flow:

- "What kind of relationships do you most often need help navigating?"
- "How would you describe your communication style?"
- "Is there anything you'd like Vilora to know about you that would help in future sessions?"
- All optional, skippable, and editable later

### Phase 4: Cross-Session Pattern Detection

**Goal:** Vilora proactively identifies patterns across a user's sessions over time.

#### 4.1 Periodic Pattern Analysis

After every 3-5 sessions, run a pattern detection pass:

- Input: all session histories + existing patterns
- Look for: recurring themes, growth areas, persistent challenges, relationship dynamics
- Update pattern memories with increased confidence as patterns repeat
- Lower confidence for patterns that haven't appeared recently

#### 4.2 Proactive Insights

When appropriate, Vilora can surface insights:

- "I've noticed that feeling unheard comes up in several of your mediations. Would it be helpful to explore that pattern?"
- "You've been doing a really good job of staying curious instead of defensive — I've seen a real shift over your last few sessions."

*Always optional, never pushy. The user controls whether Vilora offers proactive insights.*

### Phase 5: Relationship Memory (Multi-Party Awareness)

**Goal:** Vilora understands the relationships between participants, not just individuals.

#### 5.1 Relationship Context

When two users have mediated together before:

- Vilora remembers their dynamic, past agreements, and unresolved issues
- Can reference past progress: "Last time, you both agreed to a weekly check-in — has that been happening?"
- Understands their communication patterns together (not just individually)

#### 5.2 Relationship Memory Schema

```sql
CREATE TABLE relationship_memories (
    id SERIAL PRIMARY KEY,
    user_a_id INTEGER NOT NULL REFERENCES users(id),
    user_b_id INTEGER NOT NULL REFERENCES users(id),
    content TEXT NOT NULL,
    source_session_id INTEGER REFERENCES mediation_sessions(id),
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

*Both participants must have memory collection enabled. Either can delete relationship memories.*

---

## Privacy & Ethics — Core Principles

This feature deals with sensitive personal information. These principles are non-negotiable:

### Transparency
- Users can always see everything Vilora remembers about them
- No hidden or system-only memories
- Clear explanation of what data is collected and why

### Control
- Users can edit, deactivate, or delete any memory at any time
- Users can pause all memory collection
- Users can export their memory data
- Users can delete all memories permanently ("forget everything about me")

### Boundaries
- Memories are NEVER shared between participants
- Vilora never reveals what one person said in a private intake to the other
- Vilora never uses memories to manipulate or take sides
- Vilora never infers sensitive attributes (health, politics, religion, sexuality) unless explicitly shared
- If a memory might be wrong, Vilora asks rather than assumes

### Data Handling
- Memories are stored encrypted at rest
- Memories are excluded from any analytics or training data
- Clear retention policy (e.g., inactive memories auto-archive after 12 months)
- Account deletion removes all memories permanently

### Therapeutic Boundary
- Vilora is a mediator, not a therapist
- Memory-informed responses should feel personal and attuned, but Vilora should never:
  - Diagnose or pathologize behavior patterns
  - Provide mental health advice
  - Claim to understand someone's psychology
  - Make users feel surveilled or analyzed
- The tone should be: "I remember what you've told me" not "I've been analyzing you"

---

## How Memory Changes the Experience

### First Session (No Memory)
> "Welcome to Vilora. I'm here to help you work through this together."

### Third Session (Some Memory)
> "Welcome back. I can see this session is about a workplace issue — I remember you mentioned in a past session that directness is important to you, so I'll keep my facilitation straightforward."

### Tenth Session (Deep Memory)
> "I've noticed that feeling heard is a recurring theme across several of your mediations — and I've also seen you get much better at expressing your needs clearly. That growth matters. Let's bring that same openness to this conversation."

### Framing with Memory
Without memory:
> "Here's a neutral framing of your issue..."

With memory:
> "Based on what you've shared with me over time, I know fairness is a core value for you. Here's a framing that centers that without putting the other person on the defensive — since I know you tend to soften your own needs, I kept your perspective a bit more direct than what you wrote."

---

## Success Criteria

| Criteria | Measurement |
|----------|-------------|
| Memories feel accurate | Users rarely need to correct or delete extracted memories |
| Personalization feels natural | Users report Vilora "gets them" in feedback |
| No creepy factor | Users feel in control, not surveilled |
| Returning users engage more | Higher session creation rate for users with 3+ sessions |
| Privacy controls work | Users can view, edit, delete, and pause memory easily |
| Memory improves mediation quality | Returning user sessions show faster progress toward resolution |
| Cross-session patterns are useful | Users find pattern insights relevant and actionable |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Memories are wrong/outdated | Confidence scoring + user can correct; Vilora asks before acting on low-confidence memories |
| Users feel surveilled | Transparent memory page; warm framing ("what you've told me"); easy opt-out |
| Memories reveal private info | Strict per-user isolation; never shared across participants |
| Over-personalization feels forced | Vilora uses memory subtly; never forces references; user controls proactiveness |
| Data breach exposes memories | Encryption at rest; minimal retention; memory export/deletion |
| Therapeutic boundary creep | Clear guidelines in system prompt; Vilora acknowledges limits; refer to professionals when appropriate |

---

## References

- **Design Reference:** `developer-guides/architecture/design-reference.md`
- **Mediation Engine:** `mediation/engine.py` — System prompt and response generation
- **Framing Assistant:** `mediation/engine.py` → `frame()` method
- **Database:** `models/database.py` — Schema patterns for SQLite/PostgreSQL dual support
- **Privacy patterns:** Memory viewing, editing, and deletion modeled after GDPR right-to-access and right-to-erasure

---

## Changelog

| Date | Change |
|------|--------|
| 2026-03-30 | Initial creation — five-phase memory and personalization system |
