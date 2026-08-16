from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def _env(name: str, default: str | None = None, *, required: bool = False) -> str:
    value = os.environ.get(name, default)
    if required and not value:
        raise RuntimeError(f"missing required environment variable: {name}")
    return value or ""


@dataclass(frozen=True)
class Config:
    # Content locations
    clips_dir: Path
    schedule_csv: Path
    publish_log_path: Path
    site_base_url: str
    timezone: str
    end_card_trim_seconds: float

    # Instagram Graph API
    ig_user_id: str
    ig_access_token: str

    # TikTok Content Posting API (inbox/draft flow)
    tiktok_access_token: str
    tiktok_client_key: str
    tiktok_client_secret: str
    tiktok_refresh_token: str

    dry_run: bool

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            clips_dir=Path(_env("CLIPS_DIR", str(REPO_ROOT / "clips"))),
            schedule_csv=Path(
                _env("SCHEDULE_CSV", str(REPO_ROOT / "LITTOS_publer_schedule_PLAIN.csv"))
            ),
            publish_log_path=Path(
                _env("PUBLISH_LOG_PATH", str(REPO_ROOT / "automation" / "state" / "publish_log.json"))
            ),
            site_base_url=_env("SITE_BASE_URL", "https://futureimperfect.band"),
            timezone=_env("TIMEZONE", "America/New_York"),
            end_card_trim_seconds=float(_env("END_CARD_TRIM_SECONDS", "10.0")),
            ig_user_id=_env("IG_USER_ID"),
            ig_access_token=_env("IG_ACCESS_TOKEN"),
            tiktok_access_token=_env("TIKTOK_ACCESS_TOKEN"),
            tiktok_client_key=_env("TIKTOK_CLIENT_KEY"),
            tiktok_client_secret=_env("TIKTOK_CLIENT_SECRET"),
            tiktok_refresh_token=_env("TIKTOK_REFRESH_TOKEN"),
            dry_run=_env("DRY_RUN", "false").lower() in ("1", "true", "yes"),
        )
