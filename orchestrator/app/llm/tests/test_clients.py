# app/llm/tests/test_clients.py

import pytest
import sys
import types
import logging
from app.llm.clients import LLMClient

class DummySettings:
    # neither "openai" nor "llama"
    LLM_BACKEND = "not_a_real_backend"
    OPENAI_API_KEY = None
    LLAMA_MODEL_PATH = None

def test_unknown_backend_raises_value_error():
    with pytest.raises(ValueError) as exc:
        LLMClient(DummySettings())
    assert "Unknown LLM_BACKEND" in str(exc.value)

# --- Helpers to stub out backends ------------------------------------------

class DummyOpenAI:
    def __init__(self, api_key):
        # simulate openai.OpenAI.chat.completions.create(...)
        self.chat = types.SimpleNamespace(
            completions=types.SimpleNamespace(
                create=lambda *, model, messages, **kwargs: types.SimpleNamespace(
                    choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="openai-response"))]
                )
            )
        )
        self.last_call = {}

    def _wrap_create(self, **kwargs):
        # record arguments for inspection
        self.last_call = kwargs
        return self.chat.completions.create(**kwargs)

def make_dummy_openai_module():
    mod = types.ModuleType("openai")
    mod.OpenAI = DummyOpenAI
    return mod

def make_dummy_transformers_module():
    # Simulate transformers.pipeline returning a callable
    def pipeline(task, model, device):
        def gen(prompt, **kwargs):
            gen.last = {"prompt": prompt, "kwargs": kwargs}
            return [{"generated_text": "llama-response"}]
        return gen

    mod = types.ModuleType("transformers")
    mod.pipeline = pipeline
    return mod

# --- Existing tests --------------------------------------------------------

def test_openai_generate_logs(caplog, monkeypatch):
    # stub out openai module
    monkeypatch.setitem(sys.modules, "openai", make_dummy_openai_module())
    settings = types.SimpleNamespace(LLM_BACKEND="openai", OPENAI_API_KEY="key123")
    client = LLMClient(settings)

    caplog.set_level(logging.INFO)
    resp = client.generate("hello world", max_tokens=10)

    assert resp == "openai-response"
    assert any("LLMClient.generate start" in rec.getMessage() for rec in caplog.records)
    assert any("LLMClient.generate completed" in rec.getMessage() for rec in caplog.records)

def test_llama_generate_logs(caplog, monkeypatch):
    monkeypatch.setitem(sys.modules, "transformers", make_dummy_transformers_module())
    settings = types.SimpleNamespace(LLM_BACKEND="llama", LLAMA_MODEL_PATH="some/path")
    client = LLMClient(settings)

    caplog.set_level(logging.INFO)
    resp = client.generate("foo bar", top_k=5)

    assert resp == "llama-response"
    assert any("LLMClient.generate start" in rec.getMessage() for rec in caplog.records)
    assert any("LLMClient.generate completed" in rec.getMessage() for rec in caplog.records)

# --- New tests for `context` parameter ------------------------------------

def test_generate_with_string_context(monkeypatch):
    # stub out openai
    monkeypatch.setitem(sys.modules, "openai", make_dummy_openai_module())
    settings = types.SimpleNamespace(LLM_BACKEND="openai", OPENAI_API_KEY="key123")
    client = LLMClient(settings)
    # replace client.client with dummy instance to capture calls
    dummy = client.client
    # wrap create so we can inspect
    dummy.chat.completions.create = types.MethodType(lambda self, *, model, messages, **kwargs: dummy.last_call.update({
        "model": model, "messages": messages, "kwargs": kwargs
    }) or types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="ok"))]), dummy)

    out = client.generate("What’s your name?", context="USER: Hi\nBOT: Hello", max_tokens=5)
    assert out == "ok"
    expected = "USER: Hi\nBOT: Hello\n\nWhat’s your name?"
    assert dummy.last_call["messages"] == [{"role": "user", "content": expected}]

def test_generate_with_list_context(monkeypatch):
    monkeypatch.setitem(sys.modules, "openai", make_dummy_openai_module())
    settings = types.SimpleNamespace(LLM_BACKEND="openai", OPENAI_API_KEY="key123")
    client = LLMClient(settings)
    dummy = client.client
    dummy.chat.completions.create = types.MethodType(lambda self, *, model, messages, **kwargs: dummy.last_call.update({
        "model": model, "messages": messages, "kwargs": kwargs
    }) or types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="ok"))]), dummy)

    history = ["USER: A", "BOT: B", "USER: C"]
    out = client.generate("Next?", context=history, max_tokens=5)
    assert out == "ok"
    joined = "USER: A\n\nBOT: B\n\nUSER: C"
    expected = f"{joined}\n\nNext?"
    assert dummy.last_call["messages"] == [{"role": "user", "content": expected}]

def test_generate_without_context(monkeypatch):
    monkeypatch.setitem(sys.modules, "openai", make_dummy_openai_module())
    settings = types.SimpleNamespace(LLM_BACKEND="openai", OPENAI_API_KEY="key123")
    client = LLMClient(settings)
    dummy = client.client
    dummy.chat.completions.create = types.MethodType(lambda self, *, model, messages, **kwargs: dummy.last_call.update({
        "model": model, "messages": messages, "kwargs": kwargs
    }) or types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="ok"))]), dummy)

    out = client.generate("No context here", max_tokens=5)
    assert out == "ok"
    assert dummy.last_call["messages"] == [{"role": "user", "content": "No context here"}]
