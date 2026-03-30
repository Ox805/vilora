#!/usr/bin/env python3
"""
Simulate a full mediation session between two test users.

Usage:
    python scripts/test_mediation.py                          # uses local server
    python scripts/test_mediation.py https://your-app.up.railway.app  # uses deployed app

This script:
1. Registers two test users (Alice and Bob)
2. Alice creates a mediation session with her perspective
3. Bob joins and submits his perspective
4. They exchange messages back and forth
5. Requests a summary at the end

You can watch the session live in your browser while it runs.
"""

import sys
import time
import json
import requests

BASE_URL = sys.argv[1].rstrip('/') if len(sys.argv) > 1 else 'http://localhost:5001'

# Test scenario — customize these to test different mediation types
SCENARIO = {
    'topic': 'How to split household chores fairly',
    'type': 'roommate',
    'alice': {
        'email': 'alice.test@example.com',
        'display_name': 'Alice',
        'password': 'testpass123',
        'perspective': (
            "I feel like I'm doing most of the household chores — cooking, cleaning the kitchen, "
            "and doing laundry. Bob helps sometimes but it's inconsistent and I always have to ask. "
            "I'd like us to have a more balanced and predictable system."
        ),
        'messages': [
            "I think the main issue is that there's no clear agreement on who does what. "
            "I end up doing things because they need to get done, not because I want to do everything.",

            "I appreciate that Bob, but the problem is it's not consistent. Some weeks you do a lot, "
            "other weeks nothing. I never know what to expect.",

            "That's a good point. I think I'd feel a lot better if we each had specific things we're "
            "responsible for, so I'm not always wondering if something will get done.",

            "I like that idea. Maybe we could also have a shared list or calendar so we can both "
            "see what needs doing and who's handling it?",

            "Agreed. And I want to say — I'm not trying to micromanage. I just want us both to feel "
            "like it's fair and not have resentment build up over it.",
        ]
    },
    'bob': {
        'email': 'bob.test@example.com',
        'display_name': 'Bob',
        'password': 'testpass123',
        'perspective': (
            "I think Alice underestimates how much I actually do around the house. I handle all the "
            "yard work, take out the trash, fix things when they break, and do the grocery shopping. "
            "It feels like only 'visible' chores count."
        ),
        'messages': [
            "I want to say that I do contribute — I handle the yard, the trash, grocery runs, and "
            "any repairs. It might not be as visible but it's still work.",

            "Fair point. I think part of the issue is we have different ideas of what counts as "
            "'chores.' Maybe we should lay out everything that needs doing and divide it up.",

            "Yeah, I'm open to that. I think the key is we both feel like it's fair — not that "
            "we split everything 50/50 mathematically, but that neither of us feels taken advantage of.",

            "I could definitely do a shared calendar. And maybe we revisit it every month or so "
            "to make sure it's still working for both of us.",

            "Same here. I think this conversation is already helping. Let's try the shared list "
            "thing and check in about it in a few weeks.",
        ]
    }
}


def api(session, method, path, data=None):
    """Make an API call and return the JSON response."""
    url = f"{BASE_URL}{path}"
    if method == 'GET':
        r = session.get(url)
    elif method == 'POST':
        r = session.post(url, json=data)
    elif method == 'DELETE':
        r = session.delete(url)
    else:
        raise ValueError(f"Unknown method: {method}")

    try:
        return r.json()
    except Exception:
        print(f"  ERROR: {r.status_code} — {r.text[:200]}")
        return {'success': False, 'error': r.text[:200]}


def register_or_login(session, user):
    """Register a test user, or log in if they already exist."""
    result = api(session, 'POST', '/api/register', {
        'email': user['email'],
        'display_name': user['display_name'],
        'password': user['password']
    })
    if result.get('success'):
        return True

    # Already registered — try login
    result = api(session, 'POST', '/api/login', {
        'email': user['email'],
        'password': user['password']
    })
    return result.get('success', False)


def main():
    print(f"\n{'='*60}")
    print(f"  Vilora Mediation Test — {BASE_URL}")
    print(f"{'='*60}\n")

    alice_session = requests.Session()
    bob_session = requests.Session()

    # Step 1: Register/login both users
    print("[1] Registering test users...")
    if not register_or_login(alice_session, SCENARIO['alice']):
        print("  FAILED to register/login Alice")
        return
    print(f"  Alice ({SCENARIO['alice']['email']}) — OK")

    if not register_or_login(bob_session, SCENARIO['bob']):
        print("  FAILED to register/login Bob")
        return
    print(f"  Bob ({SCENARIO['bob']['email']}) — OK")

    # Step 2: Alice creates a session
    print(f"\n[2] Alice creates session: \"{SCENARIO['topic']}\"")
    result = api(alice_session, 'POST', '/api/sessions', {
        'topic': SCENARIO['topic'],
        'type': SCENARIO['type'],
        'perspective': SCENARIO['alice']['perspective']
    })
    if not result.get('success'):
        print(f"  FAILED: {result.get('error')}")
        return

    session_data = result['session']
    invite_link = result['invite_link']
    session_id = session_data['id']
    print(f"  Session ID: {session_id}")
    print(f"  Invite link: {invite_link}")

    # Step 3: Bob joins via invite code
    print(f"\n[3] Bob joins the session...")
    invite_code = invite_link.split('/join/')[-1]
    # Visit the join URL to add Bob as participant
    bob_session.get(f"{BASE_URL}/join/{invite_code}", allow_redirects=True)
    # Also submit Bob's perspective
    result = api(bob_session, 'POST', f'/api/sessions/{session_id}/join', {
        'perspective': SCENARIO['bob']['perspective']
    })
    if result.get('success'):
        print("  Bob joined and submitted perspective — OK")
    else:
        print(f"  Join result: {result}")

    # Step 4: Exchange messages
    alice_msgs = SCENARIO['alice']['messages']
    bob_msgs = SCENARIO['bob']['messages']
    total_exchanges = min(len(alice_msgs), len(bob_msgs))

    print(f"\n[4] Simulating {total_exchanges} exchanges...\n")

    for i in range(total_exchanges):
        # Alice sends
        print(f"  Alice: {alice_msgs[i][:70]}...")
        result = api(alice_session, 'POST', f'/api/sessions/{session_id}/messages', {
            'content': alice_msgs[i]
        })
        if result.get('mediator_message'):
            vilora_msg = result['mediator_message']['content']
            print(f"  Vilora: {vilora_msg[:70]}...")
        elif not result.get('success'):
            print(f"  ERROR: {result.get('error')}")

        time.sleep(2)  # Brief pause between messages

        # Bob sends
        print(f"  Bob:   {bob_msgs[i][:70]}...")
        result = api(bob_session, 'POST', f'/api/sessions/{session_id}/messages', {
            'content': bob_msgs[i]
        })
        if result.get('mediator_message'):
            vilora_msg = result['mediator_message']['content']
            print(f"  Vilora: {vilora_msg[:70]}...")
        elif not result.get('success'):
            print(f"  ERROR: {result.get('error')}")

        time.sleep(2)
        print()

    # Step 5: Get summary
    print("[5] Requesting session summary...")
    result = api(alice_session, 'GET', f'/api/sessions/{session_id}/summary')
    if result.get('success'):
        print(f"\n{'='*60}")
        print("  SESSION SUMMARY")
        print(f"{'='*60}")
        print(result['summary'])
    else:
        print(f"  Summary FAILED: {result.get('error')}")

    # Print session URL for manual review
    print(f"\n{'='*60}")
    print(f"  View session in browser:")
    print(f"  {BASE_URL}/session/{session_id}")
    print(f"  Login as Alice: {SCENARIO['alice']['email']} / {SCENARIO['alice']['password']}")
    print(f"  Login as Bob:   {SCENARIO['bob']['email']} / {SCENARIO['bob']['password']}")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
