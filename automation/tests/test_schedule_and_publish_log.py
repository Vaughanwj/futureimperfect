from __future__ import annotations

from datetime import date, time
from pathlib import Path

from littos_poster.adapters.driven.json_publish_log import JsonPublishLog
from littos_poster.domain.models import Platform, ScheduledPost
from littos_poster.domain.schedule import Schedule


def make_post(clip_id: str, on: date) -> ScheduledPost:
    return ScheduledPost(
        clip_id=clip_id,
        clip_path=f"/clips/{clip_id}.mp4",
        publish_date=on,
        publish_time=time(18, 0),
        caption="caption",
    )


def test_schedule_due_filters_by_exact_date():
    a = make_post("a", date(2026, 8, 17))
    b = make_post("b", date(2026, 8, 18))
    schedule = Schedule(posts=(a, b))

    assert schedule.due(date(2026, 8, 17)) == [a]
    assert schedule.due(date(2026, 8, 19)) == []


def test_schedule_next_unposted_picks_earliest_from_a_given_date():
    a = make_post("a", date(2026, 8, 17))
    b = make_post("b", date(2026, 8, 18))
    schedule = Schedule(posts=(a, b))

    assert schedule.next_unposted(date(2026, 8, 18)) is b
    assert schedule.next_unposted(date(2026, 8, 20)) is None


def test_publish_log_persists_across_instances(tmp_path: Path):
    path = tmp_path / "state" / "publish_log.json"
    post = make_post("a", date(2026, 8, 17))

    log1 = JsonPublishLog(path=path)
    assert not log1.already_published(post, Platform.INSTAGRAM)
    log1.record_published(post, Platform.INSTAGRAM)

    log2 = JsonPublishLog(path=path)
    assert log2.already_published(post, Platform.INSTAGRAM)
    assert not log2.already_published(post, Platform.TIKTOK)
