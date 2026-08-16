from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from ...domain.models import Platform, ScheduledPost


def _key(post: ScheduledPost, platform: Platform) -> str:
    return f"{post.clip_id}:{platform.value}"


@dataclass
class JsonPublishLog:
    """Tracks which (clip, platform) pairs have already gone out, so a
    manual re-run of the workflow on the same day doesn't double-post.

    Backed by a JSON file that the GitHub Actions workflow commits back to
    the repo after every run - GH Actions runners have no persistent disk
    between runs, so without this the log would be lost each time.
    """

    path: Path
    _entries: set[str] = field(default_factory=set, init=False)
    _loaded: bool = field(default=False, init=False)

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self._entries = set(data.get("published", []))
        self._loaded = True

    def already_published(self, post: ScheduledPost, platform: Platform) -> bool:
        self._ensure_loaded()
        return _key(post, platform) in self._entries

    def record_published(self, post: ScheduledPost, platform: Platform) -> None:
        self._ensure_loaded()
        self._entries.add(_key(post, platform))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"published": sorted(self._entries)}, indent=2),
            encoding="utf-8",
        )
