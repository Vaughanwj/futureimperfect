from __future__ import annotations

from pathlib import Path
from typing import Protocol


class MediaProcessorPort(Protocol):
    """Produces a platform-specific variant of a clip.

    TikTok's Content Sharing Guidelines prohibit promotional text/links/
    brand names on API-shared content, so the TikTok variant strips the
    gold end-card that IG keeps.
    """

    def strip_end_card(self, clip_path: Path) -> Path: ...
