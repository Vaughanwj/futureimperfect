from __future__ import annotations

from datetime import date
from typing import Protocol

from ..domain.models import ScheduledPost


class SchedulePort(Protocol):
    def due(self, on: date) -> list[ScheduledPost]: ...
