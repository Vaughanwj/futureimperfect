from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class GithubPagesMediaHost:
    """Clips live at <site_base_url>/clips/<filename> once committed to the
    repo and served by GitHub Pages. This adapter assumes the file is
    already pushed - it only computes the predictable public URL."""

    site_base_url: str

    def public_url(self, clip_path: Path) -> str:
        return f"{self.site_base_url.rstrip('/')}/clips/{clip_path.name}"
