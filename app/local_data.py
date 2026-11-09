"""Keep tests and mock runs away from the real files in data/.

A mock run once wrote a fake withdrawal into the real trade history, and the app later
read it aloud as a real one. So a test or a mock run that reaches data/ now fails loudly.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REAL_DATA = ROOT / "data"


class MockDataError(RuntimeError):
    """A test or mock run tried to use the real data/ folder."""


def is_mock() -> bool:
    # pytest sets PYTEST_CURRENT_TEST while a test runs. Mock scripts set NEARAGENT_MOCK.
    flag = os.getenv("NEARAGENT_MOCK", "").strip().lower()
    return bool(os.getenv("PYTEST_CURRENT_TEST")) or flag not in {"", "0", "false", "no"}


def checked(path: Path) -> Path:
    if is_mock() and path.resolve().is_relative_to(REAL_DATA.resolve()):
        raise MockDataError(f"a test or mock run may not use {path.name} in the real data folder")
    return path
