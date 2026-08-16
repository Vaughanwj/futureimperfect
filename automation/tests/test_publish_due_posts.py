from __future__ import annotations

from datetime import date, time

from fakes import FakeNotifier, FakePublishLog, FakePublisher, FakeSchedule

from littos_poster.domain.models import Platform, PostOutcome, ScheduledPost
from littos_poster.domain.services import PublishDuePosts

TODAY = date(2026, 8, 17)


def make_post(clip_id: str = "01_TooFastToGovern", **kwargs) -> ScheduledPost:
    defaults = dict(
        clip_id=clip_id,
        clip_path=f"/clips/{clip_id}.mp4",
        publish_date=TODAY,
        publish_time=time(18, 0),
        caption="a caption",
        platforms=(Platform.INSTAGRAM, Platform.TIKTOK),
    )
    defaults.update(kwargs)
    return ScheduledPost(**defaults)


def build_use_case(posts, ig_fails=False, tiktok_fails=False):
    schedule = FakeSchedule(posts=posts)
    ig = FakePublisher(platform=Platform.INSTAGRAM, should_fail=ig_fails)
    tiktok = FakePublisher(platform=Platform.TIKTOK, should_fail=tiktok_fails)
    log = FakePublishLog()
    notifier = FakeNotifier()
    use_case = PublishDuePosts(
        schedule=schedule,
        publishers={Platform.INSTAGRAM: ig, Platform.TIKTOK: tiktok},
        log=log,
        notifier=notifier,
    )
    return use_case, ig, tiktok, log, notifier


def test_dispatches_due_post_to_every_configured_platform():
    post = make_post()
    use_case, ig, tiktok, log, notifier = build_use_case([post])

    report = use_case.run(TODAY)

    assert ig.calls == [post]
    assert tiktok.calls == [post]
    assert len(report.results) == 2
    assert not report.had_failures
    assert notifier.reports == [report]


def test_skips_posts_not_due_today():
    other_day_post = make_post(publish_date=date(2026, 8, 18))
    use_case, ig, tiktok, _, _ = build_use_case([other_day_post])

    report = use_case.run(TODAY)

    assert ig.calls == []
    assert tiktok.calls == []
    assert report.results == []


def test_skips_already_published_platform_without_calling_publisher_again():
    post = make_post()
    use_case, ig, tiktok, log, _ = build_use_case([post])
    log.record_published(post, Platform.INSTAGRAM)

    report = use_case.run(TODAY)

    assert ig.calls == []  # not called - already logged
    assert tiktok.calls == [post]
    ig_result = next(r for r in report.results if r.platform is Platform.INSTAGRAM)
    assert ig_result.outcome is PostOutcome.PUBLISHED
    assert "already published" in ig_result.detail


def test_failure_on_one_platform_does_not_block_the_other_and_is_not_logged():
    post = make_post()
    use_case, ig, tiktok, log, _ = build_use_case([post], ig_fails=True)

    report = use_case.run(TODAY)

    assert report.had_failures
    assert (post.clip_id, Platform.INSTAGRAM) not in log.published
    assert (post.clip_id, Platform.TIKTOK) in log.published


def test_publisher_exception_is_captured_as_a_failed_result_not_raised():
    post = make_post()

    class ExplodingPublisher:
        platform = Platform.INSTAGRAM

        def publish(self, post):  # noqa: ANN001, ANN201
            raise RuntimeError("network is down")

    use_case, _, tiktok, log, _ = build_use_case([post])
    use_case.publishers[Platform.INSTAGRAM] = ExplodingPublisher()

    report = use_case.run(TODAY)

    ig_result = next(r for r in report.results if r.platform is Platform.INSTAGRAM)
    assert ig_result.outcome is PostOutcome.FAILED
    assert "network is down" in ig_result.error
