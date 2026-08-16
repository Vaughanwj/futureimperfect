from __future__ import annotations

from pathlib import Path
from typing import Protocol


class MediaHostPort(Protocol):
    """Resolves a local clip to a public URL (required for IG Graph API,
    optional for TikTok PULL_FROM_URL)."""

    def public_url(self, clip_path: Path) -> str: ...
