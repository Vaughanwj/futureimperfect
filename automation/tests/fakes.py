from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from littos_poster.domain.models import (
    Platform,
    PostOutcome,
    PublishResult,
    RunReport,
    ScheduledPost,
)


@dataclass
class FakeSchedule:
    posts: list[ScheduledPost]

    def due(self, on: date) -> list[ScheduledPost]:
        return [p for p in self.posts if p.publish_date == on]


@dataclass
class FakePublisher:
    platform: Platform
    should_fail: bool = False
    calls: list[ScheduledPost] = field(default_factory=list)

    def publish(self, post: ScheduledPost) -> PublishResult:
        self.calls.append(post)
        if self.should_fail:
            return PublishResult(
                post=post, platform=self.platform, outcome=PostOutcome.FAILED, error="boom"
            )
        return PublishResult(
            post=post, platform=self.platform, outcome=PostOutcome.PUBLISHED, detail="ok"
        )


@dataclass
class FakePublishLog:
    published: set[tuple[str, Platform]] = field(default_factory=set)

    def already_published(self, post: ScheduledPost, platform: Platform) -> bool:
        return (post.clip_id, platform) in self.published

    def record_published(self, post: ScheduledPost, platform: Platform) -> None:
        self.published.add((post.clip_id, platform))


@dataclass
class FakeNotifier:
    reports: list[RunReport] = field(default_factory=list)

    def notify_run_complete(self, report: RunReport) -> None:
        self.reports.append(report)
