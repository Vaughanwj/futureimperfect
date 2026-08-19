from __future__ import annotations

from pathlib import Path

from littos_poster.adapters.driven.in_memory_publish_log import InMemoryPublishLog
from littos_poster.adapters.driven.json_publish_log import JsonPublishLog
from littos_poster.adapters.driving.cli import ACTIVE_PLATFORMS, _build_publish_due
from littos_poster.config import Config
from littos_poster.domain.models import Platform


def make_config(tmp_path: Path, *, dry_run: bool) -> Config:
    return Config(
        clips_dir=tmp_path / "clips",
        schedule_csv=tmp_path / "schedule.csv",
        publish_log_path=tmp_path / "publish_log.json",
        site_base_url="https://example.test",
        timezone="UTC",
        end_card_trim_seconds=10.0,
        ig_user_id="ig-user",
        ig_access_token="ig-token",
        tiktok_access_token="",
        tiktok_client_key="",
        tiktok_client_secret="",
        tiktok_refresh_token="",
        dry_run=dry_run,
    )


def test_tiktok_is_not_active_by_default():
    assert ACTIVE_PLATFORMS == frozenset({Platform.INSTAGRAM})


def test_only_instagram_publisher_is_wired(tmp_path: Path):
    use_case = _build_publish_due(make_config(tmp_path, dry_run=False))

    assert set(use_case.publishers.keys()) == {Platform.INSTAGRAM}


def test_dry_run_uses_an_in_memory_log_not_the_real_file(tmp_path: Path):
    config = make_config(tmp_path, dry_run=True)

    use_case = _build_publish_due(config)

    assert isinstance(use_case.log, InMemoryPublishLog)
    assert not config.publish_log_path.exists()


def test_real_run_uses_the_json_log_backed_by_the_configured_path(tmp_path: Path):
    config = make_config(tmp_path, dry_run=False)

    use_case = _build_publish_due(config)

    assert isinstance(use_case.log, JsonPublishLog)
    assert use_case.log.path == config.publish_log_path
