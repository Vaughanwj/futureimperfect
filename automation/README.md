# LITTOS social auto-poster

Drips the short-form clips to Instagram Reels (fully automatic) on the
schedule in `LITTOS_publer_schedule_PLAIN.csv`. Built to be reused for
future releases, not thrown away after this one.

## How it works

- **Instagram**: fully automatic. The daily GitHub Actions run publishes
  the Reel publicly with no human step.
- **TikTok is not part of this pipeline.** The Content Posting API turned
  out to be a dead end for a public brand account: unaudited apps are
  restricted to `SELF_ONLY` posting on a private account, and TikTok's
  audit guidelines explicitly reject "a utility tool to help upload to
  the account(s) you manage" as a use case - so there's no path to
  auto-publishing publicly through the API. TikTok posting is handled
  natively via **TikTok Studio's own scheduler** instead.
  The `TikTokInboxPublisher` adapter (inbox/draft upload) is still in the
  codebase and still tested, in case the API route is ever worth
  revisiting - it's just not wired into the default run. See
  `ACTIVE_PLATFORMS` in `adapters/driving/cli.py` to re-enable it.
- **Facebook (FutureWatch-AI Page): built, not yet turned on.** Instagram
  being linked to the Page doesn't cross-post API-published Reels there
  automatically - that's a separate `FacebookPagePublisher` adapter,
  written but **not live-verified** (no Page credentials exist yet to
  test against). See §One-time owner setup to enable it.

## One-time owner setup

1. **Instagram Business account.** Convert `shadow_spray_art` to a
   Business account and link it to the FutureWatch-AI Facebook Page.
2. **Meta app.** Create one at developers.facebook.com, add the
   `instagram_business_basic` + `instagram_business_content_publish`
   permissions, and note the IG user id. You do **not** need to submit for
   App Review: Meta only requires review for people who aren't already on
   the app's own role list, and since this only ever posts to your own
   account, adding yourself as Admin/Developer/Tester on the app is enough
   to publish in Development Mode indefinitely.

   **The token must be long-lived, not the raw token Graph API Explorer
   gives you.** A token straight out of the Explorer is short-lived
   (expires in ~1-2 hours) and *will* silently break the next cron run.
   Exchange it before saving it anywhere:
   ```bash
   curl -s "https://graph.facebook.com/v21.0/oauth/access_token?grant_type=fb_exchange_token&client_id=$META_APP_ID&client_secret=$META_APP_SECRET&fb_exchange_token=$SHORT_LIVED_TOKEN"
   ```
   The `access_token` in that response is the long-lived one (~60 days) -
   that's what goes in the `IG_ACCESS_TOKEN` secret below. (Equivalently:
   set `IG_ACCESS_TOKEN` to the short-lived token temporarily and run
   `littos-poster refresh-ig-token` once locally, then use *its* output.)
   Sanity-check with the token debug tool
   (developers.facebook.com/tools/debug/accesstoken) that `Expires` shows
   weeks out, not hours, before moving on.
3. **GitHub repo secrets** (Settings -> Secrets and variables -> Actions):
   - `IG_USER_ID`, `IG_ACCESS_TOKEN`
   - `META_APP_ID`, `META_APP_SECRET` (only needed for the token-refresh
     workflow)
   - `GH_PAT` - a personal access token with `repo` scope. Needed for the
     weekly token-refresh workflow to actually persist a refreshed token
     (it calls `gh secret set`, which the default `GITHUB_TOKEN` isn't
     allowed to do). **Without this, `refresh-ig-token.yml` computes a new
     token every week and then has nowhere to put it** - the old one
     keeps ticking down to expiry regardless. Only skip this if you're
     committing to refreshing `IG_ACCESS_TOKEN` by hand before every
     ~60-day deadline.
4. Clips already live at `/clips/*.mp4` and the schedule at
   `/LITTOS_publer_schedule_PLAIN.csv`, both committed to this repo so
   GitHub Pages serves them at `https://futureimperfect.band/clips/...`
   for the Instagram Graph API's `video_url`.
5. **TikTok**: schedule posts natively in TikTok Studio (app or
   tiktok.com) using the same clips/captions from
   `LITTOS_publer_schedule_PLAIN.csv` - no pipeline setup needed.
6. **Facebook (optional, to enable Page cross-posting):**
   - In the same Meta app, add the `pages_show_list`, `pages_read_engagement`,
     and `pages_manage_posts` permissions.
   - Generate a *user* token in Graph API Explorer with those scopes, then
     call `GET /me/accounts?access_token=<user_token>` - the response
     lists your pages with a page-specific `access_token` and `id` for
     each. Use the FutureWatch-AI Page's values.
   - Add `FB_PAGE_ID` and `FB_PAGE_ACCESS_TOKEN` as GitHub repo secrets.
   - In `adapters/driving/cli.py`, add `Platform.FACEBOOK` to
     `ACTIVE_PLATFORMS`, and in `domain/models.py` add it to
     `ScheduledPost`'s default `platforms` tuple. Without both, either
     nothing dispatches to Facebook, or it dispatches with no publisher
     registered and fails every run.
   - Expect to debug the actual Graph API calls the first time this runs
     for real - see the warning in `facebook_page_publisher.py`.

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
  `InstagramGraphPublisher`, `TikTokInboxPublisher` (dormant),
  `FacebookPagePublisher` (dormant, unverified), `FfmpegEndCardTrimmer`,
  `GithubPagesMediaHost`, `JsonPublishLog`, `SystemClock`,
  `ConsoleNotifier`, `MetaLongLivedTokenRefresher`.
- `adapters/driving/cli.py` - the only entrypoint; everything above it is
  wired here. `ACTIVE_PLATFORMS` at the top of this file is the single
  switch for which platforms actually get dispatched to - currently just
  `Platform.INSTAGRAM`. A publisher is only constructed and registered
  when its platform is in that set, so TikTok's and Facebook's adapters
  exist but never get wired up (or asked for their credentials) in the
  default run.

Reviving TikTok or turning on Facebook is the same two-step recipe either
way: add the platform to `ACTIVE_PLATFORMS` in `cli.py`, and to
`ScheduledPost`'s default `platforms` tuple in `domain/models.py`. Adding
a genuinely new platform beyond those two means writing one new
`PublisherPort` adapter first, then the same two steps - nothing else in
`domain/` changes.

## Tests

```bash
cd automation
pip install -e ".[dev]"
pytest
```

Domain/use-case tests run against fake in-memory adapters (`tests/fakes.py`)
- no network, no ffmpeg. The ffmpeg trimmer has its own tests against a
synthetic generated clip and skips automatically if ffmpeg isn't on PATH.
