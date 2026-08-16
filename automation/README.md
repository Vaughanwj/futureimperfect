# LITTOS social auto-poster

Drips the short-form clips to Instagram Reels (fully automatic) and TikTok
(pushed to your inbox, you tap Publish) on the schedule in
`LITTOS_publer_schedule_PLAIN.csv`. Built to be reused for future releases,
not thrown away after this one.

## How it works

- **Instagram**: fully automatic. The daily GitHub Actions run publishes
  the Reel publicly with no human step.
- **TikTok**: semi-manual by design. TikTok's own guidelines make a
  self-use auto-poster ineligible for the audit required to auto-publish
  publicly, so the pipeline instead pushes the clip into your TikTok
  inbox as a draft each run. Open the app, tap through the normal post
  screen (the caption isn't carried by the API - paste it from the run's
  summary, see below), and hit Publish yourself. About a minute.
- The clip sent to TikTok has the gold end-card trimmed off first
  (`END_CARD_TRIM_SECONDS`, default 10.0s). TikTok's Content Sharing
  Guidelines prohibit brand names/promotional text/links on API-shared
  content, and the end-card says "A film by Future Imperfect / Available
  for free on YouTube now!" - so IG gets the full clip, TikTok gets the
  footage only.

## One-time owner setup

1. **Instagram Business account.** Convert `shadow_spray_art` to a
   Business account and link it to the FutureWatch-AI Facebook Page.
2. **Meta app.** Create one at developers.facebook.com, add the
   `instagram_business_basic` + `instagram_business_content_publish`
   permissions, generate a long-lived user token, and note the IG user id.
   You do **not** need to submit for App Review: Meta only requires review
   for people who aren't already on the app's own role list, and since
   this only ever posts to your own account, adding yourself as
   Admin/Developer/Tester on the app is enough to publish in Development
   Mode indefinitely.
3. **TikTok for Developers app.** Add the Content Posting API, enable
   `video.upload` (inbox scope), authorize the FutureWatch-AI TikTok
   account, note the access token. No domain verification needed - this
   pipeline uploads file bytes directly (`FILE_UPLOAD`), not
   `PULL_FROM_URL`.
4. **GitHub repo secrets** (Settings -> Secrets and variables -> Actions):
   - `IG_USER_ID`, `IG_ACCESS_TOKEN`
   - `META_APP_ID`, `META_APP_SECRET` (only needed for the token-refresh
     workflow)
   - `TIKTOK_ACCESS_TOKEN`, `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`,
     `TIKTOK_REFRESH_TOKEN`
   - `GH_PAT` - a personal access token with `repo` scope, only needed if
     you want the weekly token-refresh workflow to update `IG_ACCESS_TOKEN`
     automatically (it calls `gh secret set`, which the default
     `GITHUB_TOKEN` isn't allowed to do). Skip it and refresh manually
     every ~60 days if you'd rather not maintain a PAT.
5. Clips already live at `/clips/*.mp4` and the schedule at
   `/LITTOS_publer_schedule_PLAIN.csv`, both committed to this repo so
   GitHub Pages serves them at `https://futureimperfect.band/clips/...`
   for the Instagram Graph API's `video_url`.

## Running it

```bash
cd automation
pip install -e ".[dev]"
cp .env.example .env   # fill in secrets for a local run
littos-poster publish-due --date today
```

Set `DRY_RUN=true` in `.env` to log what would happen without calling any
real API - useful before secrets are wired up. `--date YYYY-MM-DD` lets you
test or backfill a specific day.

`littos-poster refresh-ig-token` exchanges `IG_ACCESS_TOKEN` for a fresh
~60-day token and prints it to stdout (needs `META_APP_ID`/`META_APP_SECRET`
set too).

## Automation

Two GitHub Actions workflows, both in `.github/workflows/` at the repo
root (GitHub only reads workflows from there, not from `automation/`):

- **`social-publish.yml`** - runs weekdays at 18:00 America/New_York
  (`0 22 * * 1-5` UTC), plus `workflow_dispatch` for manual runs. Commits
  `automation/state/publish_log.json` back to the repo after every run,
  even on partial failure, so a retry never double-posts to a platform
  that already succeeded.
- **`refresh-ig-token.yml`** - weekly, keeps the Meta token from ever
  approaching its ~60-day expiry.

**DST caveat**: GitHub Actions cron is UTC-only and doesn't shift for
daylight saving. `0 22 * * 1-5` lands at 18:00 during EDT (summer) and
17:00 during EST (winter) - a known one-hour seasonal drift. If your
timezone isn't America/New_York, or you want exact-time posting
year-round, adjust the cron expression and the `TIMEZONE` env var in
`social-publish.yml` together.

## Architecture

Hexagonal / ports-and-adapters, `src/littos_poster/`:

- `domain/` - `ScheduledPost`, `Schedule`, and the `PublishDuePosts` use
  case. No I/O, no knowledge of HTTP or ffmpeg.
- `ports/` - the interfaces the domain depends on
  (`PublisherPort`, `SchedulePort`, `MediaHostPort`, `MediaProcessorPort`,
  `PublishLogPort`, `ClockPort`, `NotifierPort`).
- `adapters/driven/` - the implementations: `CsvSchedule`,
  `InstagramGraphPublisher`, `TikTokInboxPublisher`,
  `FfmpegEndCardTrimmer`, `GithubPagesMediaHost`, `JsonPublishLog`,
  `SystemClock`, `ConsoleNotifier`, `MetaLongLivedTokenRefresher`.
- `adapters/driving/cli.py` - the only entrypoint; everything above it is
  wired here.

Adding a platform later (the spec calls out Facebook as an easy one) means
writing one new `PublisherPort` adapter and registering it in
`cli.py::_build_publish_due` - nothing in `domain/` changes.

## Tests

```bash
cd automation
pip install -e ".[dev]"
pytest
```

Domain/use-case tests run against fake in-memory adapters (`tests/fakes.py`)
- no network, no ffmpeg. The ffmpeg trimmer has its own tests against a
synthetic generated clip and skips automatically if ffmpeg isn't on PATH.
