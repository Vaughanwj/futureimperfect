from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .models import ScheduledPost


@dataclass(frozen=True)
class Schedule:
    """In-memory, I/O-free view over the full list of scheduled posts."""

    posts: tuple[ScheduledPost, ...]

    def due(self, on: date) -> list[ScheduledPost]:
        return [p for p in self.posts if p.publish_date == on]

    def next_unposted(self, after: date) -> ScheduledPost | None:
        upcoming = sorted(
            (p for p in self.posts if p.publish_date >= after),
            key=lambda p: (p.publish_date, p.publish_time),
        )
        return upcoming[0] if upcoming else None
