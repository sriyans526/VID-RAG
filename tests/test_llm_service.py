import sys, types
import pytest

fake_module = types.ModuleType("langchain_openai")
fake_module.ChatOpenAI = lambda **kwargs: None
sys.modules.setdefault("langchain_openai", fake_module)

from service import LLM_service


def test_ollama_cloud_uses_native_api_with_reasoning_disabled(monkeypatch):
    import sys
    import types
    received = {}

    fake_module = types.ModuleType("langchain_openai")
    class FakeChatOpenAI:
        def __init__(self, **kwargs):
            received.update(kwargs)
    fake_module.ChatOpenAI = FakeChatOpenAI
    monkeypatch.setitem(sys.modules, "langchain_openai", fake_module)

    monkeypatch.setenv("LLM_PROVIDER", "ollama_cloud")
    monkeypatch.setenv("OLLAMA_API_KEY", "test-key")
    monkeypatch.setenv("OLLAMA_CLOUD_BASE_URL", "https://ollama.com/v1")
    monkeypatch.setenv("OLLAMA_CLOUD_MODEL", "nemotron-3-nano:30b-cloud")
    LLM_service.LLMService.get_llm.cache_clear()

    try:
        LLM_service.LLMService.get_llm()
    finally:
        LLM_service.LLMService.get_llm.cache_clear()

    assert received == {
        "model": "nemotron-3-nano:30b-cloud",
        "api_key": "test-key",
        "base_url": "https://ollama.com/v1",
        "temperature": 0.1,
        "max_tokens": 1024,
        "timeout": 120,
        "max_retries": 2,
    }


def test_ollama_cloud_requires_api_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama_cloud")
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    LLM_service.LLMService.get_llm.cache_clear()

    try:
        with pytest.raises(RuntimeError, match="OLLAMA_API_KEY"):
            LLM_service.LLMService.get_llm()
    finally:
        LLM_service.LLMService.get_llm.cache_clear()


def test_unknown_provider_is_not_silently_treated_as_gemini(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama_cloud_typo")
    LLM_service.LLMService.get_llm.cache_clear()

    try:
        with pytest.raises(ValueError, match="Unsupported LLM_PROVIDER"):
            LLM_service.LLMService.get_llm()
    finally:
        LLM_service.LLMService.get_llm.cache_clear()
