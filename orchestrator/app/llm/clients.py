# orchestrator/app/llm/clients.py

import os
import logging
from time import perf_counter
from typing import Optional, Union, Sequence

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

    def generate(
        self,
        prompt: str,
        *,
        context: Optional[Union[str, Sequence[str]]] = None,
        **kwargs
    ) -> str:
        """
        Generate a completion for the given prompt.

        If `context` is provided as a string or list of strings, it is prepended to the prompt
        (joined with two newlines) to give the model conversational memory.

        Logs backend, duration, full prompt, kwargs, and a truncated response.
        """
        # 1) Build the full prompt
        if context:
            if isinstance(context, str):
                context_block = context.strip()
            else:
                # list of lines → join with double newlines
                context_block = "\n\n".join(line.strip() for line in context)
            full_prompt = f"{context_block}\n\n{prompt}"
        else:
            full_prompt = prompt

        logger.info(
            "LLMClient.generate start: backend=%r prompt=%r kwargs=%s",
            self.backend, full_prompt, kwargs
        )
        start = perf_counter()

        # 2) Call out to the correct backend
        if self.backend == "openai":
            model = kwargs.pop("model", "gpt-3.5-turbo")
            resp = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": full_prompt}],
                **kwargs
            )
            result = resp.choices[0].message.content

        elif self.backend == "llama":
            out = self.client(full_prompt, **kwargs)
            result = out[0].get("generated_text", "")

        else:
            # Should never happen
            raise RuntimeError(f"Unsupported backend {self.backend!r}")

        # 3) Log elapsed time and a truncated preview of the output
        duration = perf_counter() - start
        display = result if len(result) < 200 else result[:200] + "...(truncated)"
        logger.info(
            "LLMClient.generate completed in %.3fs, response=%r",
            duration,
            display
        )
        return result
