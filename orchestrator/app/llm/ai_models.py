from abc import ABC, abstractmethod
import os

import openai

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None  # LLaMA support is optional


class AIModel(ABC):
    """
    Abstract interface for language model backends.
    """

    @abstractmethod
    async def generate(self, prompt: str) -> str:
        """
        Generate a completion for the given prompt.
        """
        pass


class OpenAIModel(AIModel):
    """
    OpenAI ChatCompletion backend.
    """

    def __init__(self,
                 api_key: str = None,
                 model_name: str = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        openai.api_key = self.api_key
        self.model_name = model_name or os.environ.get("OPENAI_MODEL_NAME", "gpt-4.1-mini")

    async def generate(self, prompt: str) -> str:
        resp = await openai.ChatCompletion.acreate(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content


class LlamaModel(AIModel):
    """
    Local LLaMA backend via llama_cpp (if installed), otherwise a stub.
    """

    def __init__(self, model_path: str = None):
        self.model_path = model_path or os.environ.get("LLAMA_MODEL_PATH")
        if Llama and self.model_path:
            self.client = Llama(model_path=self.model_path)
        else:
            self.client = None

    async def generate(self, prompt: str) -> str:
        if self.client:
            # llama_cpp is synchronous; run in thread
            import asyncio
            result = await asyncio.to_thread(self.client.create_completion, prompt=prompt)
            return result["choices"][0]["text"]
        # fallback stub
        return f"[LLaMA stub] {prompt}"


def get_llm_model() -> AIModel:
    """
    Factory to return the configured LLM backend instance.
    """
    backend = os.environ.get("LLM_BACKEND", "openai").lower()
    if backend == "openai":
        return OpenAIModel()
    if backend == "llama":
        return LlamaModel()
    raise ValueError(f"Unknown LLM_BACKEND: {backend}")
