# Master Development Plan

*Created: February 1, 2026*
*Last Updated: February 13, 2026*
*Status: Active*

---

## Reference Documents

| Document | Purpose |
|----------|---------|
| `COMPETITIVE_ANALYSIS.md` | Market positioning, feature differentiation, Option C goals |
| `strategy-suggestions.md` | Strategy Suggestion Engine architecture and roadmap |
| `active/AI_COACH_UPGRADE_PROMPT.md` | Core coaching system improvements |
| `active/SOLVER_RANGE_USE_PROMPT.md` | Solver-based preflop range implementation |
| `active/AI_COACH_TRAINING_MODULE_PROMPT.md` | Self-improving AI coach via LLM review |
| `active/RANGE_BASED_EQUITY_PROMPT.md` | Equity calculation vs villain ranges |
| `active/STACK_DEPTH_AND_TABLE_SIZE_RANGES_PROMPT.md` | HU, short-handed, stack depth ranges |
| `active/POSTFLOP_RANGE_COACHING_PROMPT.md` | **Solver-based postflop coaching (critical)** |
| `active/SCORING_SYSTEM_PROMPT.md` | Performance tracking by street/position |
| `active/GTO_RANGE_GENERATION_PLAN.md` | Proprietary solver range generation |
| `planned/ADJUSTABLE_OPPONENT_PROFILES_PROMPT.md` | Customizable AI opponent play styles |
| `active/QUICK_HAND_INPUT_PROMPT.md` | Scenario builder for targeted practice |
| `planned/STREET_FOCUS_PRACTICE_PROMPT.md` | Focus practice on specific streets |

---

## Vision Statement

Build **"The Complete Platform"** - the most comprehensive AI poker training platform that provides:
- Real-time coaching during simulated play
- GTO-based decision analysis with solver-derived ranges
- Personalized weakness identification and focused practice
- Self-improving coaching that learns from user feedback

See `COMPETITIVE_ANALYSIS.md` → "Our Positioning (Goal)" for full positioning details.

---

## Development Phases Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     DEVELOPMENT ROADMAP                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PHASE 1: FOUNDATION (COMPLETE)                                              │
│  ├── AI Coach Upgrade (game-type, player count, PLO)         ✅ Complete    │
│  ├── Solver Range Use (preflop position-vs-position)         ✅ Complete    │
│  └── AI Coach Training Module (self-improvement)             ✅ Complete    │
│                                                                              │
│  PHASE 2: COACHING QUALITY (CRITICAL - COMPLETE)                             │
│  ├── Range-Based Equity (vs villain range, not random)       ✅ Complete    │
│  ├── Stack Depth & Table Size Ranges (HU, 10bb-200bb)        ✅ Complete    │
│  └── Postflop Range Coaching (solver-based, not heuristic)   ✅ Complete    │
│                                                                              │
│  PHASE 3: COMMERCIAL PREP (PARALLEL TRACK)                                   │
│  └── Proprietary Solver Ranges & Multi-Street GTO            🔄 In Progress │
│                                                                              │
│  PHASE 4: PERSONALIZATION (IN PROGRESS)                                      │
│  ├── Scoring System (street, position, hand type tracking)   ✅ Complete    │
│  ├── Weakness Identification (leak detection)                🔲 New         │
│  └── Exploitability Alerts (pattern warnings)                🔲 New         │
│                                                                              │
│  PHASE 5: ENGAGEMENT (IN PROGRESS)                                            │
│  ├── Focused Practice (auto-generated drills)                🔲 New         │
│  └── Quick Hand Input (scenario builder)                     ✅ MVP Complete │
│                                                                              │
│  PHASE 6: POLISH (FUTURE)                                                    │
│  ├── Mobile App                                              🔲 Future      │
│  ├── Community Features                                      🔲 Future      │
│  └── Hand History Import                                     🔲 Future      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

⭐ = Critical for competitive positioning
```

---

## Feature Build Order

### Priority 1: Complete Foundation Features

| # | Feature | Prompt | Status | Dependencies | Notes |
|---|---------|--------|--------|--------------|-------|
| 1 | ~~AI Coach Upgrade (P1-3)~~ | `AI_COACH_UPGRADE_PROMPT.md` | ✅ Complete | None | Game-type routing, player count, PLO |
| 2 | ~~Solver Range Use~~ | `SOLVER_RANGE_USE_PROMPT.md` | ✅ Complete | AI Coach Upgrade | Position-vs-position preflop ranges |
| 3 | ~~AI Coach Training Module~~ | `AI_COACH_TRAINING_MODULE_PROMPT.md` | ✅ Complete | Solver Ranges | Self-improvement via LLM review |

### Priority 2: Core Coaching Quality

| # | Feature | Prompt | Status | Dependencies | Notes |
|---|---------|--------|--------|--------------|-------|
| 4 | ~~Range-Based Equity~~ | `RANGE_BASED_EQUITY_PROMPT.md` | ✅ Complete | Solver Range Use ✅ | Equity vs villain range, not random |
| 4a | ~~Stack Depth & Table Size Ranges~~ | `STACK_DEPTH_AND_TABLE_SIZE_RANGES_PROMPT.md` | ✅ Complete | Range-Based Equity ✅ | HU, short-handed, 10bb-200bb ranges |
| 4b | Postflop Range Narrowing | `POSTFLOP_RANGE_NARROWING_PROMPT.md` | Phase 1+1b ✅ | Postflop Coaching ✅, Solver Data ✅ | Narrows villain range by postflop actions |
| 5 | ~~Postflop Range Coaching~~ | `POSTFLOP_RANGE_COACHING_PROMPT.md` | ✅ Complete | Board texture classification | Solver-based postflop with range viewer |

> **Note on Feature #5:** Core implementation complete. Includes board texture classification, postflop range API, unified range viewer, and vulnerable hand detection. Remaining: turn/river data, 3-bet pots.

### Priority 3: Commercial Preparation (Parallel Track)

| # | Feature | Prompt | Status | Dependencies | Notes |
|---|---------|--------|--------|--------------|-------|
| 6 | **Proprietary Solver Ranges & Multi-Street GTO** | `GTO_RANGE_GENERATION_PLAN.md` | 🔄 In Progress | GTO+ (configured) | Phases 1-2 + 2c complete (36 flop files); Phase 4a turn complete (93 turn files) |

> **Note:** Feature #6 runs in parallel with coding work. **Phases 1-2 SRP flop complete** (all 9 textures, 19 solves, multi-board averaging). **Phase 2c COMPLETE** — IP facing OOP bet (36 total flop files). **Phase 4a COMPLETE (Feb 8)** — Turn check-check line extracted from all 19 solves across 63 turn cards (5 categories × 9 textures). 93 merged turn JSON files deployed to `ai/postflop_strategies/srp/turn/`. Engine classifies turn cards and looks up category-specific strategies. **Next:** Phase 4b (bet-call/check-bet-call turn lines), Phase 3 (3-bet pots). See `GTO_RANGE_GENERATION_PLAN.md` for the full data roadmap.

### Priority 4: Personalization Features

| # | Feature | Prompt | Status | Dependencies | Notes |
|---|---------|--------|--------|--------------|-------|
| 7 | **Scoring System** | `SCORING_SYSTEM_PROMPT.md` | ✅ Complete | None | Database, API, UI for tracking |
| 8 | **Weakness Identification** | *New prompt needed* | 🔲 New | Scoring System | Pattern detection from scores |
| 9 | **Exploitability Alerts** | *New prompt needed* | 🔲 New | Weakness ID | Warn when patterns are exploitable |

### Priority 5: Engagement Features

| # | Feature | Prompt | Status | Dependencies | Notes |
|---|---------|--------|--------|--------------|-------|
| 10 | **Street Focus Practice** | `planned/STREET_FOCUS_PRACTICE_PROMPT.md` | 🔲 Planned | Scoring System ✅ | Practice specific streets with auto-play |
| 11 | **Quick Hand Input** | `active/QUICK_HAND_INPUT_PROMPT.md` | ✅ Feature Complete | None | Scenario modal, card picker, multi-street coaching, hand library, Play It Out, Play All Hands |

### Priority 6: Future Enhancements

| # | Feature | Prompt | Status | Dependencies | Notes |
|---|---------|--------|--------|--------------|-------|
| 12 | Mobile App | *Future* | 🔲 Future | All core features | React Native or PWA |
| 13 | Community Features | *Future* | 🔲 Future | User accounts | Share hands, leaderboards |
| 14 | Hand History Import | *Future* | 🔲 Future | Quick Hand Input | PokerStars, GGPoker formats |
| 15 | **Adjustable Opponent Profiles** | `planned/ADJUSTABLE_OPPONENT_PROFILES_PROMPT.md` | 🔲 Planned | None | Customize AI villain play styles |
| 16 | **Database Backup & Persistence** | `planned/DATABASE_BACKUP_PROMPT.md` | 🔲 Planned | None | Automated backups, git-tracked seed, migration safety |

---

## Dependency Graph

```
                    ┌──────────────────────┐
                    │   AI Coach Upgrade   │
                    │     (P1-3) ✅        │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
    ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
    │  Solver Range   │ │ Scoring System  │ │  Proprietary    │
    │    Use ✅       │ │      🔲         │ │  Solver Ranges  │
    └────────┬────────┘ └────────┬────────┘ │      🔲         │
             │                   │          └─────────────────┘
    ┌────────┴────────┐          │           (PARALLEL TRACK)
    │                 │          │           Commercial requirement
    ▼                 ▼          │           Preflop + Postflop data
┌─────────────┐ ┌─────────────┐  │
│ Range-Based │ │  Postflop   │  │
│  Equity ✅  │ │   Range     │  │
└─────────────┘ │ Coaching ✅ │  │
                └──────┬──────┘  │
                       │         │
                       ▼         ▼
              ┌─────────────────────────────┐
              │      AI Coach Training      │
              │   (validates both) ✅       │
              └─────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────┐
                    │    Weakness     │
                    │ Identification  │
                    │      🔲         │
                    └────────┬────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
            ▼                ▼                ▼
 ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
 │ Exploitability  │ │ Focused         │ │ Quick Hand      │
 │   Alerts 🔲     │ │ Practice 🔲     │ │   Input ✅      │
 └─────────────────┘ └─────────────────┘ └─────────────────┘
```

### Parallel Work Streams

| Stream | Features | Notes |
|--------|----------|-------|
| **Coding Track A** | Range-Based Equity (#4) | Preflop equity fix |
| **Coding Track B** | Postflop Range Coaching (#5) | Major feature - solver-based postflop |
| **Coding Track C** | Scoring → Weakness ID → Drills | Personalization features |
| **Solver Track** | Proprietary Range Generation (#6) | Independent - runs solver software |
| **Independent** | Quick Hand Input, UI improvements | Can be done anytime |

> **Critical Path:** Postflop Range Coaching (#5) is the most impactful feature for coaching quality and competitive positioning. Consider prioritizing it.

---

## Detailed Feature Specifications

### Feature 4: Range-Based Equity

**Prompt:** `active/RANGE_BASED_EQUITY_PROMPT.md`
**Status:** ✅ Complete
**Dependencies:** Solver Ranges (Complete)
**Priority:** High - Fixes inaccurate equity feedback

**Problem:** Coach calculates equity vs random hands, not villain's range.

**Solution:** Calculate equity against villain's GTO range based on their position and actions.

**Deliverables:**
- `sample_hand_from_range()` in `hand_strength.py`
- `calculate_equity_vs_range()` in `hand_strength.py`
- `_get_villain_range()` in `gto_engine.py`
- Updated feedback messages

**Recent Improvements (Feb 2026):**
- Preflop equity now calculated vs opener's actual range using Monte Carlo simulation
- Display shows "~X% vs [position]" to clarify equity is range-adjusted
- Comprehensive fold explanations when pot odds suggest call but fold is correct:
  - **Facing open:** Position disadvantage, gappy/weak hands, poor playability
  - **Facing 3-bet/4-bet:** Domination risk, bad SPR, bloated pot concerns
  - Explains key concept of "equity realization" - why raw equity isn't enough

---

### Feature 4b: Postflop Range Narrowing

**Prompt:** `active/POSTFLOP_RANGE_NARROWING_PROMPT.md`
**Status:** Phase 1 + 1b Complete, Phase 2-3 Planned
**Dependencies:** Postflop Range Coaching (Complete), Solver Data (Complete)

**Problem:** AI Coach calculates equity against villain's full preflop range on all streets, even after villain's postflop actions narrow their range.

**Solution:** Use solver action frequencies as a Bayesian filter to weight villain's range based on their actions.

**Deliverables (Phase 1 + 1b — Complete):**
- `narrow_range_by_action()` in `postflop_ranges.py` — weights villain range by solver action frequencies
- `calculate_equity_vs_weighted_range()` in `hand_strength.py` — Monte Carlo equity with weighted sampling
- `_try_narrow_range()` in `gto_engine.py` — classifies texture, resolves villain position/action_faced
- Handles OOP-none, IP-check, and IP-bet_small (Phase 2c data) action contexts
- 15 tests (unit + integration with real solver data)

**Remaining:**
- Phase 2: Turn narrowing now works with Phase 4a turn data (check-check line). Cumulative multi-street narrowing still needs implementation.
- Phase 3: 3-bet pot narrowing (needs 3-bet pot solver data)

---

### Feature 5: Postflop Range Coaching ✅

**Prompt:** `active/POSTFLOP_RANGE_COACHING_PROMPT.md`
**Status:** ✅ Complete (Core)
**Dependencies:** Board texture classification
**Priority:** **Critical** - Essential for competitive positioning

**Problem:** Postflop coaching currently uses heuristics ("c-bet dry boards") instead of solver-derived strategies.

**Solution Implemented:**
1. Board texture classification (9 categories)
2. Postflop range data structures with fallback hand matching
3. Solver strategies stored by texture/position
4. Range-based feedback with vulnerable hand detection
5. Unified range viewer (preflop + postflop)

**Completed Deliverables:**
- `ai/board_analyzer.py` - Board classification system
- `ai/postflop_ranges.py` - Postflop range manager
- `ai/postflop_strategies/` - Solver-derived strategy data (JSON)
- `/api/ranges/postflop` - API endpoint
- `static/js/range-viewer.js` - Unified range viewer
- Vulnerable hand detection in `gto_engine.py` and `hand_strength.py`

**Remaining Work (Data Gaps - Code is Ready):**
- Turn strategy data for bet-call and check-bet-call flop lines (Phase 4b)
- River strategy data - code structure ready (Phase 5)
- 3-bet pot strategies - code supports pot_type parameter (Phase 3)

**Recent Improvements (Feb 2026):**
- Stats visibility now dynamic - only shows stats with hands (count > 0) for cleaner display
- Legend and stats properly sync visibility
- Mode transitions (preflop ↔ postflop) properly reset visibility state
- Weighted frequency stats account for mixed strategies correctly

> **Note:** The range viewer and API are fully implemented. When solver data is generated (see Feature #6), it can be dropped into `ai/postflop_strategies/` and will automatically be used.

---

### Feature 6: Proprietary Solver Ranges & Multi-Street GTO Coaching

**Prompt:** `active/GTO_RANGE_GENERATION_PLAN.md`
**Status:** In Progress (Phase 1 complete)
**Dependencies:** GTO+ (purchased and configured)
**Priority:** High for commercial viability and coaching quality

**Goal:** Provide the best GTO coaching realistically possible for preflop and postflop play through all streets (flop, turn, river).

**Problem:** Using third-party range data has licensing concerns. Additionally, flop-only coaching covers a fraction of the decisions players face — turn and river are where the biggest mistakes happen and the most EV is won/lost.

**Solution — Phased Approach:**

**Near-term (Phases 1-3): Pre-computed solver strategies**
- Phase 1: SRP flop strategies for all 9 textures (1 board each) — **COMPLETE**
- Phase 2: Additional boards per texture for averaging (~10-18 more solves)
- Phase 3: 3-bet pot flop strategies (8 solves)
- This gives solid flop coaching covering ~70-80% of common spots

**Near-term (Phase 4): Turn strategy extraction from existing solves**
- The 19 existing `.gto2` files contain the full game tree through all streets — no additional solving needed
- Categorize turn cards into 5 types (overcard, brick, flush completing, straight completing, board pairing)
- Extract 5 representative turn cards × 3 nodes per flop action sequence
- Phase 4a: Check-check line (~135 JSON files) — most common scenario
- Phase 4b: Bet-call and check-bet-call lines (~270 more files)
- Estimated extraction time: 5-15 hours manual work

**Later (Phase 5): River strategy extraction**
- Same approach, one level deeper — extract from existing solved trees
- Scale: ~675-2,000+ files depending on coverage
- Alternative: if manual extraction is too labor-intensive at this scale, evaluate real-time solver queries or neural network approximation using accumulated data as training input

**Code Integration (Already Ready):**
The code infrastructure for using solver data is complete:
- Preflop: Update entries in `ai/preflop_ranges.json` (loaded by `ai/solver_ranges.py`)
- Postflop: Add JSON files to `ai/postflop_strategies/`
- Range viewer, API endpoints, and coaching logic will automatically use new data

**Known Architectural Limitation — Position-Specific Solver Data:**
Current postflop solver data represents a single BTN vs BB scenario. The BB's strategy (donk-bet/check-raise frequencies) is being applied to all defender positions, and the BTN's strategy is applied to all aggressor positions. This creates equity estimation errors because:
- A CO opener's c-bet range differs from BTN's c-bet range (CO opens tighter)
- BB's donk-bet strategy doesn't match how other positions play OOP
- Range narrowing uses BB frequencies to estimate villain's range, inflating equity for marginal hands

**Future fix:** Generate separate solver configurations for common aggressor/caller matchups (e.g., CO vs BB, BTN vs BB, HJ vs BB). This is a data-generation task, not a code change — the code infrastructure already supports position-specific strategy lookup via the `pot_type` parameter.

**Current Progress:**
- Phase 1 SRP flop: **COMPLETE** — 9 textures, 1 board each (9 solves, 27 JSON files)
- Phase 2 multi-board averaging: **COMPLETE** — 10 additional boards merged in (19 total solves)
- Phase 2c IP facing OOP bet: **COMPLETE** — 9 `_ip_vs_bet_small.json` files (36 total flop files)
- Phase 4a turn check-check: **COMPLETE (Feb 8)** — 63 turn cards extracted via hybrid GUI+socket approach, 93 merged turn JSON files deployed to `ai/postflop_strategies/srp/turn/`
- Engine integration: `_get_postflop_situation()` classifies turn cards, `get_strategy()` uses composite `turn:{category}` keys with flop fallback
- Merge script: `scripts/merge_strategies.py` with dedicated `merge_turn_strategies()` function groups by turn category
- Extraction tools: `gto_turn_hybrid.ps1` (hybrid GUI-first approach — socket can't navigate chance nodes)
- All 19 `.gto2` files saved — contain full turn/river trees ready for deeper extraction
- **Next:** Phase 4b (bet-call/check-bet-call turn lines), Phase 3 (3-bet pot solves)
- **PioSolver migration planned** — replaces GTO+ extraction pipeline with automated PioSolver UPI scripts. See `active/PIOSOLVER_MIGRATION_PLAN.md`
- See `GTO_RANGE_GENERATION_PLAN.md` for detailed roadmap

**Preflop Situation Architecture (Decided Feb 9, 2026):**

The system currently supports 4 preflop situations. Additional situations are planned for future implementation (PioSolver migration or GTO Wizard import). The full taxonomy of preflop decisions:

| Situation | Key Format | Meaning | Hero's Options | Villain Position Constraint |
|-----------|-----------|---------|----------------|---------------------------|
| `opening` | `6max\|UTG\|100bb` | First voluntary action (RFI) | Raise, Fold (SB: also Call/Complete) | N/A |
| `facing_open` | `HJ\|vs_UTG\|100bb\|6max` | Someone opened, hero acts | Call, 3-bet, Fold | Villain acted before hero |
| `facing_3bet` | `CO\|vs_BTN\|100bb\|6max` | Hero opened, villain 3-bet | Call, 4-bet, Fold | Villain acted **after** hero (hero was opener) |
| `facing_limp` | `BB\|vs_SB\|100bb\|6max` | Someone limped, hero acts | Raise, Check/Fold | Villain acted before hero (currently BB vs SB only) |
| `facing_3bet_cold` | `CO\|cold_vs_HJ\|100bb\|6max` | Someone opened, someone else 3-bet, hero hasn't acted | Cold call, Cold 4-bet, Fold | **Any position** (hero wasn't involved) |
| `facing_4bet` | `UTG\|vs_BTN\|100bb\|6max` | Hero 3-bet, villain 4-bet | Call, 5-bet/All-in, Fold | Villain acted after hero |
| `squeeze` | `CO\|vs_UTG_call_HJ\|100bb\|6max` | Open + cold call, hero 3-bets over both | Raise (squeeze), Fold | Two villains: opener + caller |
| `overcall` | *TBD* | Open + caller(s), hero cold calls | Call, Fold | Opener acted before hero |

**Key design decisions:**
- **`facing_3bet` vs `facing_3bet_cold`**: These are fundamentally different because hero's starting range differs. In `facing_3bet`, hero has an opening range (narrowed). In `facing_3bet_cold`, hero hasn't acted (full range). Different ranges = different situations.
- **`facing_3bet_cold` tracks only the 3-bettor** (`cold_vs_HJ`), not the original opener. The 3-bettor's position is the primary driver of hero's decision. The opener's identity has a second-order effect (it influences the 3-bettor's range width) but adds significant key combinatorics.
- **Future enhancement**: If coaching precision requires it, expand `facing_3bet_cold` keys to include the opener: `CO|cold_vs_HJ_over_UTG|100bb|6max`. This is a data expansion, not a code change — the key format is just a string.
- **`facing_limp` is currently BB vs SB only**. Range data only exists for this matchup. The UI only shows facing_limp when hero is BB. Future enhancement: add facing_limp for other positions (e.g., CO vs UTG limp) when solver data becomes available via PioSolver.
- **`facing_3bet` villain is always after hero** in position order (hero opened, so the 3-bettor must act later). The range compare tool correctly restricts villain options to positions after hero for this situation.

---

### Feature 7: Scoring System

**Prompt:** `active/SCORING_SYSTEM_PROMPT.md`
**Status:** Partial (scoring logic exists, storage not implemented)
**Dependencies:** None
**Priority:** Medium - enables personalization features

**Problem:** No persistent tracking of player performance.

**Solution:** Database tables for action scores and aggregated street performance.

**Deliverables:**
- Database schema (`action_scores`, `street_performance`)
- `/api/performance` endpoint
- Stats modal with performance tab
- Weakest street identification

---

### Feature 8: Weakness Identification (NEW)

**Prompt:** *To be created*
**Status:** New
**Dependencies:** Scoring System
**Priority:** Medium - key differentiator

**Problem:** Players don't know their specific leaks.

**Solution:** Analyze scoring patterns to identify systematic leaks.

**Planned Deliverables:**
- Pattern detection algorithms
- Leak categories (position, hand type, street, action type)
- "Your Leaks" dashboard section
- Trend analysis over time

---

### Feature 9: Exploitability Alerts (NEW)

**Prompt:** *To be created*
**Status:** New
**Dependencies:** Weakness Identification
**Priority:** Medium - unique feature

**Problem:** Players don't realize when their patterns become exploitable.

**Solution:** Warn when tendencies are pronounced enough to be exploited.

**Planned Deliverables:**
- Exploitability threshold calculations
- Alert system for pronounced patterns
- Suggested counter-adjustments
- "How opponents would exploit you" explanations

---

### Feature 10: Focused Practice (NEW)

**Prompt:** *To be created*
**Status:** New
**Dependencies:** Weakness Identification
**Priority:** Medium - drives engagement

**Problem:** Generic practice doesn't address specific weaknesses.

**Solution:** Auto-generate practice scenarios targeting identified leaks.

**Planned Deliverables:**
- Drill generator based on weakness categories
- Adaptive difficulty
- Progress tracking per drill type
- Drill library (preflop, c-bet, 3-bet pots, etc.)

---

### Feature 11: Quick Hand Input

**Prompt:** `active/QUICK_HAND_INPUT_PROMPT.md`
**Status:** ✅ Feature Complete (Feb 13, 2026)
**Dependencies:** None
**Priority:** Medium - user-requested feature

**Problem:** Users can't easily input specific situations to practice.

**Solution:** Modal with visual card picker, position/action configuration, full GTO coaching feedback, and Play It Out / Play All Hands for hands-on practice.

**Deliverables (Complete):**
- `build_scenario_game_state()` — synthetic GameState construction at hero's decision point
- `POST /api/scenarios/analyze` — validation, analysis, DB persistence
- `ScenarioAnalyzer` class — card picker (4×13 grid), action toggles, results display
- `scenarios` table — schema supports future on-demand playback, random mix, featured hands
- Multi-street analysis: preflop + flop + turn + river coaching in one result
- Hand Library: save, browse, load, delete hands (New Hand / Library tabs)
- "Play It Out" mode: initialize GameState from any scenario and play against AI (Feb 10)
- "Play All Hands": sequential play-through of entire library with progress tracking (Feb 13)
- Dynamic modal title ("Hand Library" / "Quick Hand Input") and hand count display
- Save Hand from Game: `POST /api/hands/save-from-game` saves completed game hands to library (Feb 15)
- Hand Sharing: custom share menu (Copy Link, Text/SMS, WhatsApp, X, Email with client picker), spoiler-free share text, OG preview image with hero cards, `ProxyFix` for HTTPS on Railway (Feb 15)
- 67 tests (GameState construction, playout, multi-street, raise-vs-bet, force-scenario)

**Remaining (Future Phases):**
- Featured/curated hands UI (DB schema ready: `is_featured` column)

---

### Feature 15: Adjustable Opponent Profiles

**Prompt:** `planned/ADJUSTABLE_OPPONENT_PROFILES_PROMPT.md`
**Status:** Planned
**Dependencies:** None (core AI already uses solver ranges)
**Priority:** Low - enhancement feature for realistic practice

**Problem:** AI opponents all play GTO, but real-world opponents have varying tendencies.

**Solution:** Allow users to configure AI opponent profiles with adjustable play styles.

**Planned Deliverables:**
- Profile modifiers: tightness, aggression, 3-bet freq, c-bet freq, fold-to-3bet, bluff freq
- Preset profiles: GTO, LAG, TAG, Calling Station, Nit, Maniac, Recreational
- Per-seat configuration in settings UI
- Database storage for saved configurations
- Coach feedback mentioning opponent tendencies

**Use Cases:**
- Practice exploiting specific player types (e.g., "this table has two calling stations")
- Simulate realistic table dynamics with mixed skill levels
- Prepare for live games where opponents don't play balanced strategies

---

## Implementation Schedule

### Immediate Next Steps (Priority Order)

**Coding Track (Core Coaching Quality):**
1. ~~**Range-Based Equity** (#4)~~ - ✅ Complete
2. ~~**Stack Depth & Table Size Ranges** (#4a)~~ - ✅ Complete
3. ~~**Postflop Range Coaching** (#5)~~ - ✅ Complete (Core)

**Next Up (Personalization):**
4. **Scoring System** (#7) - ⭐ Enables personalization features
5. **Weakness Identification** (#8) - Key differentiator

**Parallel Tracks (Can run simultaneously):**
- **Proprietary Solver Ranges** (#6) - Solver work, no code dependencies
- **Quick Hand Input** (#11) - UI feature, independent
- **UI improvements** - Can be done anytime

### Commercial Preparation

1. **Proprietary Solver Ranges** - Required before commercial launch (licensing)
2. **Legal review** - Terms of service, data usage policies

### Engagement Features

1. **Focused Practice** - After weakness identification
2. **Quick Hand Input** - Can be built independently (parallel track)

### Recommended Build Order

```
Month 1:  Range-Based Equity + Stack Depth/Table Size Ranges    ✅ COMPLETE
Month 2:  Postflop Range Coaching (core implementation)         ✅ COMPLETE
Month 3:  Scoring System + Weakness Identification              SCORING ✅ COMPLETE
Month 4:  Exploitability Alerts + Focused Practice              ← NEXT
Month 5:  Quick Hand Input + UI Polish
Month 6:  Postflop expansion (turn/river, 3-bet pots)
```

---

## Success Metrics

| Phase | Key Metrics |
|-------|-------------|
| Foundation | Coaching accuracy (measured by Training Module), user satisfaction |
| Accuracy | Equity calculation correctness, fewer "weird" recommendations |
| Personalization | User retention, session length, return visits |
| Engagement | Drill completion rates, weakness improvement over time |
| Polish | User acquisition, conversion rates, NPS score |

---

## Prompt Template for New Features

When creating a new feature prompt, use this template:

```markdown
# [Feature Name]

**Created:** [Date]
**Status:** [Planning/In Progress/Complete]
**Dependencies:** [List dependencies]
**Priority:** [High/Medium/Low] - [Brief justification]
**Master Plan Reference:** `developer-guides/prompts/DEVELOPMENT_PLAN.md` → Feature #[N]

---

## Problem Statement

[What problem does this solve?]

---

## Architecture Overview

[System diagram or description]

---

## Implementation Plan

### Phase 1: [Phase Name]
[Tasks and deliverables]

### Phase 2: [Phase Name]
[Tasks and deliverables]

---

## Success Criteria

| Criteria | Measurement |
|----------|-------------|
| [Criterion] | [How to measure] |

---

## References

- **Master Plan:** `developer-guides/prompts/DEVELOPMENT_PLAN.md`
- [Other related documents]
```

---

## Changelog

| Date | Change |
|------|--------|
| 2026-02-01 | Initial creation of master development plan |
| 2026-02-01 | Clarified Range-Based Equity vs Proprietary Ranges dependencies; added parallel tracks |
| 2026-02-01 | Added Postflop Range Coaching (Feature #5) - critical for competitive positioning; renumbered features |
| 2026-02-02 | Updated Stack Depth & Table Size Ranges with allin/check actions, mixed frequency gradients, and 402-test API suite |
| 2026-02-02 | Marked Postflop Range Coaching (#5) as Complete (Core) - includes board texture classification, postflop range API, unified range viewer, vulnerable hand detection |
| 2026-02-03 | Added code integration details to Feature #5 and #6; documented data gaps (facing-bet postflop, turn/river) and noted that code infrastructure is ready for solver data |
| 2026-02-03 | Added: preflop equity vs opener's range, dynamic stats visibility, mode transition fixes |
| 2026-02-03 | Added: comprehensive fold explanations for all preflop scenarios (facing open, 3-bet, 4-bet) explaining equity realization |
| 2026-02-03 | Added: AI opponents now use solver-based postflop decisions; added Feature #15 (Adjustable Opponent Profiles) |
| 2026-02-04 | Completed Scoring System (#7): action_scores/street_performance tables, /api/performance endpoint, Performance tab in Stats modal |
| 2026-02-04 | Fixed HU range lookup bug: num_players now passed correctly to solver range functions |
| 2026-02-04 | Created Quick Hand Input prompt (Feature #11) |
| 2026-02-04 | Created Street Focus Practice prompt (Feature #10): Practice specific streets with auto-play context |
| 2026-02-05 | Feature #6 Phase 1 complete: all 9 SRP textures have real GTO+ solver data (27 JSON files). Updated Feature #6 to include multi-street coaching vision (real-time solver, neural net, heuristic approaches for turn/river) |
| 2026-02-05 | Feature #6 Phase 2 complete: 10 additional boards solved and merged (19 total). Added merge_strategies.py for averaging hand frequencies across multiple representative boards per texture |
| 2026-02-08 | Feature #6 Phase 2c COMPLETE: IP facing OOP bet (node 4) extracted from all 19 solves. 9 new `_ip_vs_bet_small.json` merged files (36 total flop files). Range viewer "Facing OOP Bet" dropdown added. Merge script null-handling fix |
| 2026-02-08 | Feature #4b: Postflop Range Narrowing Phase 1 + 1b COMPLETE. Villain range narrowed by solver action frequencies (bet/check/raise/call). Weighted Monte Carlo equity. Handles OOP-none, IP-check, IP-bet_small contexts. 15 tests |
| 2026-02-08 | AI Coach improvements: river raise-vs-call scoring (2/5 not 4/5), solver frequency threshold (>=80% → 2/5), paired board texture fix (all paired → HIGH_PAIRED), flush draw strength qualifiers (nut/strong/Q-high/weak) |
| 2026-02-08 | Feature #6 Phase 4a COMPLETE: Turn check-check strategies extracted from all 19 solves (63 turn cards, 189 extractions). 93 merged JSON files in srp/turn/. Hybrid GUI+socket extraction (socket can't navigate chance nodes). Engine classifies turn cards and uses category-specific strategies with flop fallback. Range narrowing works on turn street. |
| 2026-02-09 | Preflop situation taxonomy designed: documented 8 situations (4 current + 4 planned). Key decision: `facing_3bet_cold` is separate from `facing_3bet` (different hero starting range). `facing_3bet_cold` tracks only 3-bettor position (not opener) to limit key combinatorics; opener tracking is a future enhancement. PioSolver migration plan created (`active/PIOSOLVER_MIGRATION_PLAN.md`). |
| 2026-02-09 | Range compare tool: paste range feature (All In / Raise / Call/Check), BB auto-switch to facing_limp, facing_limp defaults to check (not fold) |
| 2026-02-10 | Feature #11 Quick Hand Input MVP COMPLETE: ScenarioAnalyzer modal with card picker, `build_scenario_game_state()` synthetic state construction, `/api/scenarios/analyze` endpoint, `scenarios` DB table, 17 tests. Prompt moved from `planned/` to `active/`. |
| 2026-02-10 | Added Feature #16 (Database Backup & Persistence) after data loss incident — empty poker.db caused login failure. Prompt: `planned/DATABASE_BACKUP_PROMPT.md` |
| 2026-02-10 | Feature #11 enhancements: Hand Library (save/browse/load/delete), multi-street analysis with preflop coaching, street pot display, hero stack per street, section locking for prior streets, situation-aware preflop selectors (opening/facing_open/facing_3bet/facing_limp), `saved_hands` table + `GET /api/hands/list` + `DELETE /api/hands/<id>` |
| 2026-02-10 | Coaching bug fixes: `num_raises` now set in `build_scenario_game_state` (was 0, caused "5-bet" instead of "4-bet" labels); mixed frequency feedback returns fold when fold is highest frequency (fixes conflicting "fold" + "should 4-bet" advice); preflop action buttons preserved when adding board cards |
| 2026-02-13 | Feature #11 Play All Hands: sequential play-through of entire hand library. Dynamic modal title ("Hand Library" / "Quick Hand Input"), hand count display, "Play All Hands" button. Post-hand buttons adapt for play-all mode: "Next Hand (2 of 10)" / "Back to Library" / "Deal New Hand". Fix for preflop fold showing regular "Deal Next Hand" instead of play-all buttons. Status upgraded from MVP Complete → Feature Complete. |
| 2026-02-15 | Mobile UI: AI Coach sidebar collapsed by default on mobile, tap-outside-to-close, sidebar overlay breakpoint fix (768px) |
| 2026-02-15 | Scoring: preflop mixed strategy actions scored 4/5 when hero's action is a valid mixed-frequency option |
| 2026-02-15 | Save Hand from Game: `POST /api/hands/save-from-game` endpoint, "Save Hand" button in post-hand flex layout, auto-generates title with profit |
| 2026-02-15 | Hand Sharing: custom share menu replaces OS share sheet (Copy Link, Text/SMS, WhatsApp, X, Email). Email client picker (Gmail/Outlook/Yahoo) with localStorage preference. Spoiler-free share text (hero hand + positions + situation only). OG preview image shows hero cards only at large size. `ProxyFix` middleware fixes `og:image` HTTPS URLs behind Railway proxy. |
| 2026-02-18 | Preflop range coverage: all 15 `facing_4bet` matchups at 100bb/6max completed. 100bb/6max fully covered through 4-bet pots (opening, facing_open, facing_3bet, facing_3bet_cold, facing_4bet, facing_limp). Coverage tracker: `developer-guides/preflop-range-coverage.md`. |
| 2026-02-18 | Range compare tool: comparison display synced with Our Range — same grid rendering (multi-color gradients for mixed hands, partial-fill for conditional ranges), same legend combo counting (frequency-weighted distribution across all actions), tooltips with frequency breakdown. Validation script confirms 532 situations with zero discrepancies. |

