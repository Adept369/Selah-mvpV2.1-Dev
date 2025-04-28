# orchestrator/app/llm/clients.py

import os
import logging
from time import perf_counter

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self, settings):
        # strip out any inline comments or stray whitespace
        raw = settings.LLM_BACKEND.split("#", 1)[0].strip()
        backend = raw.lower()
        if backend == "openai":
            from openai import OpenAI
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
            self.backend = "openai"

        elif backend == "llama":
            from transformers import pipeline
            self.client = pipeline(
                "text-generation",
                model=settings.LLAMA_MODEL_PATH,
                device="cpu"  # switch to "cuda" if you have a GPU
            )
            self.backend = "llama"

        else:
            raise ValueError(f"Unknown LLM_BACKEND: {settings.LLM_BACKEND!r}")

        logger.info("Initialized LLMClient with backend %r", self.backend)

    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate a completion for the given prompt.
        Logs prompt, kwargs, backend, duration and (truncated) response.
        """
        logger.info(
            "LLMClient.generate start: backend=%r prompt=%r kwargs=%s",
            self.backend, prompt, kwargs
        )
        start = perf_counter()

        if self.backend == "openai":
            # Customize model, temperature, max_tokens, etc. via kwargs
            model = kwargs.pop("model", "gpt-3.5-turbo")
            resp = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            )
            result = resp.choices[0].message.content

        elif self.backend == "llama":
            out = self.client(prompt, **kwargs)
            result = out[0].get("generated_text", "")

        else:
            # Should never happen
            raise RuntimeError(f"Unsupported backend {self.backend!r}")

        duration = perf_counter() - start
        # Truncate long responses in the log
        display = result if len(result) < 200 else result[:200] + "...(truncated)"
        logger.info(
            "LLMClient.generate completed in %.3fs, response=%r",
            duration,
            display
        )
        return result