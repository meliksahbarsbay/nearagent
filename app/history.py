"""A local record of confirmed swaps, dry and live.

It is a convenience, so a write problem never stops a swap. A live swap's real record is
the Agent API's. The file holds no keys, and git ignores it.
"""
import json
import logging
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("nearagent.history")

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = ROOT / "data" / "history.json"
KEEP = 50


class History:
    # A shared server must not read one visitor's trades to the next.
    enabled = True

    def path(self) -> Path:
        return Path(os.getenv("HISTORY_PATH") or DEFAULT_PATH)

    def _read(self) -> list[dict]:
        path = self.path()
        if not path.exists():
            return []
        entries = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(entries, list):
            raise ValueError("history is not a list")
        return entries

    def _write(self, entries: list[dict]) -> None:
        path = self.path()
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(entries[-KEEP:]), encoding="utf-8")
        temporary.replace(path)

    def add(self, **entry) -> str:
        key = secrets.token_hex(8)
        if not self.enabled:
            return key
        record = {"id": key, "at": datetime.now(timezone.utc).isoformat(), **entry}
        try:
            self._write([*self._read(), record])
        except (OSError, ValueError) as error:
            log.warning("history not saved: %s", type(error).__name__)
        return key

    def update(self, key: str, **changes) -> None:
        try:
            entries = self._read()
            for entry in entries:
                if entry["id"] == key:
                    entry.update({k: v for k, v in changes.items() if v is not None})
            self._write(entries)
        except (OSError, ValueError, KeyError, TypeError) as error:
            log.warning("history not updated: %s", type(error).__name__)

    def recent(self, count: int) -> list[dict]:
        """Newest first. An unreadable file raises, so the page can say so."""
        if not self.enabled:
            return []
        return list(reversed(self._read()[-count:]))


history = History()
