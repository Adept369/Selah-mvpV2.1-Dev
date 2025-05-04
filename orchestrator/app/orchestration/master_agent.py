# orchestrator/app/orchestration/master_agent.py

import logging
from typing import List, Tuple

from app.agents.memory.buffer_memory import BufferMemory
from app.core.config import settings
from app.orchestration.registry import build_registry

logger = logging.getLogger(__name__)

class MasterAgent:
    MEM_SIZE = 21  # keep last 21 turns

    def __init__(self, llm_client):
        self.llm      = llm_client
        self.registry = build_registry(llm_client)
        # our in-process async buffer memory backed by Redis
        self.memory   = BufferMemory()
        # load our new system prompt
        self.system_prompt = settings.MASTER_PROMPT

    def classify_intent(self, text: str) -> str:
        lower = text.lower()
        if any(k in lower for k in ["sovereignty", "case", "statute", "law", "precedent"]):
            return "case_law_scholar"
        if any(k in lower for k in ["memo", "draft"]):
            return "memo_drafter"
        if "remind" in lower or "schedule" in lower:
            return "n8n_scheduler"
        if any(k in lower for k in ["weather", "help", "how do i", "what is"]):
            return "help"
        return "generic"

    def parse(self, text: str) -> Tuple[str, str]:
        text = text.strip()
        if text.startswith("/"):
            parts = text[1:].split(maxsplit=1)
            cmd   = parts[0]
            query = parts[1] if len(parts) > 1 else ""
            logger.info("MasterAgent: detected slash-command '%s' → %r", cmd, query)
            return cmd, query
        return self.classify_intent(text), text

    async def run(self, update: dict) -> str:
        msg     = update.get("message", {})
        text    = msg.get("text", "").strip()
        chat_id = str(msg.get("chat", {}).get("id"))

        if not text:
            return "🤖 Please send me some text to work with."

        agent_key, query = self.parse(text)
        logger.info("MasterAgent: routing to '%s' for %r", agent_key, query)

        # 1) For generic fallbacks, pull last MEM_SIZE turns
        history: List[str] = []
        if agent_key == "generic":
            history = await self.memory.get_history(chat_id)
            if history:
                logger.debug("Loaded memory for chat %s: %s", chat_id, history)
 
        # 2) Dispatch to a specialized agent
        if agent_key in self.registry:
            agent = self.registry[agent_key]
            try:
                result = agent.run(query)
                if hasattr(result, "__await__"):
                    result = await result
            except Exception:
                logger.exception("Error in agent %s", agent_key)
                return "⚠️ Oops, something went wrong in that agent."
        else:
            # 3) Generic LLM fallback, passing buffer-memory as context
            # Generic LLM fallback: include our master-level system prompt +
            # any recent history as context before the user query.
            full_context = []
            if self.system_prompt:
                full_context.append(self.system_prompt)
            if history:
                full_context.extend(history)

            try:
                result = self.llm.generate(
                  prompt=query,
                    context=full_context or None,
                    max_tokens=5000
                )
            except Exception:
                logger.exception("LLM fallback failed")
                return "⚠️ Sorry, I wasn’t able to fetch an answer."

        # 4) Post-process legal answers with a witty one-liner
        if agent_key == "case_law_scholar" and result:
            try:
                summary = self.llm.generate(
                    prompt=(
                        "In a single witty sentence, summarize this legal explanation for Telegram:\n\n"
                        f"{result}\n"
                    ),
                    max_tokens=60,
                ).strip()
                if summary:
                    result = f"🕵️ {summary}\n\n{result}"
            except Exception:
                logger.exception("Failed to create case-law summary")

        # 5) Save user+assistant into buffer only for generic chats
        if agent_key == "generic":
            try:
                await self.memory.add(chat_id, "user", query)
                await self.memory.add(chat_id, "bot", result)
            except Exception:
                logger.warning("Failed to write memory for chat %s", chat_id)

        return result
