import os
import json
import asyncio

from decimal import Decimal
from pydantic import BaseModel, Field
from livekit import api
from livekit.protocol.sip import TransferSIPParticipantRequest
from livekit.agents.llm import ChatContext, ChatMessage
from livekit.plugins import openai
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from livekit.agents import (
    AgentSession, ConversationItemAddedEvent, CloseEvent
)

class SupervisorScore(BaseModel):
    """Supervisor scores"""
    relevance: Decimal = Field(ge=0, le=1, description="Relevance score 0 to 1")
    completeness: Decimal = Field(ge=0, le=1, description="Completeness score 0 to 1")
    groundedness: Decimal = Field(ge=0, le=1, description="Groundedness score 0 to 1")


class Supervisor:
    def __init__(self,
                 session: AgentSession,
                 room,
                 llm = None) -> None:
        self.session = session
        self.llm = llm if llm else openai.LLM(model="gpt-4o-mini")
        self.room = room

        self.first_greeting_done = False
        self.escalated_to_live_agent = False
        self.nth_issue = 0

    async def start(self):
        # Create a synchronous wrapper for the close event since it's async
        def on_close_wrapper(ev):
            asyncio.create_task(self._on_close(ev))

        # Wire event handlers (class-bound methods)
        self.session.on("conversation_item_added")(self._on_added)
        self.session.on("close")(on_close_wrapper)

    def _on_added(self, ev: ConversationItemAddedEvent):
        if self.escalated_to_live_agent:
            return
        if self.first_greeting_done is False and ev.item.role == "assistant":
            self.first_greeting_done = True
            return

        if ev.item.role == "assistant":
            asyncio.create_task(self._score_response_and_act())

    async def _score_response_and_act(self):
        prompt = """You are a deterministic supervisor that scores one bot reply against one user message.
Return only a compact JSON with three numbers: "relevance", "completeness", "groundedness".

Inputs (in the user message):
- "user_text": the user's utterance for this turn.
- "bot_text": the bot's reply for this turn.

Scoring (0-1, two decimals; any value in this range is allowed):
- Relevance: how directly the reply addresses the user's intent or asks a focused clarifying question that advances it.
- Completeness: whether the reply covers the necessary elements for this step or gives a clear next action; major omissions → lower score.
- Groundedness: whether statements are supported by provided context or make no external claims; unsupported/conflicting claims → lower score.

Frustration handling:
- If the user appears frustrated (e.g., complaints, “you're not listening,” repeated re-asks) and the bot fails to address or fix the issue in this turn, assign **lower values** to the scores to reflect the poor experience.

Output format — output ONLY this JSON (no extra text/keys):
{"relevance": x.xx, "completeness": x.xx, "groundedness": x.xx}

If uncertain, choose the lower score."""

        chat_ctx = ChatContext([ChatMessage(role="system", content=[prompt]),
                                *self.session._chat_ctx.items[-6:]])

        result = ""
        async with self.llm.chat(chat_ctx=chat_ctx) as stream:
            async for chunk in stream:
                d = getattr(chunk, "delta", None)
                if d and d.content:
                    result += d.content

        try:
            score = SupervisorScore.model_validate(json.loads(result))
            print(f"[checkthis score] {score}")
        except Exception as e:
            print(f"[checkthis llm response] {result}")
            print(f"[checkthis score parse error] {e}")
            return

        avg_score = (score.relevance + score.completeness + score.groundedness) / 3

        if avg_score > 0.7:
            self.nth_issue = 0
            return

        self.nth_issue += 1
        if self.nth_issue >= 1:
            self.escalated_to_live_agent = True
            await self.session.interrupt()
            await self.session.say("Let me transfer you to live agent", allow_interruptions=False)
            await self.transfer_call_voice()

    async def transfer_call_voice(self):
        print("transfer_call_voice function called...")
        try:
            async with api.LiveKitAPI() as livekit_api:
                asterisk_ip = os.getenv("ASTERISK_SERVER_IP")
                transfer_to = f"sip:5000@{str(asterisk_ip)}"
                # transfer_to = "sip:5000@139.64.158.216"
                participant_identity = list(self.room.remote_participants.values())[0].identity
                # Create transfer request
                transfer_request = TransferSIPParticipantRequest(
                    participant_identity=participant_identity,
                    room_name=self.room.name,
                    transfer_to=transfer_to,
                    play_dialtone=False,
                    # wait_until_answered=True,
                )

                # Transfer caller
                await livekit_api.sip.transfer_sip_participant(transfer_request)
        except Exception as e:
            print(f"Error during call transfer: {e}")
            return "Issue with call transfer"


    async def _on_close(self, _: CloseEvent):
        await self.stop()
