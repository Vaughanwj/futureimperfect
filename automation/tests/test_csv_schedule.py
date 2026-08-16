from __future__ import annotations

from datetime import date, time
from pathlib import Path

import pytest

from littos_poster.adapters.driven.csv_schedule import CsvSchedule
from littos_poster.domain.models import Platform

CSV_CONTENT = (
    'Date,Time,Clip,Caption\n'
    '08/17/2026,18:00,01_TooFastToGovern,"""You wanted a god."" Full film free - link in bio. #reels"\n'
    '08/18/2026,18:00,02_AllIWantFromYou,"Simple caption, no quotes."\n'
)


@pytest.fixture
def schedule(tmp_path: Path) -> CsvSchedule:
    csv_path = tmp_path / "schedule.csv"
    csv_path.write_text(CSV_CONTENT, encoding="utf-8")

    clips_dir = tmp_path / "clips"
    clips_dir.mkdir()
    (clips_dir / "01_TooFastToGovern.mp4").write_bytes(b"fake")
    (clips_dir / "02_AllIWantFromYou.mp4").write_bytes(b"fake")

    return CsvSchedule(csv_path=csv_path, clips_dir=clips_dir)


def test_due_returns_only_the_matching_date(schedule: CsvSchedule):
    due = schedule.due(date(2026, 8, 17))

    assert len(due) == 1
    post = due[0]
    assert post.clip_id == "01_TooFastToGovern"
    assert post.publish_time == time(18, 0)
    assert post.caption.startswith('"You wanted a god."')
    assert post.platforms == (Platform.INSTAGRAM, Platform.TIKTOK)
    assert post.clip_path.endswith("01_TooFastToGovern.mp4")


def test_due_returns_empty_for_a_date_with_no_rows(schedule: CsvSchedule):
    assert schedule.due(date(2099, 1, 1)) == []


def test_missing_clip_file_raises(tmp_path: Path):
    csv_path = tmp_path / "schedule.csv"
    csv_path.write_text(CSV_CONTENT, encoding="utf-8")
    empty_clips_dir = tmp_path / "clips"
    empty_clips_dir.mkdir()

    schedule = CsvSchedule(csv_path=csv_path, clips_dir=empty_clips_dir)

    with pytest.raises(FileNotFoundError):
        schedule.due(date(2026, 8, 17))
