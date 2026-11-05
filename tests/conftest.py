"""Keep every test away from the real local files."""
import pytest

from app import intent_repair, transcribe
from app.history import history


PROVIDER_SETTINGS = (
    "NEARAI_API_KEY", "NEAR_AI_API_KEY", "NEARAI_BASE_URL", "NEAR_AI_BASE_URL",
    "NEARAI_REPAIR_MODEL", "NEARAI_TRANSCRIBE_MODEL", "REPAIR_PROVIDER", "TRANSCRIBE_PROVIDER",
    "REPAIR_MODEL", "OPENAI_TRANSCRIBE_MODEL",
)


@pytest.fixture(autouse=True)
def local_files(monkeypatch, tmp_path, request):
    # A NEAR AI key in .env must not change which service a test talks to.
    # Tests marked live use the real keys on purpose, so they keep them.
    if request.node.get_closest_marker("live") is None:
        for name in PROVIDER_SETTINGS:
            monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HISTORY_PATH", str(tmp_path / "history.json"))
    monkeypatch.setenv("LIVE_LEDGER_PATH", str(tmp_path / "spend.json"))
    # The public guard turns history off for the whole process, so each test starts on.
    monkeypatch.setattr(history, "enabled", True)
    # No test may reach a real language model. Tests that need one turn it on with a fake.
    monkeypatch.setattr(intent_repair, "llm_allowed", False)
    monkeypatch.setattr(transcribe, "allowed", False)
