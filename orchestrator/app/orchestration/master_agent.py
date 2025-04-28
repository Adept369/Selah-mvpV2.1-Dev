# orchestrator/app/orchestration/master_agent.py

import logging
from typing import Tuple

from app.orchestration.registry import build_registry

logger = logging.getLogger(__name__)

class MasterAgent:
    def __init__(self, llm_client):
        self.llm = llm_client
        self.registry = build_registry(llm_client)

    def classify_intent(self, text: str) -> str:
        """
        Decide which specialized agent should handle this text.
        If no rule matches, return 'generic'.
        """
        lower = text.lower()
        if any(k in lower for k in ["sovereignty", "case", "statute", "law", "precedent"]):
            return "case_law_scholar"
        # you can add more special‐case rules here...
        return "generic"

    def parse(self, text: str) -> Tuple[str, str]:
        """Returns (agent_key, query_text)."""
        return self.classify_intent(text), text

    async def run(self, update: dict) -> str:
        msg = update.get("message", {})
        text = msg.get("text", "").strip()
        if not text:
            return "🤖 Please send me some text to work with."

        agent_key, query = self.parse(text)
        logger.info("MasterAgent: routing to '%s' for %r", agent_key, query)

        if agent_key in self.registry:
            # use your specialized agent
            agent = self.registry[agent_key]
            result = agent.run(query)
            if hasattr(result, "__await__"):
                result = await result

        else:
            # generic LLM fallback
            prompt = f"Answer this question as concisely and authoritatively as you can:\n\n{query}"
            try:
                result = self.llm.generate(prompt, max_tokens=500)
            except Exception as e:
                logger.exception("LLM fallback failed")
                return "⚠️ Sorry, I wasn’t able to fetch an answer."

        # for legal queries, we still prepend a one-liner summary
        if agent_key == "case_law_scholar" and result:
            summary_prompt = (
                "In a single witty sentence, summarize this legal explanation for Telegram:\n\n"
                f"{result}\n"
            )
            try:
                summary = self.llm.generate(summary_prompt, max_tokens=60)
            except Exception:
                summary = None

            if summary:
                return f"🕵️ {summary.strip()}\n\n{result}"

        return result