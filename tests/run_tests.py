#!/usr/bin/env python3
"""
Vilora Mediation Quality Test Runner

Loads test scenarios, runs them through the MediationEngine, and evaluates
response quality using Claude as an LLM judge.

Usage:
    python tests/run_tests.py                    # run all tests
    python tests/run_tests.py --evaluate         # run + evaluate with LLM judge
    python tests/run_tests.py --scenario NAME    # run a specific scenario file
    python tests/run_tests.py --list             # list available scenarios
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env file if it exists (for local development)
env_path = PROJECT_ROOT / '.env'
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                os.environ.setdefault(key.strip(), value.strip())

from anthropic import Anthropic

# ---------------------------------------------------------------------------
# Mock objects to simulate database models
# ---------------------------------------------------------------------------

class MockUser:
    def __init__(self, id, display_name):
        self.id = id
        self.display_name = display_name

class MockMessage:
    def __init__(self, msg_type, user_id, content, id=None):
        self.id = id or 0
        self.session_id = 1
        self.user_id = user_id
        self.content = content
        self.msg_type = msg_type
        self.created_at = datetime.now()

# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

SCENARIOS_DIR = PROJECT_ROOT / 'tests' / 'scenarios'
HISTORY_DIR = PROJECT_ROOT / 'tests' / 'history'

EVALUATOR_PROMPT = """\
You are evaluating the quality of an AI mediator/counselor response. You will be given:
- The scenario context (topic, participants, conversation history)
- The AI's response
- A list of evaluation criteria with descriptions

For EACH criterion, score it as PASS or FAIL and give a brief (1-2 sentence) explanation.

Then give an overall assessment: what the response did well and what could be improved.

Respond in EXACTLY this JSON format (no markdown, no code fences):
{
  "criteria_results": [
    {"name": "criterion_name", "result": "PASS or FAIL", "explanation": "why"}
  ],
  "overall_strengths": "what the response did well",
  "overall_weaknesses": "what could be improved",
  "overall_score": 0.0
}

The overall_score should be 0.0-1.0 based on weighted criteria results.
Be strict but fair. A mediocre response that checks boxes should not score above 0.7.
A genuinely good response that misses one minor criterion can still score 0.8+.
"""


def load_scenarios(scenario_filter=None):
    """Load all scenario JSON files from the scenarios directory."""
    scenarios = []
    for path in sorted(SCENARIOS_DIR.glob('*.json')):
        if scenario_filter and scenario_filter not in path.stem:
            continue
        with open(path) as f:
            data = json.load(f)
            data['_file'] = path.stem
            scenarios.append(data)
    return scenarios


def build_mocks(scenario):
    """Build mock participants and messages from scenario data."""
    participants = [MockUser(p['id'], p['display_name']) for p in scenario['participants']]
    messages = [
        MockMessage(m['msg_type'], m.get('user_id'), m['content'], id=i+1)
        for i, m in enumerate(scenario['messages'])
    ]
    return participants, messages


def run_mediate_test(engine, scenario):
    """Run a mediate() test and return the response."""
    participants, messages = build_mocks(scenario)
    response = engine.mediate(
        topic=scenario['topic'],
        session_type=scenario['session_type'],
        messages=messages,
        participants=participants,
        participant_memories=None,
        session_mode=scenario['session_mode']
    )
    return response


def run_should_respond_test(engine, case):
    """Run a should_respond() test case and return result + expected."""
    participants = [MockUser(p['id'], p['display_name']) for p in case['participants']]
    messages = [
        MockMessage(m['msg_type'], m.get('user_id'), m['content'], id=i+1)
        for i, m in enumerate(case['messages'])
    ]
    result = engine.should_respond(
        topic=case['topic'],
        messages=messages,
        participants=participants,
        session_mode='mediation'
    )
    return result, case['expected']


def run_welcome_test(engine, case):
    """Run a welcome() test case and return the response."""
    response = engine.welcome(
        topic=case['topic'],
        session_type=case['session_type'],
        perspective=case['perspective'],
        creator_name=case['creator_name'],
        session_mode=case['session_mode']
    )
    return response


def evaluate_response(client, scenario_context, response_text, criteria):
    """Use Claude to evaluate a response against criteria."""
    eval_prompt = (
        f"## Scenario Context\n{scenario_context}\n\n"
        f"## AI Response to Evaluate\n{response_text}\n\n"
        f"## Evaluation Criteria\n"
    )
    for c in criteria:
        eval_prompt += f"- **{c['name']}** (weight: {c.get('weight', 1)}): {c['description']}\n"

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=EVALUATOR_PROMPT,
            messages=[{"role": "user", "content": eval_prompt}]
        )
        return json.loads(response.content[0].text)
    except Exception as e:
        return {"error": str(e), "criteria_results": [], "overall_score": 0.0}


def build_scenario_context(scenario):
    """Build a text description of the scenario for the evaluator."""
    parts = [
        f"Topic: {scenario['topic']}",
        f"Session mode: {scenario.get('session_mode', 'mediation')}",
        f"Session type: {scenario.get('session_type', 'general')}",
        f"Participants: {', '.join(p['display_name'] for p in scenario['participants'])}",
        "\nConversation history:"
    ]
    names = {p['id']: p['display_name'] for p in scenario['participants']}
    for m in scenario['messages']:
        if m['msg_type'] == 'intake':
            name = names.get(m.get('user_id'), 'Unknown')
            parts.append(f"  [{name}'s initial perspective]: {m['content']}")
        elif m['msg_type'] == 'user':
            name = names.get(m.get('user_id'), 'Unknown')
            parts.append(f"  [{name}]: {m['content']}")
        elif m['msg_type'] == 'mediator':
            parts.append(f"  [Vilora]: {m['content']}")
    return '\n'.join(parts)


def run_all_tests(evaluate=False, scenario_filter=None):
    """Run all test scenarios and optionally evaluate them."""
    from mediation.engine import MediationEngine
    engine = MediationEngine()
    if not engine.client:
        print("ERROR: ANTHROPIC_API_KEY not found. Check .env file.")
        return None
    client = Anthropic() if evaluate else None

    scenarios = load_scenarios(scenario_filter)
    if not scenarios:
        print("No scenarios found.")
        return None

    results = {
        'timestamp': datetime.now().isoformat(),
        'total_tests': 0,
        'passed': 0,
        'failed': 0,
        'scenarios': []
    }

    for scenario in scenarios:
        test_method = scenario['evaluate']['test_method']
        print(f"\n{'='*60}")
        print(f"  {scenario['name']}")
        print(f"{'='*60}")

        if test_method == 'should_respond':
            # Multiple sub-cases
            scenario_result = {
                'name': scenario['name'],
                'file': scenario['_file'],
                'test_method': test_method,
                'cases': []
            }
            for case in scenario['cases']:
                results['total_tests'] += 1
                actual, expected = run_should_respond_test(engine, case)
                passed = actual == expected
                if passed:
                    results['passed'] += 1
                    status = 'PASS'
                else:
                    results['failed'] += 1
                    status = 'FAIL'

                print(f"  [{status}] {case['name']}: expected={expected}, got={actual}")
                scenario_result['cases'].append({
                    'name': case['name'],
                    'expected': expected,
                    'actual': actual,
                    'passed': passed
                })
            results['scenarios'].append(scenario_result)

        elif test_method == 'welcome':
            scenario_result = {
                'name': scenario['name'],
                'file': scenario['_file'],
                'test_method': test_method,
                'cases': []
            }
            for case in scenario['cases']:
                results['total_tests'] += 1
                print(f"\n  Case: {case['name']}")
                response = run_welcome_test(engine, case)
                print(f"  Response: {response[:120]}...")

                case_result = {
                    'name': case['name'],
                    'response': response,
                    'passed': True  # default if no evaluation
                }

                if evaluate and client:
                    context = (
                        f"Topic: {case['topic']}\nSession mode: {case['session_mode']}\n"
                        f"Creator: {case['creator_name']}\n"
                        f"Their perspective: {case['perspective']}"
                    )
                    eval_result = evaluate_response(client, context, response, case['criteria'])
                    case_result['evaluation'] = eval_result
                    score = eval_result.get('overall_score', 0)
                    passed = score >= 0.7
                    case_result['passed'] = passed
                    case_result['score'] = score

                    if passed:
                        results['passed'] += 1
                    else:
                        results['failed'] += 1

                    print(f"  Score: {score:.2f} {'PASS' if passed else 'FAIL'}")
                    for cr in eval_result.get('criteria_results', []):
                        print(f"    [{cr['result']}] {cr['name']}: {cr['explanation']}")
                else:
                    results['passed'] += 1

                scenario_result['cases'].append(case_result)
            results['scenarios'].append(scenario_result)

        elif test_method == 'mediate':
            results['total_tests'] += 1
            print(f"  Running mediation response...")
            response = run_mediate_test(engine, scenario)
            print(f"  Response: {response[:150]}...")

            scenario_result = {
                'name': scenario['name'],
                'file': scenario['_file'],
                'test_method': test_method,
                'response': response,
                'passed': True
            }

            if evaluate and client:
                context = build_scenario_context(scenario)
                criteria = scenario['evaluate']['criteria']
                eval_result = evaluate_response(client, context, response, criteria)
                scenario_result['evaluation'] = eval_result
                score = eval_result.get('overall_score', 0)
                passed = score >= 0.7
                scenario_result['passed'] = passed
                scenario_result['score'] = score

                if passed:
                    results['passed'] += 1
                else:
                    results['failed'] += 1

                print(f"\n  Score: {score:.2f} {'PASS' if passed else 'FAIL'}")
                for cr in eval_result.get('criteria_results', []):
                    print(f"    [{cr['result']}] {cr['name']}: {cr['explanation']}")
                if eval_result.get('overall_strengths'):
                    print(f"  Strengths: {eval_result['overall_strengths']}")
                if eval_result.get('overall_weaknesses'):
                    print(f"  Weaknesses: {eval_result['overall_weaknesses']}")
            else:
                results['passed'] += 1

            results['scenarios'].append(scenario_result)

    # Summary
    total = results['total_tests']
    passed = results['passed']
    rate = (passed / total * 100) if total else 0
    results['pass_rate'] = rate

    print(f"\n{'='*60}")
    print(f"  RESULTS: {passed}/{total} passed ({rate:.0f}%)")
    print(f"{'='*60}\n")

    # Save to history
    HISTORY_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    history_file = HISTORY_DIR / f"run_{timestamp}.json"
    with open(history_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Results saved to {history_file}")

    return results


def list_scenarios():
    """List all available test scenarios."""
    for path in sorted(SCENARIOS_DIR.glob('*.json')):
        with open(path) as f:
            data = json.load(f)
        method = data['evaluate']['test_method']
        if method in ('should_respond', 'welcome'):
            count = len(data.get('cases', []))
            print(f"  {path.stem}: {data['name']} ({count} cases, method={method})")
        else:
            count = len(data['evaluate'].get('criteria', []))
            print(f"  {path.stem}: {data['name']} ({count} criteria, method={method})")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Vilora Mediation Quality Tests')
    parser.add_argument('--evaluate', action='store_true', help='Enable LLM evaluation')
    parser.add_argument('--scenario', type=str, help='Filter to specific scenario name')
    parser.add_argument('--list', action='store_true', help='List available scenarios')
    args = parser.parse_args()

    if args.list:
        print("\nAvailable test scenarios:")
        list_scenarios()
    else:
        run_all_tests(evaluate=args.evaluate, scenario_filter=args.scenario)
