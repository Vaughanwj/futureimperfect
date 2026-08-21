from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

import requests

from ...domain.models import Platform, PostOutcome, PublishResult, ScheduledPost
from ...ports.media_host import MediaHostPort


class FacebookPublishError(RuntimeError):
    pass


@dataclass
class FacebookPagePublisher:
    """Publishes a Reel to a Facebook Page via the Page Reels Publishing
    API: start an upload session, have Meta pull the file from our own
    hosted video_url (same GithubPagesMediaHost URL Instagram uses), then
    finish/publish.

    NOT LIVE-VERIFIED. Built from Meta's documented three-phase flow
    (upload_phase=start -> hosted-file transfer -> upload_phase=finish),
    the same pattern used elsewhere in Meta's video upload APIs, but this
    repo has no Facebook Page credentials yet to test against. Expect a
    debugging pass the first time this actually runs, the same way the
    Instagram and TikTok adapters both needed one.

    Requires a Page (not user) access token with pages_manage_posts, and
    the target Page's id. A Page token minted from a still-valid user
    token via GET /me/accounts does not expire on its own timeline the
    way the IG user token does, but re-derive it if the source user token
    is ever revoked or regenerated.
    """

    media_host: MediaHostPort
    page_id: str
    access_token: str
    api_version: str = "v21.0"
    poll_interval_seconds: float = 5.0
    poll_timeout_seconds: float = 180.0
    session: requests.Session = field(default_factory=requests.Session)

    platform: Platform = Platform.FACEBOOK

    @property
    def _base(self) -> str:
        return f"https://graph.facebook.com/{self.api_version}"

    def publish(self, post: ScheduledPost) -> PublishResult:
        video_url = self.media_host.public_url(Path(post.clip_path))

        video_id, upload_url = self._start_upload()
        self._transfer_hosted_file(upload_url, video_url)
        self._finish_and_publish(video_id, post.caption)
        self._wait_until_ready(video_id)

        return PublishResult(
            post=post,
            platform=self.platform,
            outcome=PostOutcome.PUBLISHED,
            detail=f"fb page video id {video_id}",
        )

    def _start_upload(self) -> tuple[str, str]:
        resp = self.session.post(
            f"{self._base}/{self.page_id}/video_reels",
            data={"upload_phase": "start", "access_token": self.access_token},
            timeout=30,
        )
        _raise_for_graph_error(resp)
        data = resp.json()
        return data["video_id"], data["upload_url"]

    def _transfer_hosted_file(self, upload_url: str, video_url: str) -> None:
        resp = self.session.post(
            upload_url,
            headers={
                "Authorization": f"OAuth {self.access_token}",
                "file_url": video_url,
            },
            timeout=120,
        )
        if not resp.ok or resp.json().get("success") is False:
            raise FacebookPublishError(f"hosted file transfer failed ({resp.status_code}): {resp.text}")

    def _finish_and_publish(self, video_id: str, caption: str) -> None:
        resp = self.session.post(
            f"{self._base}/{self.page_id}/video_reels",
            data={
                "upload_phase": "finish",
                "video_id": video_id,
                "video_state": "PUBLISHED",
                "description": caption,
                "access_token": self.access_token,
            },
            timeout=30,
        )
        _raise_for_graph_error(resp)
        if resp.json().get("success") is False:
            raise FacebookPublishError(f"finish/publish reported failure: {resp.text}")

    def _wait_until_ready(self, video_id: str) -> None:
        """Best-effort status check - doesn't hard-fail on an unrecognized
        status shape, since the exact field name/values here are the least
        certain part of this adapter without a live account to test against."""
        deadline = time.monotonic() + self.poll_timeout_seconds
        while time.monotonic() < deadline:
            resp = self.session.get(
                f"{self._base}/{video_id}",
                params={"fields": "status", "access_token": self.access_token},
                timeout=30,
            )
            if not resp.ok:
                return
            status = resp.json().get("status", {})
            phase = status.get("video_status") if isinstance(status, dict) else status
            if phase in ("ready", "PUBLISHED", None):
                return
            if phase in ("error", "ERROR", "failed"):
                raise FacebookPublishError(f"video {video_id} processing failed: {status}")
            time.sleep(self.poll_interval_seconds)


def _raise_for_graph_error(resp: requests.Response) -> None:
    if resp.ok:
        return
    try:
        detail = resp.json().get("error", {}).get("message", resp.text)
    except ValueError:
        detail = resp.text
    raise FacebookPublishError(f"Graph API error ({resp.status_code}): {detail}")
