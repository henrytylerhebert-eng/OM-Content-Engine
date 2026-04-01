"""Build a compact weekly export summary from downstream planning outputs."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

from src.reporting.editorial_assignments import (
    OUTPUT_JSON_NAME as EDITORIAL_ASSIGNMENTS_JSON_NAME,
)
from src.reporting.editorial_plan import (
    OUTPUT_JSON_NAME as EDITORIAL_PLAN_JSON_NAME,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN_DIR = REPO_ROOT / "data" / "processed" / "local_run"
OUTPUT_MARKDOWN_NAME = "weekly_export_summary.md"
DEFAULT_TOP_BLOCKERS = 5


def _load_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _utc_timestamp() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _normalized_text(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def build_weekly_export_summary(
    editorial_plan: dict[str, object],
    assignments: Sequence[dict[str, object]],
    review_rows: Sequence[dict[str, object]],
    *,
    top_n: int = DEFAULT_TOP_BLOCKERS,
) -> dict[str, object]:
    """Build a compact weekly summary from existing downstream outputs."""

    status_counts = Counter(str(row.get("assignment_status") or "unassigned") for row in assignments)
    blocker_counts = Counter(str(row.get("flag_code") or "") for row in review_rows if str(row.get("flag_code") or ""))
    top_blockers: list[dict[str, object]] = []
    for flag_code, count in blocker_counts.most_common(top_n):
        sample = next(
            (row for row in review_rows if str(row.get("flag_code") or "") == flag_code),
            {},
        )
        top_blockers.append(
            {
                "flag_code": flag_code,
                "count": count,
                "severity": sample.get("severity"),
                "recommended_action": sample.get("recommended_action"),
            }
        )

    return {
        "generated_at": _utc_timestamp(),
        "use_now_count": int(editorial_plan.get("bucket_counts", {}).get("use_now", 0)),
        "needs_review_count": int(editorial_plan.get("bucket_counts", {}).get("needs_review", 0)),
        "assignment_status_counts": dict(status_counts),
        "top_unresolved_review_blockers": top_blockers,
    }


def render_weekly_export_summary(summary: dict[str, object]) -> str:
    """Render a compact operator-friendly markdown summary."""

    lines = [
        "# Weekly Export Summary",
        "",
        "- Run date: `%s`" % summary.get("generated_at"),
        "- Total use_now items: `%s`" % summary.get("use_now_count", 0),
        "- Total needs_review items: `%s`" % summary.get("needs_review_count", 0),
        "",
        "## Assignment Status",
        "",
    ]

    status_counts = dict(summary.get("assignment_status_counts", {}))
    if not status_counts:
        lines.append("_No assignments found._")
        lines.append("")
    else:
        for status, count in sorted(status_counts.items()):
            lines.append("- `%s`: `%s`" % (status, count))
        lines.append("")

    lines.append("## Top Unresolved Review Blockers")
    lines.append("")
    blockers = list(summary.get("top_unresolved_review_blockers", []))
    if not blockers:
        lines.append("_No unresolved review blockers found._")
        lines.append("")
    else:
        for blocker in blockers:
            lines.append("### %s" % blocker.get("flag_code"))
            lines.append("")
            lines.append("- Count: `%s`" % blocker.get("count", 0))
            severity = _normalized_text(blocker.get("severity"))
            if severity:
                lines.append("- Severity: `%s`" % severity)
            action = _normalized_text(blocker.get("recommended_action"))
            if action:
                lines.append("- Recommended action: %s" % action)
            lines.append("")
    return "\n".join(lines).strip() + "\n"


def write_weekly_export_summary(
    editorial_plan: dict[str, object],
    assignments: Sequence[dict[str, object]],
    review_rows: Sequence[dict[str, object]],
    run_dir: Path,
) -> Path:
    """Write the weekly summary markdown into an existing run directory."""

    run_dir.mkdir(parents=True, exist_ok=True)
    summary = build_weekly_export_summary(editorial_plan, assignments, review_rows)
    path = run_dir / OUTPUT_MARKDOWN_NAME
    path.write_text(render_weekly_export_summary(summary), encoding="utf-8")
    return path


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Build a weekly export summary from an existing run directory."""

    parser = argparse.ArgumentParser(description="Build a weekly export summary from an existing run directory.")
    parser.add_argument(
        "--run-dir",
        default=str(DEFAULT_RUN_DIR),
        help="Run directory containing editorial_plan.json, editorial_assignments.json, and review_flags.json.",
    )
    args = parser.parse_args(argv)

    run_dir = Path(args.run_dir)
    editorial_plan = dict(_load_json(run_dir / EDITORIAL_PLAN_JSON_NAME))
    assignments = list(_load_json(run_dir / EDITORIAL_ASSIGNMENTS_JSON_NAME))
    review_rows = list(_load_json(run_dir / "review_flags.json"))
    path = write_weekly_export_summary(editorial_plan, assignments, review_rows, run_dir)

    print("Wrote weekly export summary:")
    print("- %s" % path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
