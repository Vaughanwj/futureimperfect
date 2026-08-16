from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

import requests

from ...domain.models import Platform, PostOutcome, PublishResult, ScheduledPost
from ...ports.media_host import MediaHostPort


class InstagramPublishError(RuntimeError):
    pass


@dataclass
class InstagramGraphPublisher:
    """Publishes a Reel via the Instagram Graph API content-publishing flow:
    create container (video_url) -> poll until FINISHED -> publish.

    Requires the IG account to be a Business account linked to a Facebook
    Page, and a Meta app with instagram_business_basic +
    instagram_business_content_publish. Since this only ever posts to the
    app owner's own account, Meta App Review is not required - having the
    account's user added with a role on the app (Admin/Developer/Tester) is
    enough for Development Mode to work indefinitely.
    """

    media_host: MediaHostPort
    ig_user_id: str
    access_token: str
    api_version: str = "v21.0"
    poll_interval_seconds: float = 5.0
    poll_timeout_seconds: float = 180.0
    session: requests.Session = field(default_factory=requests.Session)

    platform: Platform = Platform.INSTAGRAM

    @property
    def _base(self) -> str:
        return f"https://graph.facebook.com/{self.api_version}"

    def publish(self, post: ScheduledPost) -> PublishResult:
        video_url = self.media_host.public_url(Path(post.clip_path))

        container_id = self._create_container(video_url, post.caption)
        self._wait_until_finished(container_id)
        media_id = self._publish_container(container_id)

        return PublishResult(
            post=post,
            platform=self.platform,
            outcome=PostOutcome.PUBLISHED,
            detail=f"ig media id {media_id}",
        )

    def _create_container(self, video_url: str, caption: str) -> str:
        resp = self.session.post(
            f"{self._base}/{self.ig_user_id}/media",
            data={
                "media_type": "REELS",
                "video_url": video_url,
                "caption": caption,
                "access_token": self.access_token,
            },
            timeout=30,
        )
        _raise_for_graph_error(resp)
        return resp.json()["id"]

    def _wait_until_finished(self, container_id: str) -> None:
        deadline = time.monotonic() + self.poll_timeout_seconds
        while True:
            resp = self.session.get(
                f"{self._base}/{container_id}",
                params={"fields": "status_code", "access_token": self.access_token},
                timeout=30,
            )
            _raise_for_graph_error(resp)
            status = resp.json().get("status_code")
            if status == "FINISHED":
                return
            if status == "ERROR":
                raise InstagramPublishError(f"container {container_id} failed processing")
            if time.monotonic() > deadline:
                raise InstagramPublishError(
                    f"container {container_id} still '{status}' after {self.poll_timeout_seconds}s"
                )
            time.sleep(self.poll_interval_seconds)

    def _publish_container(self, container_id: str) -> str:
        resp = self.session.post(
            f"{self._base}/{self.ig_user_id}/media_publish",
            data={"creation_id": container_id, "access_token": self.access_token},
            timeout=30,
        )
        _raise_for_graph_error(resp)
        return resp.json()["id"]


def _raise_for_graph_error(resp: requests.Response) -> None:
    if resp.ok:
        return
    try:
        detail = resp.json().get("error", {}).get("message", resp.text)
    except ValueError:
        detail = resp.text
    raise InstagramPublishError(f"Graph API error ({resp.status_code}): {detail}")
