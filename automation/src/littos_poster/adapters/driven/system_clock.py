from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo


class SystemClock:
    def __init__(self, timezone: str) -> None:
        self._tz = ZoneInfo(timezone)

    def today(self) -> date:
        return datetime.now(self._tz).date()
