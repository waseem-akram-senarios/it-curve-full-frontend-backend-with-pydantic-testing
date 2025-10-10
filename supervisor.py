# import os
# import json
# import asyncio

# from decimal import Decimal
# from logging_config import get_logger

# # Initialize logger
# logger = get_logger('supervisor')
# from pydantic import BaseModel, Field
# from livekit import api
# from livekit.protocol.sip import TransferSIPParticipantRequest
# from livekit.agents.llm import ChatContext, ChatMessage
# from livekit.plugins import openai
# from livekit.plugins.turn_detector.multilingual import MultilingualModel
# from livekit.agents import (
#     AgentSession,
#     ConversationItemAddedEvent,
#     CloseEvent,
#     metrics,
#     MetricsCollectedEvent
# )

# class SupervisorScore(BaseModel):
#     """Supervisor scores"""
#     relevance: Decimal = Field(ge=0, le=1, description="Relevance score 0 to 1")
#     completeness: Decimal = Field(ge=0, le=1, description="Completeness score 0 to 1")
#     groundedness: Decimal = Field(ge=0, le=1, description="Groundedness score 0 to 1")


# class Supervisor:
#     def __init__(self,
#                  session: AgentSession,
#                  room,
#                  llm = None) -> None:
#         self.session = session
#         self.llm = llm if llm else openai.LLM(model="gpt-4o-mini")
#         self.room = room

#         self.first_greeting_done = False
#         self.escalated_to_live_agent = False
#         self.nth_issue = 0
#         self.score_history = []

#     async def start(self):
#         # Create a synchronous wrapper for the close event since it's async
#         def on_close_wrapper(ev):
#             asyncio.create_task(self._on_close(ev))

#         # Wire event handlers (class-bound methods)
#         self.session.on("conversation_item_added")(self._on_added)
#         self.session.on("close")(on_close_wrapper)

#         self.usage_collector = metrics.UsageCollector()
#         @self.llm.on("metrics_collected")
#         def on_metrics_collected(ev: MetricsCollectedEvent):
#             self.usage_collector.collect(ev)

#     def _on_added(self, ev: ConversationItemAddedEvent):
#         if self.escalated_to_live_agent:
#             return
#         if self.first_greeting_done is False and ev.item.role == "assistant":
#             self.first_greeting_done = True
#             return

#         if ev.item.role == "assistant":
#             asyncio.create_task(self._score_response_and_act())

#     async def _score_response_and_act(self):
#         prompt = """You are a deterministic supervisor that scores one bot reply against one user message.
# Return only a compact JSON with three numbers: "relevance", "completeness", "groundedness".

# Inputs (in the user message):
# - "user_text": the user's utterance for this turn.
# - "bot_text": the bot's reply for this turn.

# Scoring (0-1, two decimals; any value in this range is allowed):
# - Relevance: how directly the reply addresses the user's intent or asks a focused clarifying question that advances it.
# - Completeness: whether the reply covers the necessary elements for this step or gives a clear next action; major omissions → lower score.
# - Groundedness: whether statements are supported by provided context or make no external claims; unsupported/conflicting claims → lower score.

# Frustration handling:
# - If the user appears frustrated (e.g., complaints, “you're not listening,” repeated re-asks) and the bot fails to address or fix the issue in this turn, assign **lower values** to the scores to reflect the poor experience.

# Output format — output ONLY this JSON (no extra text/keys):
# {"relevance": x.xx, "completeness": x.xx, "groundedness": x.xx}

# If uncertain, choose the lower score."""

#         chat_ctx = ChatContext([ChatMessage(role="system", content=[prompt]),
#                                 *self.session._chat_ctx.items[-6:]])

#         result = ""
#         async with self.llm.chat(chat_ctx=chat_ctx) as stream:
#             async for chunk in stream:
#                 d = getattr(chunk, "delta", None)
#                 if d and d.content:
#                     result += d.content

#         try:
#             score = SupervisorScore.model_validate(json.loads(result))
#         except Exception as e:
#             logger.debug(f"[supervisor llm response] {result}")
#             logger.error(f"[supervisor score parse error] {e}")
#             return

#         avg_score = (score.relevance + score.completeness + score.groundedness) / 3
#         logger.info(f"[supervisor score] {score} = {avg_score}")

#         self.score_history.append({
#             "relevance": str(float(score.relevance)),
#             "completeness": str(float(score.completeness)),
#             "groundedness": str(float(score.groundedness)),
#             "average": str(float(avg_score))
#         })

#         if avg_score > 0.7:
#             self.nth_issue = 0
#             return

#         self.nth_issue += 1
#         if self.nth_issue >= 2:
#             self.escalated_to_live_agent = True
#             await self.session.interrupt()
#             await self.session.say("Let me transfer you to live agent", allow_interruptions=False)
#             await self.transfer_call_voice()

#     async def transfer_call_voice(self):
#         logger.info("transfer_call_voice function called...")
#         try:
#             async with api.LiveKitAPI() as livekit_api:
#                 asterisk_ip = os.getenv("ASTERISK_SERVER_IP")
#                 transfer_to = f"sip:5000@{str(asterisk_ip)}"
#                 # transfer_to = "sip:5000@139.64.158.216"
#                 participant_identity = list(self.room.remote_participants.values())[0].identity
#                 # Create transfer request
#                 transfer_request = TransferSIPParticipantRequest(
#                     participant_identity=participant_identity,
#                     room_name=self.room.name,
#                     transfer_to=transfer_to,
#                     play_dialtone=False,
#                     # wait_until_answered=True,
#                 )

#                 # Transfer caller
#                 await livekit_api.sip.transfer_sip_participant(transfer_request)
#         except Exception as e:
#             logger.error(f"Error during call transfer: {e}")
#             return "Issue with call transfer"


#     async def _on_close(self, _: CloseEvent):
#         await self.stop()


import os
import json
import asyncio
from decimal import Decimal
from logging_config import get_logger

# Initialize logger
logger = get_logger('supervisor')
from pydantic import BaseModel, Field
from livekit import api
from livekit.protocol.sip import TransferSIPParticipantRequest
from livekit.agents.llm import ChatContext, ChatMessage
from livekit.plugins import openai
from livekit.agents import (
    AgentSession,
    ConversationItemAddedEvent,
    CloseEvent,
    metrics,
    MetricsCollectedEvent
)


class SupervisorScore(BaseModel):
    """Supervisor scores"""
    relevance: Decimal = Field(ge=0, le=1, description="Relevance score 0 to 1")
    completeness: Decimal = Field(ge=0, le=1, description="Completeness score 0 to 1")
    groundedness: Decimal = Field(ge=0, le=1, description="Groundedness score 0 to 1")
    repetition_detected: bool = Field(description="Flag indicating if repetition is detected")


class Supervisor:
    def __init__(self,
                 session: AgentSession,
                 room,
                 llm = None,
                 history_window: int = 6,
                 min_turns_for_repetition: int = 6,
                 repetition_threshold: int = 2) -> None:
        self.session = session
        self.llm = llm if llm else openai.LLM(model="gpt-4o-mini")
        self.room = room

        # Configuration
        self.history_window = history_window
        self.min_turns_for_repetition = min_turns_for_repetition
        self.repetition_threshold = repetition_threshold
        
        # State tracking
        self.first_greeting_done = False
        self.escalated_to_live_agent = False
        self.nth_issue = 0
        self.repetition_count = 0
        self.score_history = []
        self.restricted_history = []
        self.repetition_flag = False
        self.transfer_reason = ""
        self.status_messages = []
        self.last_bot_responses = []  # Track recent bot responses
        self.off_topic_count = 0  # Track off-topic requests

    async def start(self):
        def on_close_wrapper(ev):
            asyncio.create_task(self._on_close(ev))

        self.session.on("conversation_item_added")(self._on_added)
        self.session.on("close")(on_close_wrapper)

        self.usage_collector = metrics.UsageCollector()
        @self.llm.on("metrics_collected")
        def on_metrics_collected(ev: MetricsCollectedEvent):
            self.usage_collector.collect(ev)

    def extract_text(self, item) -> str:
        """Extract text content from conversation item."""
        if hasattr(item, 'content'):
            if isinstance(item.content, str):
                return item.content
            elif isinstance(item.content, list):
                return ' '.join(str(c) for c in item.content if c)
        return ""

    def _is_status_message(self, text: str) -> bool:
        """Detect if a message is a status/wait message."""
        status_indicators = [
            "please wait", "moment", "checking", "looking", "fetching",
            "getting", "retrieving", "let me", "one second", "just a moment"
        ]
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in status_indicators)

    def _is_off_topic_request(self, text: str) -> bool:
        """Detect if user is asking about off-topic topics."""
        off_topic_keywords = [
            "eat", "food", "burger", "pizza", "restaurant", "dining",
            "movie", "film", "show", "entertainment", "game",
            "medicine", "pill", "drug", "pharmacy", "pfizer"
        ]
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in off_topic_keywords)

    def _update_restricted_history(self, role: str, text: str):
        """Maintain a rolling window of conversation history."""
        
        # Track status messages separately
        if role == "assistant" and self._is_status_message(text):
            self.status_messages.append(text)
            logger.debug(f"Detected status message: {text[:50]}...")
        
        # Track off-topic requests
        if role == "user" and self._is_off_topic_request(text):
            self.off_topic_count += 1
            logger.debug(f"Off-topic request detected (count: {self.off_topic_count}): {text[:50]}...")
        
        # Track bot responses for semantic similarity
        if role == "assistant":
            self.last_bot_responses.append(text)
            if len(self.last_bot_responses) > 2:
                self.last_bot_responses.pop(0)
        
        # Add each message as a separate turn (no merging)
        self.restricted_history.append({"role": role, "text": text})
        
        # Keep only the last N exchanges
        if len(self.restricted_history) > self.history_window:
            self.restricted_history = self.restricted_history[-self.history_window:]

    def _format_history_for_prompt(self) -> str:
        """Format restricted history for inclusion in prompt."""
        if not self.restricted_history:
            return "No previous conversation history."
        
        formatted = []
        for i, turn in enumerate(self.restricted_history, 1):
            formatted.append(f"{i}. {turn['role'].upper()}: {turn['text']}")
        
        return "\n".join(formatted)

    def _check_semantic_repetition(self) -> bool:
        """Check if bot responses are semantically repetitive."""
        if len(self.last_bot_responses) < 2:
            return False
            
        # Simple heuristic: check if responses contain similar key phrases
        key_phrases = [
            "help with your ride", "trip service", "booking rides", 
            "assist you with", "tam transit", "how can i help"
        ]
        
        matches = 0
        for response in self.last_bot_responses:
            response_lower = response.lower()
            if any(phrase in response_lower for phrase in key_phrases):
                matches += 1
                
        # If all 2 recent responses contain key phrases, consider it repetitive
        return matches >= 2

    def _on_added(self, ev: ConversationItemAddedEvent):
        if self.escalated_to_live_agent:
            return
            
        if self.first_greeting_done is False and ev.item.role == "assistant":
            self.first_greeting_done = True
            return

        item_text = self.extract_text(ev.item)
        
        if ev.item.role == "user":
            self._update_restricted_history("user", item_text)

        if ev.item.role == "assistant":
            self._update_restricted_history("assistant", item_text)
            asyncio.create_task(self._score_response_and_act())

    async def _score_response_and_act(self):
        """Score the response and check for transfer conditions."""
        
        if len(self.restricted_history) < 2:
            return
        
        check_repetition = len(self.restricted_history) >= self.min_turns_for_repetition
        
        last_bot = self.restricted_history[-1]["text"] if self.restricted_history[-1]["role"] == "assistant" else ""
        last_user = self.restricted_history[-2]["text"] if len(self.restricted_history) >= 2 and self.restricted_history[-2]["role"] == "user" else ""
        
        # DIRECT REPETITION CHECK: If bot gives identical response 2+ times, escalate immediately
        if len(self.restricted_history) >= 4:
            bot_messages = [turn["text"] for turn in self.restricted_history if turn["role"] == "assistant"]
            if len(bot_messages) >= 2:
                last_two = bot_messages[-2:]
                if last_two[0] == last_two[1]:
                    logger.warning(f"[DIRECT REPETITION] Bot repeated identical message 2 times: '{last_two[0][:50]}...'")
                    self.transfer_reason = "Bot stuck in loop - giving identical responses repeatedly"
                    await self._escalate_with_reason(self.transfer_reason)
                    return
        
        # OFF-TOPIC LOOP CHECK: If user asks about off-topic topics 2+ times
        if self.off_topic_count >= 2:
            logger.warning(f"[OFF-TOPIC LOOP] User asked about off-topic topics {self.off_topic_count} times")
            self.transfer_reason = f"User repeatedly asking about off-topic topics ({self.off_topic_count} times) - transferring to live agent"
            await self._escalate_with_reason(self.transfer_reason)
            return
        
        # SEMANTIC REPETITION CHECK: If bot gives semantically similar responses
        if self._check_semantic_repetition():
            logger.warning(f"[SEMANTIC REPETITION] Bot giving semantically similar responses")
            self.transfer_reason = "Bot stuck in conversational loop - giving similar responses repeatedly"
            await self._escalate_with_reason(self.transfer_reason)
            return
        
        history_context = self._format_history_for_prompt()
        
        if check_repetition:
            repetition_task = """
            TASK 2 - Detect Repetition:
            Analyze the RESTRICTED HISTORY above. Set "repetition_detected" to TRUE if you see evidence of:

            1. **User repeating the SAME substantive request** 2+ times without resolution (e.g., "I need a ride" → bot responds → "I need a ride" again → bot responds → "I need a ride" AGAIN)
            2. **Bot giving IDENTICAL unhelpful responses** to different user attempts (stuck in a loop)
            3. **User explicitly complaining** about repetition: "you keep saying the same thing", "we already discussed this", "stop repeating yourself"
            4. **Zero progress** over 2+ complete exchanges on the same unresolved topic
            5. **User repeatedly asking about off-topic topics** (e.g., food, movies, etc.) that the bot cannot help with, and the bot redirecting each time without the user moving on to a relevant topic (at least 2 instances)
            6. **Conversational loop** where the same pattern (e.g., user asks about X → bot responds with Y → user asks about X again in a different way) repeats 2+ times without progress.

            DO NOT flag as repetition:
            - Normal clarifications or follow-ups (e.g., "can you tell me?" after "please wait")
            - User confirming or acknowledging bot responses ("yes", "okay", "thanks")
            - Bot status messages followed by actual answers ("please wait" → then provides answer)
            - Different phrasings of related questions as conversation naturally evolves
            - Early-stage conversations still gathering information

            If you observe any of the conditions 1-6, set "repetition_detected" to TRUE. Otherwise, set to FALSE.
            """
        else:
            repetition_task = f"""
            TASK 2 - Detect Repetition:
            NOT ENOUGH CONVERSATION HISTORY YET (less than {self.min_turns_for_repetition} turns). Set "repetition_detected" to FALSE.
            Repetition cannot be reliably detected without sufficient conversation history.
            """
        
        prompt = f"""You are a supervisor scoring a chatbot's response. Return ONLY valid JSON, no other text.

            CONVERSATION HISTORY (last {self.history_window} turns):
            {history_context}

            CURRENT EXCHANGE:
            User: {last_user}
            Bot: {last_bot}

            SCORING (0.00 to 1.00, two decimals):
            1. Relevance: Does bot address user's request or ask focused clarifying question?
            2. Completeness: Does bot provide sufficient info or clear next steps?
            3. Groundedness: Are statements factual/supported, not making unsupported claims?

            SPECIAL CASES:
            - If user asks off-topic questions (movies, food, etc.) and bot redirects to its domain, score relevance=0.80, completeness=0.70
            - If bot gives identical response 2+ times in a row, lower all scores by 0.3

            {repetition_task}

            CRITICAL: You MUST return valid JSON. Default to mid-range scores (0.50) if uncertain.

            Return ONLY this JSON (no markdown, no extra text):
            {{"relevance": 0.xx, "completeness": 0.xx, "groundedness": 0.xx, "repetition_detected": false}}"""

        chat_ctx = ChatContext([ChatMessage(role="system", content=[prompt])])

        result = ""
        async with self.llm.chat(chat_ctx=chat_ctx) as stream:
            async for chunk in stream:
                d = getattr(chunk, "delta", None)
                if d and d.content:
                    result += d.content

        try:
            result_cleaned = result.strip()
            if "```json" in result_cleaned:
                result_cleaned = result_cleaned.split("```json")[1].split("```")[0].strip()
            elif "```" in result_cleaned:
                result_cleaned = result_cleaned.split("```")[1].split("```")[0].strip()
            
            score = SupervisorScore.model_validate(json.loads(result_cleaned))
            
            if not check_repetition:
                score.repetition_detected = False
                logger.debug(f"Forced repetition_detected to False (insufficient history: {len(self.restricted_history)} turns, need {self.min_turns_for_repetition})")
                
        except Exception as e:
            logger.debug(f"[supervisor llm response] {result}")
            logger.error(f"[supervisor score parse error] {e}")
            
            if len(self.restricted_history) >= 4:
                recent_bot_messages = [turn["text"] for turn in self.restricted_history if turn["role"] == "assistant"]
                if len(recent_bot_messages) >= 2 and recent_bot_messages[-1] == recent_bot_messages[-2]:
                    logger.warning("[FALLBACK] Detected identical bot responses - using fallback low scores")
                    score = SupervisorScore(
                        relevance=Decimal("0.30"),
                        completeness=Decimal("0.30"),
                        groundedness=Decimal("0.50"),
                        repetition_detected=check_repetition
                    )
                else:
                    return
            else:
                return

        avg_score = (score.relevance + score.completeness + score.groundedness) / 3
        
        if float(avg_score) == 0.0 and float(score.relevance) == 0.0 and float(score.completeness) == 0.0:
            logger.warning(f"All scores returned as 0.0 - likely LLM parsing error. Skipping this evaluation.")
            logger.debug(f"LLM raw response was: {result[:200]}")
            return
        
        logger.info(f"[supervisor score] Relevance: {score.relevance}, Completeness: {score.completeness}, Groundedness: {score.groundedness}, Average: {avg_score}")
        logger.info(f"[repetition flag] {score.repetition_detected} (history turns: {len(self.restricted_history)}, check_enabled: {check_repetition}, threshold: {self.min_turns_for_repetition})")

        self.score_history.append({
            "relevance": str(float(score.relevance)),
            "completeness": str(float(score.completeness)),
            "groundedness": str(float(score.groundedness)),
            "average": str(float(avg_score)),
            "repetition_detected": score.repetition_detected
        })

        # Check for transfer conditions
        
        # Condition 1: Repetition detected - INCREMENT COUNTER
        if score.repetition_detected:
            self.repetition_count += 1
            logger.info(f"[REPETITION COUNTER] Repetition #{self.repetition_count} detected (threshold: {self.repetition_threshold})")
            
            if self.repetition_count >= self.repetition_threshold:
                self.transfer_reason = f"Conversation repetition detected {self.repetition_count} times - transferring to live agent for better assistance"
                await self._escalate_with_reason(self.transfer_reason)
                return
            else:
                logger.info(f"[REPETITION COUNTER] Not transferring yet - need {self.repetition_threshold - self.repetition_count} more repetition(s)")
                return
        else:
            # Reset repetition counter if no repetition detected
            if self.repetition_count > 0:
                logger.info(f"[REPETITION COUNTER] Reset to 0 (was {self.repetition_count})")
            self.repetition_count = 0

        # Condition 2: Good score - reset issue counter
        if avg_score > 0.7:
            self.nth_issue = 0
            return

        # Condition 3: Consecutive low scores
        self.nth_issue += 1
        if self.nth_issue >= 3:
            self.transfer_reason = f"Bot unable to assist effectively ({self.nth_issue} consecutive low-quality responses)"
            await self._escalate_with_reason(self.transfer_reason)

    async def _escalate_with_reason(self, reason: str):
        """Escalate to live agent with clear reason."""
        if self.escalated_to_live_agent:
            return
        
        self.escalated_to_live_agent = True
        self.transfer_reason = reason
        
        logger.info(f"[ESCALATION TRIGGERED] Reason: {reason}")
        logger.info(f"[Conversation History at Transfer]:\n{self._format_history_for_prompt()}")
        
        await self.session.interrupt()
        await self.session.say(
            "I notice we might be going in circles. Let me transfer you to a live agent who can better assist you.",
            allow_interruptions=False
        )
        await self.transfer_call_voice()

    async def transfer_call_voice(self):
        logger.info("transfer_call_voice function called...")
        logger.info(f"Transfer Reason: {self.transfer_reason}")
        
        try:
            async with api.LiveKitAPI() as livekit_api:
                asterisk_ip = os.getenv("ASTERISK_SERVER_IP")
                transfer_to = f"sip:5000@{str(asterisk_ip)}"
                participant_identity = list(self.room.remote_participants.values())[0].identity
                
                transfer_request = TransferSIPParticipantRequest(
                    participant_identity=participant_identity,
                    room_name=self.room.name,
                    transfer_to=transfer_to,
                    play_dialtone=False,
                )

                await livekit_api.sip.transfer_sip_participant(transfer_request)
                logger.info(f"Call transferred successfully. Reason: {self.transfer_reason}")
                
        except Exception as e:
            logger.error(f"Error during call transfer: {e}")
            return "Issue with call transfer"

    async def _on_close(self, _: CloseEvent):
        await self.stop()

    async def stop(self):
        """Cleanup method for supervisor shutdown."""
        logger.info("Supervisor stopping...")
        
        if self.transfer_reason:
            logger.info(f"Session ended with transfer. Reason: {self.transfer_reason}")
        
        logger.info(f"Total responses scored: {len(self.score_history)}")
        if self.score_history:
            avg_scores = {
                "relevance": sum(float(s["relevance"]) for s in self.score_history) / len(self.score_history),
                "completeness": sum(float(s["completeness"]) for s in self.score_history) / len(self.score_history),
                "groundedness": sum(float(s["groundedness"]) for s in self.score_history) / len(self.score_history),
            }
            logger.info(f"Average scores - Relevance: {avg_scores['relevance']:.2f}, Completeness: {avg_scores['completeness']:.2f}, Groundedness: {avg_scores['groundedness']:.2f}")