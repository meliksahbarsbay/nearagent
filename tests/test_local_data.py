"""A test or mock run must never touch the real files in data/."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app import live
from app.history import history
from app.local_data import REAL_DATA, MockDataError, is_mock

ROOT = Path(__file__).resolve().parent.parent


def test_tests_write_history_to_a_temporary_folder(tmp_path):
    history.add(mode="withdraw", gave="0.1", gave_symbol="NEAR", status="done")
    assert history.path().parent == tmp_path
    assert not history.path().resolve().is_relative_to(REAL_DATA.resolve())


def test_a_test_that_loses_the_temporary_path_cannot_reach_real_history(monkeypatch):
    monkeypatch.delenv("HISTORY_PATH")
    real = REAL_DATA / "history.json"
    before = real.read_bytes() if real.exists() else None
    with pytest.raises(MockDataError):
        history.add(mode="withdraw", gave="0.1", gave_symbol="NEAR", status="done", ref="MockTxHash111")
    with pytest.raises(MockDataError):
        history.recent(5)
    assert (real.read_bytes() if real.exists() else None) == before


def test_a_test_cannot_reach_the_real_spend_ledger(monkeypatch):
    monkeypatch.delenv("LIVE_LEDGER_PATH")
    with pytest.raises(MockDataError):
        live.ledger.reserve("k", 1)


def test_the_mock_flag(monkeypatch):
    monkeypatch.delenv("PYTEST_CURRENT_TEST")
    for value in ("", "0", "false"):
        monkeypatch.setenv("NEARAGENT_MOCK", value)
        assert is_mock() is False
    monkeypatch.setenv("NEARAGENT_MOCK", "1")
    assert is_mock() is True


def run_outside_pytest(code, **env):
    clean = {k: v for k, v in os.environ.items()
             if k not in {"PYTEST_CURRENT_TEST", "HISTORY_PATH", "LIVE_LEDGER_PATH", "NEARAGENT_MOCK"}}
    return subprocess.run([sys.executable, "-c", code], cwd=ROOT, env={**clean, **env},
                          capture_output=True, text=True, timeout=60)


def test_a_mock_script_outside_pytest_cannot_write_real_history():
    # This is how the fake withdrawal got in: a mock script with no HISTORY_PATH.
    code = (
        "from app.history import history\n"
        "from app.local_data import MockDataError\n"
        "try:\n"
        "    history.add(mode='withdraw', status='done', ref='MockTxHash111')\n"
        "except MockDataError:\n"
        "    print('refused')\n"
    )
    result = run_outside_pytest(code, NEARAGENT_MOCK="1")
    assert result.stdout.strip() == "refused", result.stderr


def test_a_mock_script_can_use_its_own_history_file(tmp_path):
    code = "from app.history import history\nhistory.add(mode='withdraw', status='done')\nprint(history.path())"
    path = tmp_path / "mock_history.json"
    result = run_outside_pytest(code, NEARAGENT_MOCK="1", HISTORY_PATH=str(path))
    assert result.returncode == 0, result.stderr
    assert path.exists()


def test_the_real_app_still_uses_data_when_not_mocked():
    code = "from app.history import history\nprint(history.path())"
    result = run_outside_pytest(code)
    assert result.returncode == 0, result.stderr
    assert Path(result.stdout.strip()) == REAL_DATA / "history.json"
