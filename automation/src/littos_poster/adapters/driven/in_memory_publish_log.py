from __future__ import annotations

from dataclasses import dataclass, field

from ...domain.models import Platform, ScheduledPost


@dataclass
class InMemoryPublishLog:
    """Non-persistent PublishLogPort for dry runs.

    JsonPublishLog writes straight to automation/state/publish_log.json -
    the same file the real cron run commits back to the repo. A dry run
    against that path would record posts as "published" that never
    actually went out, causing the next real run to silently skip them.
    This adapter keeps dry-run state in memory only, so nothing on disk
    (or in the repo) is ever touched.
    """

    _entries: set[tuple[str, Platform]] = field(default_factory=set)

    def already_published(self, post: ScheduledPost, platform: Platform) -> bool:
        return (post.clip_id, platform) in self._entries

    def record_published(self, post: ScheduledPost, platform: Platform) -> None:
        self._entries.add((post.clip_id, platform))
