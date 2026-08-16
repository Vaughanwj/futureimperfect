from __future__ import annotations

from dataclasses import dataclass

from ...domain.models import PostOutcome, PublishResult, ScheduledPost
from ...ports.publisher import PublisherPort


@dataclass
class DryRunPublisher:
    """Wraps a real publisher so DRY_RUN=true never hits a live API."""

    wrapped: PublisherPort

    @property
    def platform(self):  # noqa: ANN201
        return self.wrapped.platform

    def publish(self, post: ScheduledPost) -> PublishResult:
        return PublishResult(
            post=post,
            platform=self.wrapped.platform,
            outcome=PostOutcome.PUBLISHED,
            detail=f"DRY RUN - would publish '{post.clip_id}' to {self.wrapped.platform.value}",
        )
