"""Mediation frameworks for different dispute types.

Each framework provides additional system prompt context tailored to
the specific type of conflict being mediated.
"""

FRAMEWORKS = {
    'general': {
        'name': 'General Mediation',
        'description': 'For any type of disagreement or conflict',
        'context': ''
    },
    'relationship': {
        'name': 'Relationship',
        'description': 'For couples, partners, or close personal relationships',
        'context': """Additional context for relationship mediation:
- Focus on attachment needs, emotional safety, and communication patterns
- Help identify recurring cycles and triggers
- Emphasize "I" statements and emotional vocabulary
- Look for bids for connection that may be disguised as complaints
- Remember: the goal is not to determine who is "right" but to rebuild understanding
- Be alert to power imbalances or signs of controlling behavior
"""
    },
    'family': {
        'name': 'Family',
        'description': 'For family disputes (siblings, parents, extended family)',
        'context': """Additional context for family mediation:
- Acknowledge that family relationships carry decades of history
- Be aware of generational patterns and cultural expectations
- Help separate past grievances from present issues
- Focus on preserving the relationship alongside resolving the issue
- Be sensitive to power dynamics between parents and adult children
"""
    },
    'workplace': {
        'name': 'Workplace',
        'description': 'For professional disagreements and team conflicts',
        'context': """Additional context for workplace mediation:
- Maintain professional framing while acknowledging personal feelings
- Consider organizational context, roles, and power dynamics
- Focus on shared professional goals and team effectiveness
- Help translate personal frustrations into actionable process improvements
- Be aware of HR and legal implications — advise professional consultation when appropriate
"""
    },
    'roommate': {
        'name': 'Roommate / Housemate',
        'description': 'For shared living arrangement conflicts',
        'context': """Additional context for roommate mediation:
- Focus on concrete, practical agreements (chores, noise, guests, shared spaces)
- Help create clear expectations and boundaries
- Acknowledge that different standards of living are valid
- Work toward written agreements on specific issues
"""
    },
    'political': {
        'name': 'Political / Social Issues',
        'description': 'For disagreements on political, social, or cultural topics',
        'context': """Additional context for political/social issue discussions:
- Focus on understanding values and experiences behind positions, not winning arguments
- Help participants see that people with different conclusions often share underlying values
- Distinguish between facts, interpretations, and values
- Encourage intellectual humility and genuine curiosity
- The goal is mutual understanding, not necessarily agreement
- Help identify specific claims that can be fact-checked vs. value differences
"""
    },
    'neighbor': {
        'name': 'Neighbor Dispute',
        'description': 'For conflicts between neighbors',
        'context': """Additional context for neighbor mediation:
- Focus on practical coexistence and clear boundaries
- Help create specific, measurable agreements
- Acknowledge that both parties must continue living near each other
- Consider local ordinances and norms as reference points, not as weapons
"""
    },
    'business': {
        'name': 'Business Partnership',
        'description': 'For disputes between business partners or co-founders',
        'context': """Additional context for business partnership mediation:
- Balance personal relationship with business interests
- Focus on shared vision and where it has diverged
- Help clarify roles, expectations, and decision-making processes
- Consider financial implications and suggest professional consultation when needed
- Work toward documented agreements on specific business decisions
"""
    }
}


def get_framework(session_type):
    return FRAMEWORKS.get(session_type, FRAMEWORKS['general'])


def get_framework_list():
    return [
        {'key': k, 'name': v['name'], 'description': v['description']}
        for k, v in FRAMEWORKS.items()
    ]
