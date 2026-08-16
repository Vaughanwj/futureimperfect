from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from ...domain.models import Platform, ScheduledPost
from ...domain.schedule import Schedule


@dataclass
class CsvSchedule:
    """Reads LITTOS_publer_schedule_PLAIN.csv (Date, Time, Clip, Caption)
    and resolves each Clip id to an actual file under clips_dir."""

    csv_path: Path
    clips_dir: Path

    def _load(self) -> Schedule:
        posts: list[ScheduledPost] = []
        with self.csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                clip_id = row["Clip"].strip()
                clip_path = self._resolve_clip_path(clip_id)
                posts.append(
                    ScheduledPost(
                        clip_id=clip_id,
                        clip_path=str(clip_path),
                        publish_date=datetime.strptime(row["Date"].strip(), "%m/%d/%Y").date(),
                        publish_time=datetime.strptime(row["Time"].strip(), "%H:%M").time(),
                        caption=row["Caption"],
                        platforms=(Platform.INSTAGRAM, Platform.TIKTOK),
                    )
                )
        return Schedule(posts=tuple(posts))

    def _resolve_clip_path(self, clip_id: str) -> Path:
        matches = sorted(self.clips_dir.glob(f"{clip_id}.mp4"))
        if not matches:
            raise FileNotFoundError(f"no clip file found for '{clip_id}' under {self.clips_dir}")
        return matches[0]

    def due(self, on: date) -> list[ScheduledPost]:
        return self._load().due(on)
