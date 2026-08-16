from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time
from enum import Enum


class Platform(str, Enum):
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"


class PostOutcome(str, Enum):
    PUBLISHED = "published"
    QUEUED_FOR_MANUAL_STEP = "queued_for_manual_step"
    FAILED = "failed"


@dataclass(frozen=True)
class ScheduledPost:
    clip_id: str
    clip_path: str
    publish_date: date
    publish_time: time
    caption: str
    platforms: tuple[Platform, ...] = (Platform.INSTAGRAM, Platform.TIKTOK)


@dataclass(frozen=True)
class PublishResult:
    post: ScheduledPost
    platform: Platform
    outcome: PostOutcome
    detail: str = ""
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.outcome is not PostOutcome.FAILED


@dataclass
class RunReport:
    results: list[PublishResult] = field(default_factory=list)

    @property
    def failures(self) -> list[PublishResult]:
        return [r for r in self.results if not r.ok]

    @property
    def had_failures(self) -> bool:
        return len(self.failures) > 0
