from __future__ import annotations

from typing import Protocol

from ..domain.models import RunReport


class NotifierPort(Protocol):
    def notify_run_complete(self, report: RunReport) -> None: ...
