from __future__ import annotations

from typing import Protocol

from ..domain.models import Platform, ScheduledPost


class PublishLogPort(Protocol):
    """Idempotency guard: has this (clip, platform) pair already gone out?

    Needed because GitHub Actions runners are stateless between runs, and a
    manual re-run on a day that already succeeded must not double-post.
    """

    def already_published(self, post: ScheduledPost, platform: Platform) -> bool: ...

    def record_published(self, post: ScheduledPost, platform: Platform) -> None: ...
