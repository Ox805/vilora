import os
import sys
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

SHOULD_RESPOND_PROMPT = """You are analyzing a mediation conversation to decide if the mediator (Vilora) \
should chime in right now, or let the participants continue talking.

Vilora should chime in when:
- There have been several exchanges (3+) between participants without mediator input
- A participant directly asks Vilora a question or asks for help
- The conversation is escalating or getting heated
- There's a misunderstanding that needs reframing
- Someone has made a concession or shown willingness to compromise (acknowledge it)
- The conversation seems stuck or going in circles
- There's an opportunity to highlight common ground
- A new participant has just shared their first message in the session

Vilora should stay silent when:
- Participants are having a productive back-and-forth on their own
- Only 1-2 messages have been exchanged since the last mediator input
- The participants are actively building on each other's ideas without conflict

Respond with ONLY "YES" or "NO" — nothing else."""


class MediationEngine:
    def __init__(self):
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if api_key:
            self.client = Anthropic(api_key=api_key)
        else:
            self.client = None

    def frame(self, topic, perspective, session_type):
        if not self.client:
            return "Framing suggestions require an API key to be configured."

        text = ""
        if topic:
            text += f"Topic: {topic}\n"
        if perspective:
            text += f"Their perspective: {perspective}\n"
        if session_type and session_type != 'general':
            text += f"Context: {session_type} mediation\n"

        prompt = (
            f"A user is about to start a mediation session and has written the following:\n\n"
            f"{text}\n"
            f"Help them frame this more effectively for a productive mediation. Provide:\n\n"
            f"1. **Suggested topic** — A clear, neutral one-line description of the issue "
            f"(not blaming either side)\n\n"
            f"2. **Suggested perspective** — A reframed version of their perspective that:\n"
            f"   - Focuses on feelings and needs rather than blame\n"
            f"   - Uses 'I' statements where possible\n"
            f"   - Acknowledges the other person's likely perspective\n"
            f"   - Is specific about what they'd like to resolve\n\n"
            f"3. **Tips** — 2-3 brief tips for how to approach this mediation constructively\n\n"
            f"Keep the tone warm and encouraging. Format with clear headers."
        )

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=(
                "You are Vilora, an AI mediation assistant. You're helping someone "
                "prepare for a mediation session by framing their issue constructively. "
                "Be warm, supportive, and practical."
            ),
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text

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
            model="claude-sonnet-4-20250514",
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text

    def should_respond(self, topic, messages, participants):
        """Decide whether Vilora should chime in based on conversation state."""
        if not self.client:
            return True

        participant_names = {p.id: p.display_name for p in participants}

        # Always respond to the very first user message in the session
        user_messages = [m for m in messages if m.msg_type == 'user']
        if len(user_messages) <= 1:
            return True

        # Count user messages since last mediator response
        msgs_since_mediator = 0
        for m in reversed(messages):
            if m.msg_type == 'mediator':
                break
            if m.msg_type == 'user':
                msgs_since_mediator += 1

        # If many messages have passed, always respond
        if msgs_since_mediator >= 5:
            return True

        # If only 1 message since last mediator response, usually skip
        if msgs_since_mediator <= 1:
            return False

        # For 2-4 messages, ask Claude to decide
        recent = messages[-8:]  # last 8 messages for context
        conversation_text = ""
        for msg in recent:
            if msg.msg_type == 'mediator':
                conversation_text += f"[Vilora]: {msg.content}\n\n"
            elif msg.msg_type == 'user':
                name = participant_names.get(msg.user_id, 'Unknown')
                conversation_text += f"[{name}]: {msg.content}\n\n"
            elif msg.msg_type == 'intake':
                name = participant_names.get(msg.user_id, 'Unknown')
                conversation_text += f"[{name}'s initial perspective]: {msg.content}\n\n"

        prompt = (
            f"Mediation topic: {topic}\n\n"
            f"Recent conversation:\n{conversation_text}\n"
            f"Messages since last mediator input: {msgs_since_mediator}\n\n"
            f"Should the mediator chime in now?"
        )

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=10,
                system=SHOULD_RESPOND_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            answer = response.content[0].text.strip().upper()
            return answer.startswith("YES")
        except Exception as e:
            sys.stderr.write(f"[Vilora] Error in should_respond: {e}\n")
            # Default to responding if we can't decide
            return msgs_since_mediator >= 3

    def mediate(self, topic, session_type, messages, participants):
        if not self.client:
            return self._fallback_response(messages)

        participant_names = {p.id: p.display_name for p in participants}
        conversation = self._build_conversation(topic, session_type, messages, participant_names)

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
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
            model="claude-sonnet-4-20250514",
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
