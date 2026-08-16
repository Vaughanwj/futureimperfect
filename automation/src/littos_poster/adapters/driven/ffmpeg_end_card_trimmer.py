from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


class FfmpegNotFound(RuntimeError):
    pass


class FfmpegError(RuntimeError):
    pass


def _probe_duration(clip_path: Path) -> float:
    proc = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "csv=p=0",
            str(clip_path),
        ],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise FfmpegError(f"ffprobe failed for {clip_path}: {proc.stderr.strip()}")
    return float(proc.stdout.strip())


@dataclass
class FfmpegEndCardTrimmer:
    """Cuts the trailing end_card_seconds off a clip so the TikTok upload
    carries no brand name / promotional text, per TikTok's Content Sharing
    Guidelines. IG keeps the original (untrimmed) file via a separate port
    call, this adapter never touches that copy.

    The trim point was measured empirically: every LITTOS short has a fixed
    10.0s gold end-card appended after the main content, regardless of the
    clip's total length (verified against 01/08/18, whose end-cards all
    start at duration-10.0s +/- one frame). If a future release uses a
    differently-timed end-card, override via END_CARD_TRIM_SECONDS.
    """

    end_card_seconds: float
    work_dir: Path | None = None

    def strip_end_card(self, clip_path: Path) -> Path:
        duration = _probe_duration(clip_path)
        keep_seconds = duration - self.end_card_seconds
        if keep_seconds <= 1.0:
            raise FfmpegError(
                f"{clip_path.name}: end_card_seconds={self.end_card_seconds} leaves only "
                f"{keep_seconds:.2f}s of content ({duration:.2f}s total) - refusing to trim"
            )

        out_dir = self.work_dir or Path(tempfile.mkdtemp(prefix="littos_tiktok_"))
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{clip_path.stem}_tiktok.mp4"

        proc = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", str(clip_path),
                "-t", f"{keep_seconds:.3f}",
                "-c", "copy",
                str(out_path),
            ],
            capture_output=True, text=True,
        )
        if proc.returncode != 0 or not out_path.exists():
            raise FfmpegError(f"ffmpeg trim failed for {clip_path}: {proc.stderr.strip()}")
        return out_path
