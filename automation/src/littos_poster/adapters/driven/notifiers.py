from __future__ import annotations

import os
import sys
from dataclasses import dataclass

from ...domain.models import PostOutcome, RunReport


@dataclass
class ConsoleNotifier:
    """Prints a summary to stdout/stderr. Also writes to
    GITHUB_STEP_SUMMARY when running inside GitHub Actions, so the run
    summary page shows exactly what happened without extra integrations.

    A failed post does NOT raise here - the CLI entrypoint is responsible
    for turning RunReport.had_failures into a non-zero exit code, which is
    what makes GitHub Actions mark the run red and email the owner. That is
    the whole "notify the owner on failure" mechanism: no bot, no webhook,
    just GitHub's own built-in workflow-failure notification.
    """

    def notify_run_complete(self, report: RunReport) -> None:
        lines = [self._render_line(r) for r in report.results]
        text = "\n".join(lines) if lines else "(nothing due today)"
        print(text, file=sys.stdout if not report.had_failures else sys.stderr)

        summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary_path:
            with open(summary_path, "a", encoding="utf-8") as fh:
                fh.write("## LITTOS social publish run\n\n")
                for r in report.results:
                    fh.write(f"- {self._render_line(r)}\n")
                if not report.results:
                    fh.write("- nothing due today\n")

    @staticmethod
    def _render_line(r) -> str:  # noqa: ANN001
        if r.outcome is PostOutcome.FAILED:
            return f"FAILED  {r.post.clip_id} -> {r.platform.value}: {r.error}"
        if r.outcome is PostOutcome.QUEUED_FOR_MANUAL_STEP:
            return f"MANUAL  {r.post.clip_id} -> {r.platform.value}: {r.detail}"
        return f"OK      {r.post.clip_id} -> {r.platform.value}: {r.detail}"
