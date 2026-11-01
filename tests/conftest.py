"""Keep every test away from the real local files."""
import pytest


@pytest.fixture(autouse=True)
def local_files(monkeypatch, tmp_path):
    monkeypatch.setenv("HISTORY_PATH", str(tmp_path / "history.json"))
    monkeypatch.setenv("LIVE_LEDGER_PATH", str(tmp_path / "spend.json"))
