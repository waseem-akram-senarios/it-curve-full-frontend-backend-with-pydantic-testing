from dotenv import load_dotenv

import json
import asyncio
from decimal import Decimal
from pydantic import BaseModel, Field
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
                 llm = None) -> None:
        self.session = session
        self.llm = llm if llm else openai.LLM(model="gpt-4o-mini")

        self.first_greeting_done = False
        self.escalated_to_live_agent = False

    async def start(self):
        # Create a synchronous wrapper for the close event since it's async
        def on_close_wrapper(ev):
            asyncio.create_task(self._on_close(ev))

        # Wire event handlers (class-bound methods)
        self.session.on("conversation_item_added")(self._on_added)
        self.session.on("close")(on_close_wrapper)

    def _on_added(self, ev: ConversationItemAddedEvent):
        print(f"[checkthis added] '{ev}'")
        if self.first_greeting_done is False and ev.item.role == "assistant":
            self.first_greeting_done = True
            return
        if self.escalated_to_live_agent:
            return

        if ev.item.role == "assistant":
            asyncio.create_task(self._score_response_and_act())

    async def _score_response_and_act(self):
        prompt = """You are a deterministic supervisor that scores one bot reply against one user message.
Return only a compact JSON with three numbers: "relevance", "completeness", "groundedness".

Inputs (in the user message):
- "user_text": the user's utterance for this turn.
- "bot_text": the bot's reply for this turn.

Scoring (0-1, two decimals; prefer {1.00, 0.50, 0.00}):
- Relevance: how directly the reply addresses the user's intent or asks a focused clarifying question that advances it.
- Completeness: whether the reply covers the necessary elements for this step or gives a clear next action; major omissions → lower score.
- Groundedness: whether statements are supported by provided "facts" or make no external claims; unsupported/conflicting claims → lower score.

Output format — output ONLY this JSON (no extra text/keys):
{"relevance": x.xx, "completeness": x.xx, "groundedness": x.xx}

If uncertain, choose the lower score."""

        chat_ctx = ChatContext([ChatMessage(role="system", content=[prompt]),
                                self.session._chat_ctx.items[-2],
                                self.session._chat_ctx.items[-1]])

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
        
        if avg_score < 0.5:
            self.escalated_to_live_agent = True
            await self.session.interrupt()
            await self.session.say("Let me transfer you to live agent", allow_interruptions=False)


    async def _on_close(self, _: CloseEvent):
        await self.stop()
