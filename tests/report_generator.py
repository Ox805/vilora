#!/usr/bin/env python3
"""
Generates and updates tests/TESTING_MASTER_REPORT.md from test run history.

Reads all JSON results in tests/history/, analyzes trends, identifies
recurring issues, and writes a comprehensive report.

Usage:
    python tests/report_generator.py
"""

import json
import os
from datetime import datetime
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent
HISTORY_DIR = PROJECT_ROOT / 'tests' / 'history'
REPORT_PATH = PROJECT_ROOT / 'tests' / 'TESTING_MASTER_REPORT.md'


def load_history():
    """Load all test run results, newest first."""
    runs = []
    for path in sorted(HISTORY_DIR.glob('run_*.json'), reverse=True):
        with open(path) as f:
            data = json.load(f)
            data['_file'] = path.name
            runs.append(data)
    return runs


def analyze_failures(runs):
    """Find recurring failures across runs."""
    failure_counts = defaultdict(list)  # criterion_name -> [run timestamps]
    failure_details = defaultdict(list)  # criterion_name -> [explanations]

    for run in runs:
        ts = run.get('timestamp', 'unknown')
        for scenario in run.get('scenarios', []):
            # Handle mediate tests
            eval_data = scenario.get('evaluation', {})
            for cr in eval_data.get('criteria_results', []):
                if cr.get('result') == 'FAIL':
                    key = f"{scenario['name']} :: {cr['name']}"
                    failure_counts[key].append(ts)
                    failure_details[key].append(cr.get('explanation', ''))

            # Handle should_respond cases
            for case in scenario.get('cases', []):
                if not case.get('passed', True):
                    key = f"should_respond :: {case['name']}"
                    failure_counts[key].append(ts)
                    failure_details[key].append(
                        f"Expected {case['expected']}, got {case['actual']}"
                    )

            # Handle welcome cases
            for case in scenario.get('cases', []):
                case_eval = case.get('evaluation', {})
                for cr in case_eval.get('criteria_results', []):
                    if cr.get('result') == 'FAIL':
                        key = f"{scenario['name']} / {case['name']} :: {cr['name']}"
                        failure_counts[key].append(ts)
                        failure_details[key].append(cr.get('explanation', ''))

    return failure_counts, failure_details


def categorize_failures(failure_counts):
    """Group failures by category."""
    categories = defaultdict(int)
    for key, timestamps in failure_counts.items():
        # Infer category from criterion name
        criterion = key.split(' :: ')[-1]
        if criterion in ('impartiality', 'no_judgment'):
            categories['Impartiality / Bias'] += len(timestamps)
        elif criterion in ('de_escalation', 'no_lecturing'):
            categories['Tone / De-escalation'] += len(timestamps)
        elif criterion in ('reframing',):
            categories['Reframing'] += len(timestamps)
        elif criterion in ('empathy', 'genuine_empathy', 'validates_experience'):
            categories['Empathy'] += len(timestamps)
        elif criterion in ('actionable', 'practical_direction', 'forward_looking'):
            categories['Actionability'] += len(timestamps)
        elif criterion in ('spots_common_ground', 'builds_on_agreement', 'acknowledges_progress'):
            categories['Common Ground'] += len(timestamps)
        elif criterion in ('appropriate_length', 'no_premature_solutions', 'no_quick_fixes', 'no_toxic_positivity'):
            categories['Response Structure'] += len(timestamps)
        elif 'should_respond' in key:
            categories['Should Respond Logic'] += len(timestamps)
        else:
            categories['Other'] += len(timestamps)
    return dict(sorted(categories.items(), key=lambda x: -x[1]))


def generate_report(runs):
    """Generate the master report markdown."""
    if not runs:
        return "# Vilora Testing Master Report\n\nNo test runs found yet.\n"

    latest = runs[0]
    failure_counts, failure_details = analyze_failures(runs)
    categories = categorize_failures(failure_counts)

    # Recurring failures (3+ runs)
    recurring = {k: v for k, v in failure_counts.items() if len(v) >= 3}

    lines = []
    lines.append("# Vilora Testing Master Report")
    lines.append(f"\nLast updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"\nTotal test runs analyzed: {len(runs)}")

    # --- Pass Rate Trend ---
    lines.append("\n## Pass Rate Trend\n")
    lines.append("| Run | Date | Pass Rate | Passed | Total |")
    lines.append("|-----|------|-----------|--------|-------|")
    for i, run in enumerate(runs[:10]):  # last 10 runs
        ts = run.get('timestamp', 'unknown')
        try:
            date = datetime.fromisoformat(ts).strftime('%Y-%m-%d %H:%M')
        except (ValueError, TypeError):
            date = ts
        rate = run.get('pass_rate', 0)
        passed = run.get('passed', 0)
        total = run.get('total_tests', 0)
        marker = ' (latest)' if i == 0 else ''
        lines.append(f"| {run.get('_file', '?')}{marker} | {date} | {rate:.0f}% | {passed} | {total} |")

    # --- Top Issue Categories ---
    if categories:
        lines.append("\n## Top Issue Categories\n")
        lines.append("Focus fixes on the most common category first.\n")
        for cat, count in categories.items():
            lines.append(f"- **{cat}**: {count} failure(s)")

    # --- Recurring Failures ---
    if recurring:
        lines.append("\n## Recurring Failures (3+ runs)\n")
        lines.append("These need code-level fixes, not prompt tweaks.\n")
        for key, timestamps in sorted(recurring.items(), key=lambda x: -len(x[1])):
            lines.append(f"### {key}")
            lines.append(f"Failed in {len(timestamps)} run(s)\n")
            details = failure_details.get(key, [])
            if details:
                lines.append("Recent explanations:")
                for d in details[-3:]:
                    lines.append(f"- {d}")
            lines.append("")

    # --- Latest Run Details ---
    lines.append("\n## Latest Run Details\n")
    for scenario in latest.get('scenarios', []):
        name = scenario.get('name', 'Unknown')
        method = scenario.get('test_method', '?')

        if method == 'should_respond':
            cases = scenario.get('cases', [])
            passed_cases = sum(1 for c in cases if c.get('passed'))
            lines.append(f"### {name}")
            lines.append(f"Passed: {passed_cases}/{len(cases)}\n")
            for case in cases:
                status = 'PASS' if case.get('passed') else 'FAIL'
                lines.append(f"- [{status}] {case['name']}")
            lines.append("")

        elif method == 'welcome':
            cases = scenario.get('cases', [])
            lines.append(f"### {name}")
            for case in cases:
                score = case.get('score', 'N/A')
                status = 'PASS' if case.get('passed') else 'FAIL'
                lines.append(f"\n**{case['name']}** [{status}] Score: {score}")
                case_eval = case.get('evaluation', {})
                for cr in case_eval.get('criteria_results', []):
                    lines.append(f"- [{cr['result']}] {cr['name']}: {cr['explanation']}")
            lines.append("")

        else:
            score = scenario.get('score', 'N/A')
            passed = scenario.get('passed', True)
            status = 'PASS' if passed else 'FAIL'
            lines.append(f"### {name} [{status}] Score: {score}\n")
            eval_data = scenario.get('evaluation', {})
            for cr in eval_data.get('criteria_results', []):
                lines.append(f"- [{cr['result']}] {cr['name']}: {cr['explanation']}")
            if eval_data.get('overall_strengths'):
                lines.append(f"\n**Strengths:** {eval_data['overall_strengths']}")
            if eval_data.get('overall_weaknesses'):
                lines.append(f"\n**Weaknesses:** {eval_data['overall_weaknesses']}")
            lines.append("")

    # --- Recommendations ---
    lines.append("\n## Recommendations\n")
    if recurring:
        lines.append("### Code-level fixes needed (recurring failures)\n")
        for key in list(recurring.keys())[:5]:
            criterion = key.split(' :: ')[-1]
            lines.append(f"- **{criterion}**: Failed {len(recurring[key])}+ times. "
                        f"Prompt changes alone are unlikely to fix this.")
        lines.append("")

    if categories:
        top_cat = list(categories.keys())[0]
        lines.append(f"### Priority focus: {top_cat}\n")
        lines.append(f"This category has the most failures. Address it first for maximum impact.\n")

    lines.append("### Where to make changes\n")
    lines.append("- System prompts: `mediation/engine.py` (COUNSELOR_PROMPT, SYSTEM_PROMPT, SHOULD_RESPOND_PROMPT)")
    lines.append("- Response generation: `mediation/engine.py` -> `mediate()`, `welcome()`")
    lines.append("- Decision logic: `mediation/engine.py` -> `should_respond()`")
    lines.append("- Framework context: `mediation/frameworks.py`")
    lines.append("")
    lines.append("### General guidance\n")
    lines.append("- Prefer code-level fixes (response filtering, detection) over prompt changes")
    lines.append("- Prompt changes are fragile and can cause regressions in other areas")
    lines.append("- After fixing, re-run with `--evaluate` to confirm improvement")

    return '\n'.join(lines)


if __name__ == '__main__':
    runs = load_history()
    report = generate_report(runs)

    with open(REPORT_PATH, 'w') as f:
        f.write(report)

    print(f"Report generated: {REPORT_PATH}")
    print(f"Analyzed {len(runs)} test run(s)")
