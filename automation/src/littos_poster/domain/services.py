from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ..ports.notifier import NotifierPort
from ..ports.publish_log import PublishLogPort
from ..ports.publisher import PublisherPort
from ..ports.schedule_port import SchedulePort
from .models import Platform, PostOutcome, PublishResult, RunReport, ScheduledPost


@dataclass
class PublishDuePosts:
    """Use case: fetch posts due today, dispatch each to its platforms,
    skipping anything already logged as published, and report the result."""

    schedule: SchedulePort
    publishers: dict[Platform, PublisherPort]
    log: PublishLogPort
    notifier: NotifierPort

    def run(self, today: date) -> RunReport:
        report = RunReport()
        for post in self.schedule.due(today):
            for platform in post.platforms:
                report.results.append(self._dispatch(post, platform))
        self.notifier.notify_run_complete(report)
        return report

    def _dispatch(self, post: ScheduledPost, platform: Platform) -> PublishResult:
        if self.log.already_published(post, platform):
            return PublishResult(
                post=post,
                platform=platform,
                outcome=PostOutcome.PUBLISHED,
                detail="already published in a prior run, skipped",
            )

        publisher = self.publishers.get(platform)
        if publisher is None:
            return PublishResult(
                post=post,
                platform=platform,
                outcome=PostOutcome.FAILED,
                error=f"no publisher configured for platform {platform.value}",
            )

        try:
            result = publisher.publish(post)
        except Exception as exc:  # noqa: BLE001 - surface any adapter failure to the owner
            return PublishResult(
                post=post,
                platform=platform,
                outcome=PostOutcome.FAILED,
                error=str(exc),
            )

        if result.ok:
            self.log.record_published(post, platform)
        return result
