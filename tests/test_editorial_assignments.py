"""Tests for the weekly editorial assignment tracker."""

import json
from pathlib import Path

from src.reporting.content_briefs import build_content_briefs_from_bundle
from src.reporting.demo_pipeline import build_demo_bundle
from src.reporting.editorial_assignments import (
    build_assignments,
    render_assignment_markdown,
    summarize_assignments,
    write_assignment_outputs,
)
from src.reporting.editorial_plan import build_plan


def _build_demo_assignments() -> list[dict[str, object]]:
    bundle = build_demo_bundle()
    plan = build_plan(build_content_briefs_from_bundle(bundle))
    return build_assignments(plan)


def test_use_now_item_becomes_default_assignment(tmp_path: Path) -> None:
    overrides_path = tmp_path / "overrides.json"
    overrides_path.write_text(
        json.dumps(
            {
                "version": 1,
                "rules": [
                    {
                        "id": "review-morgan-internal",
                        "target": "person_content",
                        "match": {
                            "linked_person_id": "person:morgan_example_com",
                        },
                        "set": {
                            "content_eligible": True,
                        },
                        "reason": "Reviewed for internal planning use.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    bundle = build_demo_bundle(overrides_path=overrides_path)
    plan = build_plan(build_content_briefs_from_bundle(bundle))
    assignments = build_assignments(plan)
    morgan = next(row for row in assignments if row["entity_id"] == "person:morgan_example_com")

    assert morgan["bucket"] == "use_now"
    assert morgan["target_cycle"] == "this_week"
    assert morgan["assignment_status"] == "not_started"
    assert morgan["priority"] == "high"


def test_needs_review_item_gets_review_oriented_next_step() -> None:
    assignments = _build_demo_assignments()
    delta = next(row for row in assignments if row["entity_id"] == "org:rec_member_006")

    assert delta["bucket"] == "needs_review"
    assert delta["next_step"] == "resolve_review_flag"
    assert "review_multi_value_cohort_parse" in delta["blocking_notes"]


def test_hold_items_are_not_included_by_default() -> None:
    assignments = _build_demo_assignments()

    assert all(row["bucket"] != "hold" for row in assignments)
    assert all(row["entity_id"] != "org:rec_member_003" for row in assignments)


def test_markdown_output_is_generated(tmp_path: Path) -> None:
    assignments = _build_demo_assignments()
    markdown = render_assignment_markdown(assignments)
    written_paths = write_assignment_outputs(assignments, tmp_path)

    assert markdown.startswith("# Editorial Assignments")
    assert "## This Week" in markdown
    assert "## Review Work" in markdown
    assert {path.name for path in written_paths} == {
        "editorial_assignments.json",
        "editorial_assignments.md",
        "editorial_assignments.csv",
    }


def test_assignment_summary_counts_are_reported() -> None:
    assignments = _build_demo_assignments()
    summary = summarize_assignments(assignments)

    assert summary["total_assignments"] == len(assignments)
    assert summary["bucket_counts"]["needs_review"] >= 1
    assert summary["target_cycle_counts"]["next_week"] >= 1
    assert summary["review_work_count"] >= 1
