import os
import sys
import random
from concurrent.futures import ThreadPoolExecutor
from anthropic import Anthropic

COUNSELOR_PROMPT = """You are Vilora, a warm and insightful AI counselor and advisor. In this mode, you're \
having a one-on-one conversation with someone who wants to think through a challenge, get advice, or \
just talk something out.

## Core Principles

1. **Genuine Care**: You care about this person's wellbeing. Your responses should feel warm, \
thoughtful, and human — not clinical or formulaic.

2. **Active Listening**: Reflect back what you hear. Ask clarifying questions. Make sure the person \
feels truly understood before offering perspective.

3. **Honest Guidance**: Share your perspective honestly but gently. Don't just validate — if you see \
a blind spot or a different way to look at things, say so with care.

4. **Practical Wisdom**: Help people think through situations concretely. What are the options? \
What are the tradeoffs? What would they advise a friend in the same situation?

5. **Empowerment**: Help people find their own answers. Ask questions that help them think more \
clearly rather than just telling them what to do.

6. **Boundaries**: You're a supportive advisor, not a licensed therapist. If someone describes \
a crisis, abuse, or serious mental health concerns, acknowledge their pain and encourage them \
to reach out to a professional or crisis resource.

## Communication Style

- Warm, direct, and genuine — like a thoughtful friend who happens to give great advice
- Ask open-ended questions to deepen understanding
- Share observations using "I notice..." or "It sounds like..."
- Offer perspective when you have it, frame it as "one way to think about it..."
- Celebrate their self-awareness and willingness to reflect
- Be honest about the limits of what you can help with

## Knowledge & Reference

When the user asks factual questions or needs information on any topic, provide accurate, helpful \
answers directly. You're a knowledgeable resource across all domains. If they're researching options, \
exploring ideas, or need context to make a decision, give them substantive information. Always note \
when information may be outdated or when professional advice should be sought for final decisions.

## Session Awareness

Stay focused on what the person wants to discuss. Follow their lead but gently guide toward \
clarity and actionable next steps when the conversation is ready for it.
"""

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

## Knowledge & Reference

When participants ask factual questions, request data, or need expert context, provide accurate, \
helpful information directly in the conversation. You serve as a knowledgeable reference on any topic. \
For example, if a brainstorming session about international expansion needs information about tax \
regulations, cultural norms, or market conditions in a specific country, provide that information \
clearly and concisely. Always note when information may be outdated or when professional advice \
(legal, medical, financial) should be sought for final decisions.

## Session Awareness

You are facilitating a specific topic. Stay focused on that topic while being flexible enough to \
address related issues that emerge. Keep track of what has been agreed upon and what remains unresolved.

When participants reach agreements, clearly state them and confirm both parties accept.
"""

SHOULD_RESPOND_PROMPT = """You are analyzing a mediation conversation to decide if the mediator (Vilora) \
should chime in right now, or let the participants continue talking.

Vilora should chime in when:
- A participant asks a question, requests information, or asks for facts/data/research
- A participant directly addresses Vilora or asks for help
- There have been several exchanges (3+) between participants without mediator input
- The conversation is escalating or getting heated
- There's a misunderstanding that needs reframing
- Someone has made a concession or shown willingness to compromise (acknowledge it)
- The conversation seems stuck or going in circles
- There's an opportunity to highlight common ground
- A new participant has just shared their first message in the session

Vilora should stay silent when:
- Participants are having a productive back-and-forth on their own
- Only 1-2 messages have been exchanged since the last mediator input AND no one is asking a question
- The participants are actively building on each other's ideas without conflict

Respond with ONLY "YES" or "NO" — nothing else."""


class MediationEngine:
    def __init__(self):
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if api_key:
            self.client = Anthropic(api_key=api_key)
        else:
            self.client = None

    def generate_title(self, text):
        """Generate a short session title from the user's input."""
        if not self.client:
            # Fallback: truncate to first sentence or 60 chars
            first_line = text.split('.')[0].split('\n')[0].strip()
            return first_line[:60] if len(first_line) > 60 else first_line

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=60,
            system=(
                "Generate a brief, empathetic session title (under 60 characters) from the user's message. "
                "The title should capture the core theme without being clinical or judgmental. "
                "Examples: 'Feeling overwhelmed at work', 'Navigating a tough conversation with my partner'. "
                "Respond with ONLY the title text — no quotes, no punctuation at the end, no explanation."
            ),
            messages=[{"role": "user", "content": text}]
        )
        return response.content[0].text.strip().strip('"\'')

    def polish(self, text):
        """Polish text for spelling, punctuation, and clarity without changing voice or meaning."""
        if not self.client:
            return text

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=(
                "You are a writing assistant. Your ONLY job is to clean up the user's text. "
                "Fix spelling errors, punctuation, and grammar. Improve clarity where a sentence "
                "is confusing or awkwardly phrased. Do NOT change the meaning, tone, voice, or "
                "personality of the writing. Do NOT add new ideas, remove ideas, or restructure "
                "the content. Do NOT make it sound more formal or 'polished' in tone. Keep it "
                "sounding exactly like the person who wrote it, just with fewer errors. "
                "If the text is already clean, return it unchanged. "
                "Respond with ONLY the polished text, nothing else."
            ),
            messages=[{"role": "user", "content": text}]
        )

        return response.content[0].text

    def frame(self, raw_text, user_memories=None):
        if not self.client:
            return None

        memory_context = ""
        if user_memories:
            context = self._build_memory_context(user_memories)
            if context:
                memory_context = (
                    f"\n\nYou know the following about this user from past sessions:\n{context}\n"
                    f"Use this to make your framing suggestions more attuned to who they are — "
                    f"but don't explicitly reference what you know. Just let it inform your tone and advice."
                )

        prompt = (
            f"A user wants to start a mediation session. They've described their situation "
            f"in their own words:\n\n"
            f"\"{raw_text}\"\n\n"
            f"Help them prepare by extracting and lightly refining their input into structured fields. "
            f"IMPORTANT: preserve their voice, tone, and intent. Only make small, targeted adjustments. "
            f"If their phrasing is already clear and genuine, leave it mostly as-is. "
            f"Do NOT put words in their mouth or add things they didn't say.{memory_context}\n\n"
            f"Respond in EXACTLY this JSON format (no markdown, no code fences, just raw JSON):\n"
            f'{{\n'
            f'  "topic": "A clear, neutral one-line description of the issue (not blaming either side)",\n'
            f'  "type": "one of: general, relationship, family, workplace, roommate, political, neighbor, business",\n'
            f'  "perspective": "Their perspective with only light edits — soften accusatory language, '
            f'add I-feel/I-need framing where natural, keep their original examples and personality",\n'
            f'  "tips": "2-3 brief practical tips for approaching this mediation, as a single string"\n'
            f'}}'
        )

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=(
                "You are Vilora, an AI mediation assistant. You help people frame their "
                "issues for productive mediation. Always respond with valid JSON only — "
                "no markdown, no code fences, no extra text."
            ),
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text

    def welcome(self, topic, session_type, perspective, creator_name, session_mode='mediation'):
        if not self.client:
            if session_mode == 'personal':
                return (
                    f"Thanks for sharing that, {creator_name}. "
                    "I'm here to help you think this through. What would be most helpful right now?"
                )
            return (
                f"Thank you for sharing your perspective, {creator_name}. "
                "I'm ready to help mediate once the other party joins. "
                "Please share the invite link with them so we can begin."
            )

        if session_mode == 'personal':
            tone_instruction = ""
            if "[Session tone:" in perspective:
                tone_instruction = "\nIMPORTANT: The user has indicated how they want you to approach this conversation. Follow that guidance closely.\n"
            prompt = (
                f"Topic: {topic}\n\n"
                f"{creator_name} wants to talk one-on-one about something:\n\n"
                f"\"{perspective}\"\n\n"
                f"Respond warmly and personally. This is a private conversation, not a mediation.\n"
                f"1. Acknowledge what they've shared with genuine empathy\n"
                f"2. Show you understand the situation and how they might be feeling\n"
                f"3. Ask a thoughtful follow-up question to help them explore further\n"
                f"Keep it concise and conversational — like a caring friend, not a therapist."
                f"{tone_instruction}"
            )
            system = COUNSELOR_PROMPT
        else:
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
            system = SYSTEM_PROMPT

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=512,
            system=system,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text

    def should_respond(self, topic, messages, participants, session_mode='mediation'):
        """Decide whether Vilora should chime in based on conversation state."""
        if not self.client:
            return True

        # In personal/counseling mode, always respond
        if session_mode == 'personal':
            return True

        participant_names = {p.id: p.display_name for p in participants}

        # Always respond to the very first user message in the session
        user_messages = [m for m in messages if m.msg_type == 'user']
        if len(user_messages) <= 1:
            return True

        # Count user messages since last mediator response
        msgs_since_mediator = 0
        last_user_msg = None
        for m in reversed(messages):
            if m.msg_type == 'mediator':
                break
            if m.msg_type == 'user':
                msgs_since_mediator += 1
                if last_user_msg is None:
                    last_user_msg = m.content

        # Check if the latest message looks like a question or info request
        is_question = last_user_msg and ('?' in last_user_msg or
            any(last_user_msg.lower().lstrip().startswith(w) for w in
                ['what ', 'how ', 'why ', 'when ', 'where ', 'who ', 'can you ',
                 'could you ', 'tell me ', 'explain ', 'vilora', 'do you know']))

        # If someone is asking a question, always respond
        if is_question:
            return True

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

    def mediate(self, topic, session_type, messages, participants, participant_memories=None, session_mode='mediation', user_question=None):
        if not self.client:
            return self._fallback_response(messages)

        participant_names = {p.id: p.display_name for p in participants}
        conversation = self._build_conversation(topic, session_type, messages, participant_names, session_mode=session_mode)

        # Build personalized system prompt with memories
        system = COUNSELOR_PROMPT if session_mode == 'personal' else SYSTEM_PROMPT
        if participant_memories:
            memory_sections = []
            for user_id, memories in participant_memories.items():
                name = participant_names.get(user_id, 'Unknown')
                context = self._build_memory_context(memories)
                if context:
                    memory_sections.append(f"\n## What you know about {name}:\n{context}")
            if memory_sections:
                system += (
                    "\n\n## Participant Knowledge\n"
                    "Use this knowledge naturally — don't explicitly reference it unless directly relevant. "
                    "The goal is for your responses to feel attuned and personal. "
                    "NEVER reveal one participant's memories to another participant."
                    + "\n".join(memory_sections)
                )

        if user_question:
            conversation = conversation + [{
                "role": "user",
                "content": (
                    f"A participant is asking you a specific question: \"{user_question}\"\n\n"
                    "Respond directly to that question. Draw on the conversation above as context, "
                    "but keep your answer focused on what they actually asked."
                )
            }]

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system,
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

    def _build_conversation(self, topic, session_type, messages, participant_names, session_mode='mediation'):
        conversation = []

        # Build context from intake messages
        if session_mode == 'personal':
            intake_context = f"Topic: {topic}\n\n"
            intake_messages = [m for m in messages if m.msg_type == 'intake']
            if intake_messages:
                name = participant_names.get(intake_messages[0].user_id, 'Someone')
                intake_context += f"{name} wants to talk about this:\n\n"
                for msg in intake_messages:
                    intake_context += f"{msg.content}\n\n"

            conversation.append({"role": "user", "content": intake_context})
            conversation.append({
                "role": "assistant",
                "content": "Thank you for sharing this with me. I'm here to listen and help you think through this. "
                           "Let me make sure I understand what's on your mind."
            })
        else:
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
                "content": "Thank you both for sharing your perspectives on this. "
                           "I'm here to help you work through this together. "
                           "Let me make sure I understand each of your viewpoints before we proceed."
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
                # Strip summary prefix if present
                content = msg.content
                if '<!--SUMMARY-->' in content:
                    content = content.split('<!--SUMMARY-->')[1].strip()
                conversation.append({
                    "role": "assistant",
                    "content": content
                })

        return conversation

    def extract_memories(self, user_name, user_id, topic, messages, participants, existing_memories=None):
        """Extract new memories about a user from a session transcript."""
        if not self.client:
            return []

        participant_names = {p.id: p.display_name for p in participants}

        # Build transcript
        transcript = f"Topic: {topic}\n\n"
        for msg in messages:
            if msg.msg_type == 'intake':
                name = participant_names.get(msg.user_id, 'Unknown')
                transcript += f"[{name}'s initial perspective]: {msg.content}\n\n"
            elif msg.msg_type == 'user':
                name = participant_names.get(msg.user_id, 'Unknown')
                transcript += f"[{name}]: {msg.content}\n\n"
            elif msg.msg_type == 'mediator':
                transcript += f"[Vilora]: {msg.content}\n\n"

        # Format existing memories
        existing_text = "None yet."
        if existing_memories:
            existing_text = "\n".join(
                f"- [{m['category']}] {m['content']}" for m in existing_memories
            )

        prompt = (
            f"You are analyzing a mediation session to learn about the participant named "
            f"**{user_name}**. Extract insights that would help you be a better, more personal "
            f"mediator for them in future sessions.\n\n"
            f"Only extract things that are genuinely useful and clearly demonstrated — not "
            f"trivial details or wild guesses. Focus on what makes this person tick: their values, "
            f"how they communicate, what matters to them, what triggers them, and how they handle conflict.\n\n"
            f"Do NOT duplicate existing memories. If an existing memory should be updated or "
            f"refined based on new evidence, include it with the updated content.\n\n"
            f"**Existing memories about {user_name}:**\n{existing_text}\n\n"
            f"**Session transcript:**\n{transcript}\n\n"
            f"Respond with ONLY a JSON array (no markdown, no code fences). Each item:\n"
            f'{{"category": "profile|communication|history|pattern|preference", '
            f'"content": "the insight in natural language", '
            f'"confidence": 0.0-1.0}}\n\n'
            f"If there are no meaningful new insights, return an empty array: []"
        )

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=(
                    "You extract personal insights about mediation participants to help "
                    "personalize future sessions. Return valid JSON only — no markdown, "
                    "no code fences, no extra text. Be selective — quality over quantity."
                ),
                messages=[{"role": "user", "content": prompt}]
            )
            import json
            return json.loads(response.content[0].text)
        except Exception as e:
            sys.stderr.write(f"[Vilora] Memory extraction error: {e}\n")
            return []

    def _build_memory_context(self, user_memories):
        """Format user memories for inclusion in system prompt."""
        if not user_memories:
            return ""

        sections = {}
        for m in user_memories:
            cat = m.get('category', 'other')
            if cat not in sections:
                sections[cat] = []
            sections[cat].append(m['content'])

        labels = {
            'profile': 'About them',
            'communication': 'Communication style',
            'history': 'Past mediations',
            'pattern': 'Patterns noticed',
            'preference': 'Their preferences for how you interact'
        }

        lines = []
        for cat, items in sections.items():
            label = labels.get(cat, cat.title())
            lines.append(f"**{label}:** " + "; ".join(items))

        return "\n".join(lines)

    # --- Council ---

    COUNCIL_ADVISORS = [
        ('The Contrarian', (
            "You are a skeptical advisor who looks for what will fail. Your job is to find the "
            "weakest points in this plan, idea, or decision. If everything looks solid on the "
            "surface, dig deeper. You're not being negative for the sake of it. You're protecting "
            "the person from the blind spots that come with enthusiasm. What risks are being "
            "underestimated? What could go wrong that nobody is talking about? "
            "Keep your analysis to 150-250 words. Be specific and direct."
        )),
        ('The First Principles Thinker', (
            "You strip away assumptions and rebuild the problem from the ground up. Don't accept "
            "the question at face value. Ask: what is the real goal here? Is this the right question "
            "to be asking? Are there hidden assumptions baked into the framing? Sometimes the best "
            "answer is that the question itself needs to change. "
            "Keep your analysis to 150-250 words. Be specific and direct."
        )),
        ('The Expansionist', (
            "You look for what could be bigger, better, or more ambitious. What adjacent opportunity "
            "is sitting right next to this question that the person hasn't noticed? What would this "
            "look like if there were no constraints? Where is the hidden leverage? Your job is to "
            "stretch the thinking beyond the obvious. "
            "Keep your analysis to 150-250 words. Be specific and direct."
        )),
        ('The Outsider', (
            "You respond purely to what's in front of you with no insider knowledge. You don't know "
            "the jargon, the industry norms, or the 'way things are usually done.' This is your "
            "strength. Ask the obvious questions that experts forget to ask. Point out things that "
            "seem strange to a fresh pair of eyes. What would a smart person with no background in "
            "this area notice? "
            "Keep your analysis to 150-250 words. Be specific and direct."
        )),
        ('The Executor', (
            "You focus exclusively on actionability. If an idea sounds brilliant but has no clear "
            "first step, say so. What is the smallest concrete action that would move this forward? "
            "What needs to happen first, second, third? Cut through analysis paralysis. A mediocre "
            "plan executed today beats a perfect plan discussed forever. "
            "Keep your analysis to 150-250 words. Be specific and direct."
        )),
    ]

    def run_council(self, question, context=None, user_memories=None):
        """Run the Vilora Council: 5 advisors + peer review + synthesis."""
        if not self.client:
            return None

        full_question = f"Question: {question}"
        if context:
            full_question += f"\n\nContext: {context}"
        if user_memories:
            memory_ctx = self._build_memory_context(user_memories)
            if memory_ctx:
                full_question += f"\n\nAbout the person asking:\n{memory_ctx}"

        # Step 1: Run 5 advisors in parallel
        def get_advisor_response(name, system_prompt):
            try:
                response = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=512,
                    system=system_prompt,
                    messages=[{"role": "user", "content": full_question}]
                )
                return (name, response.content[0].text)
            except Exception as e:
                sys.stderr.write(f"[Vilora Council] Advisor {name} error: {e}\n")
                return (name, f"[This advisor was unable to respond: {e}]")

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(get_advisor_response, name, prompt)
                for name, prompt in self.COUNCIL_ADVISORS
            ]
            advisor_results = [f.result() for f in futures]

        # Step 2: Anonymous peer review
        review = self._council_peer_review(advisor_results)

        # Step 3: Chairman synthesis
        synthesis = self._council_synthesize(question, advisor_results, review)

        return {
            'advisors': [{'name': name, 'response': resp} for name, resp in advisor_results],
            'review': review,
            'synthesis': synthesis
        }

    def _council_peer_review(self, advisor_results):
        """Review all advisor responses and identify strengths, blind spots, and gaps."""
        review_text = "Five AI advisors have analyzed the same question. Their responses are below.\n\n"
        for name, response in advisor_results:
            review_text += f"**{name}:**\n{response}\n\n"

        review_text += (
            "As an impartial reviewer, answer these three questions. "
            "Refer to each advisor by their name (The Contrarian, The First Principles Thinker, etc.).\n"
            "1. Which response is the strongest and why?\n"
            "2. Which response has the biggest blind spot and what is it?\n"
            "3. What did ALL FIVE responses miss? What important consideration did none of them raise?\n\n"
            "Be specific and concise."
        )

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system="You are an impartial reviewer analyzing multiple advisory perspectives on the same question.",
                messages=[{"role": "user", "content": review_text}]
            )
            return response.content[0].text
        except Exception as e:
            sys.stderr.write(f"[Vilora Council] Peer review error: {e}\n")
            return "Peer review was unable to be completed."

    def _council_synthesize(self, question, advisor_results, review):
        """Chairman synthesis of all advisor responses and peer review."""
        synthesis_text = f"Original question: {question}\n\n"
        synthesis_text += "Five advisors analyzed this question. Here are their perspectives:\n\n"

        for name, response in advisor_results:
            synthesis_text += f"**{name}:**\n{response}\n\n"

        synthesis_text += f"**Peer Review:**\n{review}\n\n"

        synthesis_text += (
            "As the chairman, synthesize everything above into a clear, actionable report:\n"
            "1. **Key insight from each advisor** (1-2 sentences each)\n"
            "2. **Where the advisors agree** (common themes)\n"
            "3. **Where they disagree** (tensions and tradeoffs)\n"
            "4. **The blind spot** (what the peer review identified as missed)\n"
            "5. **Recommendation** with a confidence level (high/medium/low)\n"
            "6. **One concrete next step** (what to do first)\n\n"
            "Be clear, direct, and actionable."
        )

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                system=(
                    "You are the chairman of an advisory council. Your job is to synthesize "
                    "multiple perspectives into a clear recommendation. Be decisive but fair. "
                    "Acknowledge disagreements honestly. Always end with one concrete action."
                ),
                messages=[{"role": "user", "content": synthesis_text}]
            )
            return response.content[0].text
        except Exception as e:
            sys.stderr.write(f"[Vilora Council] Synthesis error: {e}\n")
            return "Synthesis was unable to be completed."

    def summarize_response(self, response_text):
        """Not used. Previews are generated client-side from the first few sentences."""
        return None

    def _fallback_response(self, messages):
        return (
            "I appreciate you sharing that. To provide the best mediation experience, "
            "please ensure the ANTHROPIC_API_KEY environment variable is configured. "
            "Once set up, I'll be able to fully engage as your mediator."
        )
