"""Tests for the compact weekly export summary."""

from pathlib import Path

from src.reporting.demo_pipeline import build_demo_bundle
from src.reporting.content_briefs import build_content_briefs_from_bundle
from src.reporting.editorial_assignments import build_assignments
from src.reporting.editorial_plan import build_plan
from src.reporting.weekly_export_summary import (
    build_weekly_export_summary,
    render_weekly_export_summary,
    write_weekly_export_summary,
)


def test_weekly_export_summary_uses_existing_downstream_outputs() -> None:
    bundle = build_demo_bundle()
    editorial_plan = build_plan(build_content_briefs_from_bundle(bundle))
    assignments = build_assignments(editorial_plan)

    summary = build_weekly_export_summary(editorial_plan, assignments, bundle["review_rows"])

    assert summary["use_now_count"] == editorial_plan["bucket_counts"]["use_now"]
    assert summary["needs_review_count"] == editorial_plan["bucket_counts"]["needs_review"]
    assert summary["assignment_status_counts"]["not_started"] >= 1
    assert summary["top_unresolved_review_blockers"][0]["flag_code"] == "review_missing_content_assets"


def test_weekly_export_summary_markdown_is_written(tmp_path: Path) -> None:
    bundle = build_demo_bundle()
    editorial_plan = build_plan(build_content_briefs_from_bundle(bundle))
    assignments = build_assignments(editorial_plan)

    path = write_weekly_export_summary(editorial_plan, assignments, bundle["review_rows"], tmp_path)
    markdown = render_weekly_export_summary(
        build_weekly_export_summary(editorial_plan, assignments, bundle["review_rows"])
    )

    assert path.name == "weekly_export_summary.md"
    assert path.read_text(encoding="utf-8") == markdown
    assert markdown.startswith("# Weekly Export Summary")
    assert "## Assignment Status" in markdown
    assert "## Top Unresolved Review Blockers" in markdown
