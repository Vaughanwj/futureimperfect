# LITTOS social auto-poster

Drips the short-form clips to Instagram Reels and the FutureWatch-AI
Facebook Page (both fully automatic) on the schedule in
`LITTOS_publer_schedule_PLAIN.csv`. Built to be reused for future
releases, not thrown away after this one.

## How it works

- **Instagram**: fully automatic. The daily GitHub Actions run publishes
  the Reel publicly with no human step.
- **Facebook (FutureWatch-AI Page)**: also fully automatic, via a
  separate `FacebookPagePublisher` posting directly to the Page (Instagram
  being linked to the Page does not cross-post API-published Reels there
  on its own - that's why this exists as its own adapter). Needs its own
  Page access token, distinct from the Instagram one - see owner setup
  step 6.
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
6. **Facebook** - already set up (`FB_PAGE_ID` / `FB_PAGE_ACCESS_TOKEN`
   secrets in place, `Platform.FACEBOOK` active). For reference, the
   permissions needed were `pages_show_list`, `pages_read_engagement`,
   `pages_manage_posts` on the Meta app, plus **the app itself connected
   as a business asset** under business.facebook.com -> Business Settings
   -> Accounts -> Apps (the Page being in a Business Portfolio meant a
   plain personal-profile token wasn't enough - `/me/accounts` returned
   empty until the app was explicitly connected there too). The Page
   token came from `GET /{page-id}?fields=name,access_token` using a
   long-lived user token, once that connection was in place.

   Unlike the IG token, this one has no fixed expiry (`expires_at: 0` via
   `/debug_token`) - no weekly-refresh workflow needed for it. It does
   carry a `data_access_expires_at` checkpoint (~90 days out from
   issuance, so ~2026-11-20 for the current token), which Meta's
   convention resets on continued active use - the daily cron should keep
   it current on its own. If Facebook posting ever starts failing with an
   auth error despite `is_valid: true` having held before, re-check that
   date and re-mint the token the same way if needed.

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
  (`0 22 * * 1-5` UTC), plus `workflow_dispatch` (with an optional `date`
  input for backfilling a missed/failed day) for manual runs. Commits
  `automation/state/publish_log.json` back to the repo after every run,
  even on partial failure, so a retry never double-posts to a platform
  that already succeeded. That commit step retries with a rebase if the
  push is rejected, but **avoid firing multiple `workflow_dispatch`
  backfills at the same time** - do them one at a time. Concurrent runs
  can still race on the git push; the retry handles it in the common case
  but isn't a substitute for just not doing that.
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
  `InstagramGraphPublisher`, `FacebookPagePublisher`, `TikTokInboxPublisher`
  (dormant), `FfmpegEndCardTrimmer`, `GithubPagesMediaHost`,
  `JsonPublishLog`, `SystemClock`, `ConsoleNotifier`,
  `MetaLongLivedTokenRefresher`.
- `adapters/driving/cli.py` - the only entrypoint; everything above it is
  wired here. `ACTIVE_PLATFORMS` at the top of this file is the single
  switch for which platforms actually get dispatched to - currently
  `Platform.INSTAGRAM` and `Platform.FACEBOOK`. A publisher is only
  constructed and registered when its platform is in that set, so
  TikTok's adapter exists but never gets wired up (or asked for TikTok
  credentials) in the default run.

Reviving TikTok (or adding a genuinely new platform) is the same
two-step recipe: add it to `ACTIVE_PLATFORMS` in `cli.py`, and to
`ScheduledPost`'s default `platforms` tuple in `domain/models.py` -
writing a new `PublisherPort` adapter first if one doesn't already
exist. Nothing else in `domain/` changes.

## Tests

```bash
cd automation
pip install -e ".[dev]"
pytest
```

Domain/use-case tests run against fake in-memory adapters (`tests/fakes.py`)
- no network, no ffmpeg. The ffmpeg trimmer has its own tests against a
synthetic generated clip and skips automatically if ffmpeg isn't on PATH.
