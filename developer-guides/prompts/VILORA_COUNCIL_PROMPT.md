# Vilora Council: Multi-Perspective Decision Support

**Created:** April 2, 2026
**Last Updated:** April 8, 2026
**Status:** Implemented
**Dependencies:** Mediation engine, session infrastructure
**Priority:** High. Core differentiator that leverages AI's unique ability to argue with itself
**Design Reference:** `developer-guides/architecture/design-reference.md`

---

## Problem Statement

When people ask for advice, they frame the question in a way that reflects their existing assumptions, emotional lean, and biases. AI is naturally agreeable and will often confirm whatever angle the user brings.

Ask Vilora "should I take this job?" and it'll find reasons to say yes. Ask "is this job a bad idea?" and it'll find reasons to say no. Same situation, different framing, opposite answers. That's fine for casual conversation but dangerous for real decisions.

The Vilora Council solves this by forcing multiple distinct thinking styles onto the same question. Five advisors analyze the situation from fundamentally different angles, then anonymously review each other's blind spots. The result is a synthesized recommendation that no single perspective could produce.

**Inspiration:** Andrej Karpathy's LLM Council concept (polling multiple models and having them peer-review each other), adapted to run entirely within Vilora using sub-prompts with distinct thinking styles rather than different models.

---

## The Five Advisors

### 1. The Contrarian
**Role:** Assumes the idea has a fatal flaw and tries to find it.

**Prompt persona:** "You are a skeptical advisor who looks for what will fail. Your job is to find the weakest points in this plan, idea, or decision. If everything looks solid on the surface, dig deeper. You're not being negative for the sake of it. You're protecting the person from the blind spots that come with enthusiasm. What risks are being underestimated? What could go wrong that nobody is talking about?"

**Catches:** The "this sounds great but have you thought about..." gaps people skip when they're excited.

### 2. The First Principles Thinker
**Role:** Ignores the question as framed and asks what the user is actually trying to solve.

**Prompt persona:** "You strip away assumptions and rebuild the problem from the ground up. Don't accept the question at face value. Ask: what is the real goal here? Is this the right question to be asking? Are there hidden assumptions baked into the framing? Sometimes the best answer is that the question itself needs to change."

**Catches:** "You're optimizing the wrong variable entirely." Happens more often than people think.

### 3. The Expansionist
**Role:** Hunts for upside the user is missing.

**Prompt persona:** "You look for what could be bigger, better, or more ambitious. What adjacent opportunity is sitting right next to this question that the person hasn't noticed? What would this look like if there were no constraints? Where is the hidden leverage? Your job is to stretch the thinking beyond the obvious."

**Catches:** "You're thinking too small." The opportunity cost of settling for the first decent option.

### 4. The Outsider
**Role:** Has zero context about the user, their field, or their history.

**Prompt persona:** "You respond purely to what's in front of you with no insider knowledge. You don't know the jargon, the industry norms, or the 'way things are usually done.' This is your strength. Ask the obvious questions that experts forget to ask. Point out things that seem strange to a fresh pair of eyes. What would a smart person with no background in this area notice?"

**Catches:** The curse of knowledge. Things obvious to the user but invisible to their audience, customers, or collaborators.

### 5. The Executor
**Role:** Only cares about one thing: what do you do Monday morning?

**Prompt persona:** "You focus exclusively on actionability. If an idea sounds brilliant but has no clear first step, say so. What is the smallest concrete action that would move this forward? What needs to happen first, second, third? Cut through analysis paralysis. A mediocre plan executed today beats a perfect plan discussed forever."

**Catches:** Brilliant plans with no path to actually doing them. Which is most of them.

---

## How It Works

### Step 1: User Triggers the Council
User can invoke the Council in two ways:
- **From a session:** Click a "Get Council Input" button (available in both personal and group sessions)
- **As a new session type:** "Get the Council's take" option in session creation

The user provides their question with as much context as possible. Richer input produces sharper output.

### Step 2: Five Advisors Analyze in Parallel
Vilora spawns 5 parallel API calls, each with a different advisor persona in the system prompt. All receive the same user question and context. Each produces an independent analysis (300-500 words).

### Step 3: Anonymous Peer Review
After all 5 responses come back:
1. Vilora anonymizes the responses (shuffles which advisor maps to which letter: A, B, C, D, E)
2. Runs a review pass with 3 questions:
   - Which response is strongest and why?
   - Which has the biggest blind spot?
   - What did all five miss?

The "what did all five miss?" question is the most valuable. When you read 5 perspectives side by side, the gap between them reveals what nobody thought to mention.

### Step 4: Chairman Synthesis
A final API call reads all 5 advisor responses plus the peer review and produces:
1. **Key insights** from each perspective (1-2 sentences each)
2. **Points of agreement** across advisors
3. **Points of tension** where advisors disagree and why
4. **The blind spot** (what all five missed, from the peer review)
5. **Recommendation** with confidence level
6. **One concrete next step** (the Executor's influence)

### Step 5: Display to User
The Council output is displayed as a structured, readable report within the session. The user can:
- Read the full synthesis
- Expand individual advisor responses to see the full reasoning
- Continue the conversation with follow-up questions
- Ask the Council to re-evaluate with new information

---

## Architecture

```
User Question + Context
         |
         v
┌────────────────────────────────────────────┐
│           5 Parallel API Calls              │
│                                             │
│  Contrarian  First Principles  Expansionist │
│     |              |               |        │
│  Outsider      Executor                     │
│     |              |                        │
└────────┬───────────┬───────────┬────────────┘
         |           |           |
         v           v           v
    Response A   Response B   Response C ...
         |           |           |
         v           v           v
┌────────────────────────────────────────────┐
│        Anonymize + Peer Review              │
│  - Strongest response?                      │
│  - Biggest blind spot?                      │
│  - What did all five miss?                  │
└────────────────┬───────────────────────────┘
                 |
                 v
┌────────────────────────────────────────────┐
│        Chairman Synthesis                   │
│  - Key insights per advisor                 │
│  - Agreement / tension points               │
│  - The blind spot                           │
│  - Recommendation + confidence              │
│  - One concrete next step                   │
└────────────────────────────────────────────┘
                 |
                 v
         Display in Session
```

---

## Implementation Plan

### Phase 1: Core Council Engine

#### 1.1 Council Method in MediationEngine

Add `run_council(question, context, user_memories)` to `mediation/engine.py`:
- Accepts the user's question and optional context
- Builds 5 advisor prompts with distinct personas
- Runs 5 parallel API calls (use Python threading or async)
- Collects all 5 responses
- Runs the anonymized peer review call
- Runs the chairman synthesis call
- Returns structured result

#### 1.2 API Endpoint

`POST /api/council`
- Accepts `{ question, context? }`
- Returns `{ success, council: { advisors: [...], review: {...}, synthesis: {...} } }`
- May take 15-30 seconds (multiple API calls). Consider:
  - Streaming the response
  - Or showing a progress indicator ("Advisor 1 of 5 thinking...")
  - Or running async and polling for results

#### 1.3 Parallel Execution

Since each advisor is independent, run all 5 API calls concurrently:

```python
from concurrent.futures import ThreadPoolExecutor

def run_council(self, question, context=None, user_memories=None):
    advisors = [
        ('Contrarian', CONTRARIAN_PROMPT),
        ('First Principles', FIRST_PRINCIPLES_PROMPT),
        ('Expansionist', EXPANSIONIST_PROMPT),
        ('Outsider', OUTSIDER_PROMPT),
        ('Executor', EXECUTOR_PROMPT),
    ]

    full_question = f"Question: {question}"
    if context:
        full_question += f"\n\nContext: {context}"

    def get_response(name, system):
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": full_question}]
        )
        return (name, response.content[0].text)

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(get_response, name, prompt)
                   for name, prompt in advisors]
        results = [f.result() for f in futures]

    # Anonymize and peer review
    review = self._peer_review(results)

    # Chairman synthesis
    synthesis = self._synthesize(question, results, review)

    return {
        'advisors': [{'name': name, 'response': resp} for name, resp in results],
        'review': review,
        'synthesis': synthesis
    }
```

### Phase 2: Session Integration

#### 2.1 "Get Council Input" Button

Add a button in the session room (next to "Get Summary"):
- In personal sessions: "Ask the Council"
- In group sessions: "Get Council Input"

Clicking opens a modal where the user can:
- Frame a specific question for the Council
- Optionally add context beyond what's in the session
- The session transcript is automatically included as context

#### 2.2 Council as a Session Type

Add "Get the Council's take" as a fourth option in the session creation chooser:
- Single textarea for the question
- Optional context field
- No invite link (it's a personal analysis tool)
- Results displayed in a structured layout, not as chat messages

#### 2.3 Council Results Display

The council output should be displayed in a dedicated panel (similar to the summary panel) with:
- **Synthesis section** at the top (recommendation + next step)
- **Collapsible advisor sections** (click to expand each advisor's full response)
- **Peer review findings** (strongest, blind spot, what was missed)
- **"Ask a follow-up"** button to continue the conversation with the Council's output as context

### Phase 3: Refinements

#### 3.1 Custom Advisors

Let users configure which advisors to include:
- Toggle individual advisors on/off
- Add custom advisor personas ("The Ethicist," "The Customer," "The Regulator")
- Save advisor configurations as presets

#### 3.2 Domain-Specific Councils

Pre-built advisor configurations for common use cases:
- **Startup Council:** Contrarian, Market Analyst, Technical Feasibility, Customer Advocate, Investor
- **Career Council:** Risk Assessor, Values Alignment, Long-term Thinker, Practical Advisor, Industry Insider
- **Creative Council:** Critic, Audience Member, Innovator, Traditionalist, Producer

#### 3.3 Council History

Store council results and let users:
- Review past council sessions
- Re-run with updated context
- Compare how the council's take changed over time

---

## API Cost Considerations

Each council invocation requires 7 API calls:
- 5 advisor responses
- 1 peer review
- 1 chairman synthesis

At ~1000 tokens per call, this is roughly 7x the cost of a single Vilora response. Consider:
- Making the Council a premium feature if/when monetizing
- Caching council results (like summaries)
- Allowing users to select fewer advisors (3 instead of 5) for lighter analysis

---

## Success Criteria

| Criteria | Measurement |
|----------|-------------|
| Council produces meaningfully different perspectives | Advisors don't just rephrase the same answer |
| Peer review catches real blind spots | "What did all five miss?" generates novel insights |
| Users find the Council more useful than a single response | Qualitative feedback, repeat usage |
| Execution time is acceptable | Full council completes in under 30 seconds |
| Results are actionable | Users can identify a clear next step from the synthesis |

---

## References

- **Inspiration:** Andrej Karpathy's LLM Council concept
- **Mediation Engine:** `mediation/engine.py`
- **Session Infrastructure:** `app.py`, `models/database.py`
- **Design Reference:** `developer-guides/architecture/design-reference.md`

---

## Changelog

| Date | Change |
|------|--------|
| 2026-04-02 | Initial creation. Five-advisor council with peer review and synthesis. |
| 2026-04-08 | Status updated to Implemented |

---

## Implementation Summary

Five specialized advisor personas implemented: Contrarian, First Principles Thinker, Expansionist, Outsider, and Executor. Each advisor analyzes the user's question independently via parallel API calls. Advisors peer-review each other's responses (anonymized). A final chairman synthesis produces key insights, points of agreement/tension, blind spots, and a concrete next step. Results are stored in the council_results database table. "Ask the Council" button is available in the session UI for both personal and group sessions.
