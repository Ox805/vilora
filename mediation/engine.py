import os
from anthropic import Anthropic

SYSTEM_PROMPT = """You are Vilora, an expert AI mediator. Your role is to facilitate productive dialogue \
between participants who have a disagreement, conflict, or unresolved issue.

## Core Principles

1. **Impartiality**: You never take sides. You treat all participants' perspectives as equally valid \
and worthy of exploration. You do not judge, blame, or favor anyone.

2. **Active Listening**: You reflect back what each person has said to confirm understanding before \
moving forward. You identify the emotions and needs behind positions.

3. **Reframing**: You translate accusatory or inflammatory language into neutral observations. \
"You always ignore me" becomes "It sounds like you feel unheard in certain situations."

4. **Finding Common Ground**: You actively identify and highlight areas where participants agree, \
even small ones. You build on shared values and goals.

5. **Structured Progress**: You guide the conversation through phases:
   - Understanding each person's perspective
   - Identifying underlying needs and interests (not just positions)
   - Finding areas of agreement
   - Exploring possible solutions
   - Working toward concrete next steps

6. **De-escalation**: If emotions run high, you acknowledge the feelings, slow the pace, and \
redirect toward constructive dialogue. You never match escalation with escalation.

7. **Safety**: If you detect signs of abuse, threats, or danger, you clearly state that mediation \
is not appropriate and provide relevant crisis resources.

## Communication Style

- Warm but professional
- Ask open-ended questions to deepen understanding
- Summarize frequently to ensure everyone feels heard
- Use "I notice..." and "It seems like..." rather than definitive statements about people's feelings
- Celebrate progress, no matter how small
- Be honest when the conversation is stuck and suggest new approaches

## Session Awareness

You are mediating a specific topic. Stay focused on that topic while being flexible enough to \
address related issues that emerge. Keep track of what has been agreed upon and what remains unresolved.

When participants reach agreements, clearly state them and confirm both parties accept.
"""


class MediationEngine:
    def __init__(self):
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if api_key:
            self.client = Anthropic(api_key=api_key)
        else:
            self.client = None

    def welcome(self, topic, session_type, perspective, creator_name):
        if not self.client:
            return (
                f"Thank you for sharing your perspective, {creator_name}. "
                "I'm ready to help mediate once the other party joins. "
                "Please share the invite link with them so we can begin."
            )

        prompt = (
            f"Mediation Topic: {topic}\n"
            f"Type: {session_type}\n\n"
            f"{creator_name} has started this mediation session and shared their initial perspective:\n\n"
            f"\"{perspective}\"\n\n"
            f"The other party has not joined yet. Please:\n"
            f"1. Acknowledge {creator_name}'s perspective warmly\n"
            f"2. Let them know you understand the situation\n"
            f"3. Remind them to share the invite link with the other party\n"
            f"4. Let them know you'll facilitate once both parties are present\n"
            f"Keep it concise — 2-3 short paragraphs."
        )

        response = self.client.messages.create(
            model="claude-sonnet-4-6-20250514",
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text

    def mediate(self, topic, session_type, messages, participants):
        if not self.client:
            return self._fallback_response(messages)

        participant_names = {p.id: p.display_name for p in participants}
        conversation = self._build_conversation(topic, session_type, messages, participant_names)

        response = self.client.messages.create(
            model="claude-sonnet-4-6-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=conversation
        )

        return response.content[0].text

    def summarize(self, topic, messages, participants):
        if not self.client:
            return "Summary unavailable — API key not configured."

        participant_names = {p.id: p.display_name for p in participants}

        summary_prompt = f"Topic: {topic}\n\nPlease provide a summary of this mediation session including:\n"
        summary_prompt += "1. Each participant's key concerns\n"
        summary_prompt += "2. Areas of agreement reached\n"
        summary_prompt += "3. Unresolved issues\n"
        summary_prompt += "4. Suggested next steps\n\n"
        summary_prompt += "Conversation:\n"

        for msg in messages:
            if msg.msg_type == 'intake':
                name = participant_names.get(msg.user_id, 'Unknown')
                summary_prompt += f"[Intake - {name}]: {msg.content}\n"
            elif msg.msg_type == 'user':
                name = participant_names.get(msg.user_id, 'Unknown')
                summary_prompt += f"[{name}]: {msg.content}\n"
            elif msg.msg_type == 'mediator':
                summary_prompt += f"[Vilora]: {msg.content}\n"

        response = self.client.messages.create(
            model="claude-sonnet-4-6-20250514",
            max_tokens=2048,
            system="You are a mediation session summarizer. Provide clear, neutral summaries.",
            messages=[{"role": "user", "content": summary_prompt}]
        )

        return response.content[0].text

    def _build_conversation(self, topic, session_type, messages, participant_names):
        conversation = []

        # Build context from intake messages
        intake_context = f"Mediation Topic: {topic}\nType: {session_type}\n\n"
        intake_messages = [m for m in messages if m.msg_type == 'intake']
        if intake_messages:
            intake_context += "Initial perspectives from each participant:\n\n"
            for msg in intake_messages:
                name = participant_names.get(msg.user_id, 'Unknown')
                intake_context += f"**{name}**: {msg.content}\n\n"

        conversation.append({"role": "user", "content": intake_context})
        conversation.append({
            "role": "assistant",
            "content": f"Thank you both for sharing your perspectives on this. "
                       f"I'm here to help you work through this together. "
                       f"Let me make sure I understand each of your viewpoints before we proceed."
        })

        # Add conversation messages
        for msg in messages:
            if msg.msg_type == 'user':
                name = participant_names.get(msg.user_id, 'Unknown')
                conversation.append({
                    "role": "user",
                    "content": f"[{name}]: {msg.content}"
                })
            elif msg.msg_type == 'mediator':
                conversation.append({
                    "role": "assistant",
                    "content": msg.content
                })

        return conversation

    def _fallback_response(self, messages):
        return (
            "I appreciate you sharing that. To provide the best mediation experience, "
            "please ensure the ANTHROPIC_API_KEY environment variable is configured. "
            "Once set up, I'll be able to fully engage as your mediator."
        )
