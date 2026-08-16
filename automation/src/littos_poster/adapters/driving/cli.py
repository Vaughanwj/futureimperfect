from __future__ import annotations

import argparse
import sys
from datetime import datetime

from ...config import Config
from ...domain.models import Platform
from ...domain.services import PublishDuePosts
from ..driven.csv_schedule import CsvSchedule
from ..driven.dry_run_publisher import DryRunPublisher
from ..driven.ffmpeg_end_card_trimmer import FfmpegEndCardTrimmer
from ..driven.github_pages_media_host import GithubPagesMediaHost
from ..driven.instagram_publisher import InstagramGraphPublisher
from ..driven.json_publish_log import JsonPublishLog
from ..driven.meta_token_refresher import MetaLongLivedTokenRefresher
from ..driven.notifiers import ConsoleNotifier
from ..driven.system_clock import SystemClock
from ..driven.tiktok_publisher import TikTokInboxPublisher


def _build_publish_due(config: Config) -> PublishDuePosts:
    schedule = CsvSchedule(csv_path=config.schedule_csv, clips_dir=config.clips_dir)
    media_host = GithubPagesMediaHost(site_base_url=config.site_base_url)
    media_processor = FfmpegEndCardTrimmer(end_card_seconds=config.end_card_trim_seconds)

    ig_publisher = InstagramGraphPublisher(
        media_host=media_host,
        ig_user_id=config.ig_user_id,
        access_token=config.ig_access_token,
    )
    tiktok_publisher = TikTokInboxPublisher(
        media_processor=media_processor,
        access_token=config.tiktok_access_token,
    )

    publishers = {
        Platform.INSTAGRAM: DryRunPublisher(ig_publisher) if config.dry_run else ig_publisher,
        Platform.TIKTOK: DryRunPublisher(tiktok_publisher) if config.dry_run else tiktok_publisher,
    }

    return PublishDuePosts(
        schedule=schedule,
        publishers=publishers,
        log=JsonPublishLog(path=config.publish_log_path),
        notifier=ConsoleNotifier(),
    )


def _cmd_publish_due(args: argparse.Namespace) -> int:
    config = Config.from_env()
    clock = SystemClock(timezone=config.timezone)
    today = clock.today() if args.date == "today" else datetime.strptime(args.date, "%Y-%m-%d").date()

    use_case = _build_publish_due(config)
    report = use_case.run(today)
    return 1 if report.had_failures else 0


def _cmd_refresh_ig_token(args: argparse.Namespace) -> int:  # noqa: ARG001
    import os

    config = Config.from_env()
    app_id = os.environ.get("META_APP_ID", "")
    app_secret = os.environ.get("META_APP_SECRET", "")
    if not (app_id and app_secret and config.ig_access_token):
        print(
            "META_APP_ID, META_APP_SECRET and IG_ACCESS_TOKEN must all be set",
            file=sys.stderr,
        )
        return 2

    refresher = MetaLongLivedTokenRefresher(app_id=app_id, app_secret=app_secret)
    new_token = refresher.refresh(config.ig_access_token)
    print(new_token)  # stdout only carries the token, so a workflow can capture it cleanly
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="littos-poster")
    sub = parser.add_subparsers(dest="command", required=True)

    publish_due = sub.add_parser("publish-due", help="publish today's due posts")
    publish_due.add_argument("--date", default="today", help="'today' or YYYY-MM-DD")
    publish_due.set_defaults(func=_cmd_publish_due)

    refresh = sub.add_parser("refresh-ig-token", help="exchange IG_ACCESS_TOKEN for a fresh long-lived token")
    refresh.set_defaults(func=_cmd_refresh_ig_token)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
