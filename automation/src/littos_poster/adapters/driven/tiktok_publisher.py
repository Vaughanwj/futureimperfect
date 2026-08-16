from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import requests

from ...domain.models import Platform, PostOutcome, PublishResult, ScheduledPost
from ...ports.media_processor import MediaProcessorPort


class TikTokPublishError(RuntimeError):
    pass


@dataclass
class TikTokInboxPublisher:
    """Pushes a clip into the owner's TikTok inbox as a draft via the
    Content Posting API's upload (not direct-post) endpoint.

    This is deliberately NOT full auto-publish: TikTok's guidelines make a
    "utility tool to help upload to the account(s) you manage" ineligible
    for audit, and unaudited apps are restricted to private-only posting -
    unworkable for a public brand account. The inbox/draft flow sidesteps
    both problems: the owner still taps through TikTok's own post screen
    and hits Publish themselves, so no audit is needed and the account
    stays public.

    The inbox init endpoint has no caption/title field (confirmed against
    the API reference - only source_info is accepted), so the caption is
    surfaced in PublishResult.detail for the notifier to show, and the
    owner pastes it manually in the app.

    Uploads the end-card-stripped variant (from MediaProcessorPort), not
    the original file with the promotional end-card.
    """

    media_processor: MediaProcessorPort
    access_token: str
    api_base: str = "https://open.tiktokapis.com"
    session: requests.Session = field(default_factory=requests.Session)

    platform: Platform = Platform.TIKTOK

    def publish(self, post: ScheduledPost) -> PublishResult:
        trimmed_path = self.media_processor.strip_end_card(Path(post.clip_path))
        video_bytes = trimmed_path.read_bytes()

        publish_id, upload_url = self._init_upload(len(video_bytes))
        self._upload_file(upload_url, video_bytes)

        return PublishResult(
            post=post,
            platform=self.platform,
            outcome=PostOutcome.QUEUED_FOR_MANUAL_STEP,
            detail=(
                f"pushed to TikTok inbox (publish_id {publish_id}). "
                f"Open the app to finish posting. Caption to paste: {post.caption}"
            ),
        )

    def _init_upload(self, video_size: int) -> tuple[str, str]:
        resp = self.session.post(
            f"{self.api_base}/v2/post/publish/inbox/video/init/",
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            json={
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "video_size": video_size,
                    "chunk_size": video_size,
                    "total_chunk_count": 1,
                }
            },
            timeout=30,
        )
        _raise_for_tiktok_error(resp)
        data = resp.json()["data"]
        return data["publish_id"], data["upload_url"]

    def _upload_file(self, upload_url: str, video_bytes: bytes) -> None:
        resp = self.session.put(
            upload_url,
            headers={
                "Content-Type": "video/mp4",
                "Content-Range": f"bytes 0-{len(video_bytes) - 1}/{len(video_bytes)}",
            },
            data=video_bytes,
            timeout=120,
        )
        if not resp.ok:
            raise TikTokPublishError(f"upload PUT failed ({resp.status_code}): {resp.text}")


def _raise_for_tiktok_error(resp: requests.Response) -> None:
    if resp.ok:
        body = resp.json()
        err = body.get("error", {})
        if err.get("code") not in (None, "ok"):
            raise TikTokPublishError(f"TikTok API error {err.get('code')}: {err.get('message')}")
        return
    raise TikTokPublishError(f"TikTok API HTTP error ({resp.status_code}): {resp.text}")
