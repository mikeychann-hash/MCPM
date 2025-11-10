"""Tests for Grok configuration normalization and diagnostics."""

import json

import pytest

from mcp_backend import LLMBackend


def _make_backend(grok_overrides=None):
    config = {
        "llm": {
            "default_provider": "grok",
            "providers": {
                "grok": {
                    "model": "grok-beta",
                    "base_url": "https://api.x.ai/v1",
                }
            },
        }
    }
    if grok_overrides:
        config["llm"]["providers"]["grok"].update(grok_overrides)
    return LLMBackend(config)


def test_normalize_upgrades_deprecated_model():
    backend = _make_backend()
    assert backend.config["providers"]["grok"]["model"] == "grok-3"


def test_normalize_fills_missing_fields():
    backend = _make_backend({"model": None, "base_url": None})
    grok_conf = backend.config["providers"]["grok"]
    assert grok_conf["model"] == "grok-3"
    assert grok_conf["base_url"] == "https://api.x.ai/v1"


def test_diagnose_grok_error_contains_hint():
    backend = _make_backend()
    body = json.dumps({"error": {"message": "Model not found: grok-beta"}})
    message = backend._diagnose_grok_error(404, body, "grok-beta", "https://api.x.ai/v1")
    assert "grok-3" in message


def test_extract_message_content_flattens_segments():
    backend = _make_backend()
    response = {"choices": [{"message": {"content": [{"type": "text", "text": "Hello"}]}}]}
    content = backend._extract_message_content(response, "grok")
    assert content == "Hello"
