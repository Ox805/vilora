Run the automated Vilora mediation quality test-and-improve pipeline. Execute ALL steps below in order.

## Step 0: Review Master Report (if it exists)
Read `tests/TESTING_MASTER_REPORT.md` before doing anything. Look for:
- **Recurring failures** -- if an issue has appeared in 3+ runs, do NOT try another prompt change. Use a code-level fix instead (response filtering, post-processing, detection logic).
- **Top issue categories** -- focus fixes on the most common category first.
- **Regressions from previous runs** -- avoid repeating changes that caused regressions.
- **Recommendations** -- follow the data-driven suggestions.

If this is the first run, skip to Step 1.

## Step 1: Run Tests
```
cd /home/tim/dev/vilora && python3 tests/run_tests.py --evaluate
```
Review the output. Note the pass rate and all failures.

## Step 2: Analyze & Fix Failures
For each failure, determine the root cause and implement a fix.

Key files to modify:
- **System prompts**: `mediation/engine.py` -> `COUNSELOR_PROMPT`, `SYSTEM_PROMPT`, `SHOULD_RESPOND_PROMPT`
- **Response generation**: `mediation/engine.py` -> `mediate()`, `_build_conversation()`
- **Welcome messages**: `mediation/engine.py` -> `welcome()`
- **Should-respond logic**: `mediation/engine.py` -> `should_respond()` (heuristics + prompt)
- **Framework context**: `mediation/frameworks.py`
- **Response post-processing**: Add filtering/truncation in `mediate()` if needed

**Rules:**
- Prefer code-level fixes over prompt changes -- they are more reliable
- If a prompt change is needed, make it surgical and specific (add a constraint, not rewrite the whole prompt)
- Never weaken an existing constraint to fix a different issue
- If a should_respond test fails, check the heuristic cutoffs first before touching the LLM decision prompt
- After any change, consider whether it could cause regressions in other scenarios

## Step 3: Re-Test
```
cd /home/tim/dev/vilora && python3 tests/run_tests.py --evaluate
```
Compare pass rate to Step 1. If improved, continue. If regressed, revert the fix and try a different approach.

## Step 4: Repeat
Repeat Steps 2-3 up to 3 total iterations or until pass rate reaches 90%+.

## Step 5: Generate Master Report
```
cd /home/tim/dev/vilora && python3 tests/report_generator.py
```
This updates `tests/TESTING_MASTER_REPORT.md`. Read the generated report.

## Step 6: Commit & Summarize
Commit all changes (code fixes, test results, updated report). Don't mention claude in the commit.

Provide the user a summary:
- Starting pass rate -> ending pass rate
- What was fixed and how
- What still needs work and recommended next steps
- Any patterns from the master report
- Whether any recurring failures need a fundamentally different approach

---

## Test Infrastructure Reference

Test scenarios: `tests/scenarios/*.json`
Test runner: `tests/run_tests.py` (use `--evaluate` for LLM judging)
Test history: `tests/history/`
Report generator: `tests/report_generator.py`
Master report: `tests/TESTING_MASTER_REPORT.md`

### Adding New Test Scenarios

Create a JSON file in `tests/scenarios/` following the existing patterns:
- `test_method: "mediate"` -- tests the main response generation
- `test_method: "should_respond"` -- tests the chime-in decision logic
- `test_method: "welcome"` -- tests welcome message quality

Each scenario includes evaluation criteria with names, descriptions, and weights.
The LLM judge scores each criterion as PASS/FAIL with explanations.
