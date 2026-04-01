# User Memory & Personalization -- Vilora Learns Who You Are

**Created:** March 30, 2026
**Updated:** April 1, 2026
**Status:** Phases 1-3 Implemented; Phases 4-5 Planned
**Dependencies:** None
**Priority:** High -- Core differentiator; transforms Vilora from a tool into a trusted advisor
**Design Reference:** developer-guides/architecture/design-reference.md

---

## Problem Statement

Today, every Vilora session starts from zero. Vilora knows nothing about the user -- their communication style, their values, their history, their relationships, what matters to them, or what they have worked through before.

This is the opposite of what makes mediation effective in the real world. The best mediators, therapists, and advisors are effective precisely because they *know* you -- they remember what you have struggled with, what triggers you, what your values are, how you communicate under stress, and what resolution looks like for you specifically.

**The vision:** Over time, users should feel like Vilora genuinely knows them -- the way a trusted family member, close friend, or longtime therapist would. Not in a surveillance way, but in a "you really get me" way that makes the mediation more insightful, the framing more attuned, and the guidance more personally relevant.

---

## Architecture Overview

**Memory Types:** Profile, Communication Style, History, Patterns, Preferences

**Memory Sources:** Session transcripts, Intake perspectives, Framing interactions, Explicit user input (About Me / Settings / onboarding), Per-session tone chips, Cross-session patterns (AI-detected)

**Memory Consumers:** Mediation engine, Counseling engine, Framing assistant, Welcome messages, Session summaries, Proactive check-ins

**Personalization Layers:**
- Global Settings -- persistent preferences stored as preference-category memories
- Per-Session Tone -- approach chips selected when starting a session, injected into intake message
- Learned Knowledge -- AI-extracted insights from sessions

**Privacy & Control:** Full user visibility, edit/delete any memory, pause collection, never shared between participants

---

## What Vilora Should Learn (Memory Categories)

### 1. Profile Context
Who the user is: relationships, life context, values, cultural context. Only from explicit sharing -- never infer sensitive attributes.

### 2. Communication Style
Expression patterns, emotional patterns, preferred Vilora tone.

### 3. Session History & Outcomes
Past topics, resolutions, unresolved issues, follow-ups.

### 4. Patterns & Growth
Recurring themes, growth areas, triggers -- noticed across sessions.

### 5. Preferences
Set via Settings page (global defaults) and per-session tone chips (overrides): Interaction goal, communication style, response length, custom instructions.

---

## Current Implementation Status

### Phase 1: Memory Infrastructure & Post-Session Extraction -- IMPLEMENTED

**Database Schema** (models/database.py): user_memories table with id, user_id, category, content, source_type, source_session_id, confidence, active, timestamps. Supports SQLite and PostgreSQL.

**Memory Extraction Engine** (mediation/engine.py -> extract_memories()): Runs on summary generation. Loads transcripts + existing memories, prompts Claude to extract new insights, deduplicates, stores with source_type=session. Extracts for ALL participants.

**Memory API** (app.py): GET/POST/PUT/DELETE endpoints for user memories with soft-delete support.

### Phase 2: Personalized Mediation -- IMPLEMENTED

**Memory-Augmented System Prompt** (mediate()): Loads memories for every participant, injects as labeled sections per user. Safeguard: NEVER reveal one participant's memories to another.

**Memory-Aware Framing** (frame()): User memories included in framing prompt for attuned suggestions.

**Personalized Welcome Messages** (welcome()): Uses session context including tone instructions.

### Phase 3: Explicit Memory Input & User Control -- IMPLEMENTED

**About Me Page** (templates/about_me.html, /about-me): View, edit, remove, add memories. Organized by category. AI-detected vs explicit labels.

**Onboarding Flow**: 5-step wizard -- About you, Relationships, Work, Conflict style, Values. All optional. Pre-populates on update via reverse-matching stored memories against field templates. Smart save (update/create/delete, no duplicates). Contextual header actions (banner before onboarding, buttons after).

**Settings Page** (templates/settings.html, /settings): Global defaults saved as preference memories.
- What I am usually looking for: Help me think it through / Give me direct advice / Mostly just listen / Challenge my thinking (single-select)
- Communication style: Warm and supportive / Straightforward and direct / Calm and balanced (single-select)
- Response length: Brief / Moderate / Thorough (single-select)
- Things to keep in mind: Free-form textarea for custom instructions
- Saves immediately with confirmation toast.

**Per-Session Tone Chips** (templates/dashboard.html): Multi-select, override/layer on global settings.

Personal session (Talk to Vilora) chips: Quick advice, Help me explore, Just listen, Devil's advocate, Expand my perspective, Action plan

Mediation session chips (in both Help me frame it and direct form): Find common ground, Improve communication, Get to resolution, Make sure we're heard, Set boundaries, Keep things calm

How tone flows through the system:
1. Selected tones joined as tone field in API payload
2. Backend prepends [Session tone: ...] to perspective/intake message
3. Intake message is first in conversation, so Claude sees tone in context for all mediate() calls
4. welcome() recognizes tone tag and follows closely

Framing-to-mediation handoff: Tone selections carry over automatically.

Hint below chips links to Settings page for further customization.

**Session Title Generation** (generate_title()): For personal sessions, generates short title (under 60 chars) via Claude. Full text goes to intake message. Migration: python app.py fix-titles.

---

## How It All Fits Together

1. User types message + optionally selects tone chips
2. Session created; tone prepended to intake message
3. Vilora responds -- engine loads: system prompt + all participant memories (including Settings prefs) + full conversation history (includes tone)
4. Claude sees BOTH global preferences AND session tone; session tone takes priority
5. On summary generation, new memories extracted for each participant

**Multi-party awareness:** In mediation sessions, Vilora loads memories for BOTH users separately. If User B joins User A's session and has their own Vilora history/settings, Vilora is attuned to both individually without leaking information.

---

## Remaining Implementation

### Phase 4: Cross-Session Pattern Detection -- PLANNED
Periodic pattern analysis after every 3-5 sessions. Proactive insights surfaced when appropriate (always optional, never pushy).

### Phase 5: Relationship Memory -- PLANNED
Track dynamics between participants who have mediated together before. Relationship memory table linking two users. Either participant can delete.

---

## Privacy & Ethics

- Full transparency: users see everything Vilora remembers
- Full control: edit, delete, pause, export, full deletion
- Strict isolation: memories never shared between participants
- No inference of sensitive attributes unless explicitly shared
- Therapeutic boundary: mediator/counselor, not therapist

---

## Key Files

| File | Purpose |
|------|---------|
| models/database.py | user_memories table, MediationSession model |
| mediation/engine.py | mediate(), welcome(), frame(), generate_title(), extract_memories(), _build_memory_context() |
| app.py | Memory CRUD API, session creation with tone, memory extraction on summary |
| templates/about_me.html | About Me page, onboarding, memory management |
| templates/settings.html | Settings page with preference chips |
| templates/dashboard.html | Session creation modals with tone chips |
| templates/session.html | Chat interface with voice input |
| templates/base.html | Navigation (Dashboard, About Me, Settings) |
| static/js/voice.js | Shared voice input via Web Speech API |
| static/css/style.css | All related styles |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-03-30 | Initial creation -- five-phase plan |
| 2026-03-31 | Phases 1-2 implemented -- memory infra, extraction, personalized mediation |
| 2026-03-31 | Phase 3 partial -- About Me page with onboarding, memory CRUD |
| 2026-04-01 | About Me buttons refined, onboarding update flow with pre-population |
| 2026-04-01 | Personal session UX -- consolidated inputs, short generated titles |
| 2026-04-01 | Settings page -- global preference chips + custom instructions |
| 2026-04-01 | Per-session tone chips -- multi-select for personal and mediation |
| 2026-04-01 | Tone chips added to framing modal with carry-over to review form |
| 2026-04-01 | Voice input -- Web Speech API mic buttons on all textareas |
| 2026-04-01 | Loading states on all session creation buttons |
| 2026-04-01 | Chat polling fix -- skip re-render when text selected |
