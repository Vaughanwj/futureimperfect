from __future__ import annotations

from typing import Protocol

from ..domain.models import Platform, PublishResult, ScheduledPost


class PublisherPort(Protocol):
    """One implementation per social platform."""

    platform: Platform

    def publish(self, post: ScheduledPost) -> PublishResult: ...
