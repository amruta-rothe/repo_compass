"""
Unit tests for the Ollama analysis speed-up work.

Covers:
  - the /api/generate payload disables thinking and keeps the model warm
  - num_predict is capped and format/system are forwarded only when set
  - the availability probe is memoised so a page render makes one HTTP call
"""
from app.core.config import get_settings

import app.services.llm_service as llm


def test_payload_disables_thinking_and_keeps_model_warm():
    payload = llm._build_payload("hi", None, 0.2, 250, stream=False)
    settings = get_settings()

    # Thinking is what starves the JSON output budget on qwen3-family models.
    if settings.ollama_disable_thinking:
        assert payload["think"] is False
    else:
        assert "think" not in payload

    # Model must stay resident to avoid cold reloads between calls.
    assert payload["keep_alive"] == settings.ollama_keep_alive

    assert payload["options"]["num_predict"] == 250
    assert payload["options"]["num_ctx"] == 1536
    assert "format" not in payload
    assert "system" not in payload


def test_payload_caps_num_predict_and_forwards_format_and_system():
    payload = llm._build_payload("hi", "be nice", 0.1, 9999, stream=True, format="json")

    # Output is always bounded, regardless of the requested max.
    assert payload["options"]["num_predict"] == 350
    assert payload["format"] == "json"
    assert payload["system"] == "be nice"
    assert payload["stream"] is True


def test_availability_probe_is_memoised(monkeypatch):
    calls = {"n": 0}

    class _Resp:
        status_code = 200

    def fake_get(*args, **kwargs):
        calls["n"] += 1
        return _Resp()

    monkeypatch.setattr(llm.httpx, "get", fake_get)
    llm.reset_ollama_cache()

    assert llm.check_ollama_available() is True
    assert llm.check_ollama_available() is True
    assert llm.check_ollama_available() is True
    assert calls["n"] == 1, "repeated probes within the TTL must not re-hit HTTP"

    # After an explicit reset the cache is bypassed exactly once.
    llm.reset_ollama_cache()
    assert llm.check_ollama_available() is True
    assert calls["n"] == 2
