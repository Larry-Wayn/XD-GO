import pytest


@pytest.fixture(autouse=True)
def clear_live_ai_keys(monkeypatch):
    monkeypatch.delenv('DEEPSEEK_API_KEY', raising=False)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
