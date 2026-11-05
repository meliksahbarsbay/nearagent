"""Keep every test away from the real local files."""
import pytest

from app import intent_repair, transcribe
from app.history import history


@pytest.fixture(autouse=True)
def local_files(monkeypatch, tmp_path):
    monkeypatch.setenv("HISTORY_PATH", str(tmp_path / "history.json"))
    monkeypatch.setenv("LIVE_LEDGER_PATH", str(tmp_path / "spend.json"))
    # The public guard turns history off for the whole process, so each test starts on.
    monkeypatch.setattr(history, "enabled", True)
    # No test may reach a real language model. Tests that need one turn it on with a fake.
    monkeypatch.setattr(intent_repair, "llm_allowed", False)
    monkeypatch.setattr(transcribe, "allowed", False)
