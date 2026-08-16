from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from littos_poster.adapters.driven.ffmpeg_end_card_trimmer import (
    FfmpegEndCardTrimmer,
    FfmpegError,
    _probe_duration,
)

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="ffmpeg/ffprobe not available in this environment",
)


@pytest.fixture
def synthetic_clip(tmp_path: Path) -> Path:
    """A 4s black test clip standing in for a real 'footage + end-card' file."""
    out = tmp_path / "synthetic.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=black:s=320x180:d=4",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            str(out),
        ],
        check=True, capture_output=True,
    )
    return out


def test_strip_end_card_shortens_by_configured_seconds(synthetic_clip: Path, tmp_path: Path):
    trimmer = FfmpegEndCardTrimmer(end_card_seconds=1.0, work_dir=tmp_path / "out")

    trimmed = trimmer.strip_end_card(synthetic_clip)

    assert trimmed.exists()
    original_duration = _probe_duration(synthetic_clip)
    trimmed_duration = _probe_duration(trimmed)
    assert trimmed_duration == pytest.approx(original_duration - 1.0, abs=0.2)


def test_refuses_to_trim_when_it_would_gut_the_clip(synthetic_clip: Path, tmp_path: Path):
    trimmer = FfmpegEndCardTrimmer(end_card_seconds=10.0, work_dir=tmp_path / "out")

    with pytest.raises(FfmpegError):
        trimmer.strip_end_card(synthetic_clip)
