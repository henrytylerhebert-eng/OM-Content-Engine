"""Tests for the weekly editorial planning pack."""

import json
from pathlib import Path

from src.reporting.content_briefs import build_content_briefs_from_bundle
from src.reporting.editorial_plan import build_plan, render_markdown_plan, write_outputs
from src.reporting.demo_pipeline import build_demo_bundle


def test_public_ready_brief_always_goes_to_use_now(tmp_path: Path) -> None:
    overrides_path = tmp_path / "overrides.json"
    overrides_path.write_text(
        json.dumps(
            {
                "version": 1,
                "rules": [
                    {
                        "id": "approve-jane-public",
                        "target": "person_content",
                        "match": {
                            "linked_person_id": "person:jane_acme_ai",
                        },
                        "set": {
                            "externally_publishable": True,
                        },
                        "reason": "Approved for public-facing packaging.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    bundle = build_demo_bundle(overrides_path=overrides_path)
    plan = build_plan(build_content_briefs_from_bundle(bundle))

    jane = next(
        row
        for row in plan["use_now"]
        if row["entity_id"] == "person:jane_acme_ai"
    )

    assert jane["brief_status"] == "public_ready"
    assert jane["recommended_action"] == "draft_this"


def test_reviewed_internal_brief_goes_to_use_now(tmp_path: Path) -> None:
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

    morgan = next(
        row
        for row in plan["use_now"]
        if row["entity_id"] == "person:morgan_example_com"
    )

    assert morgan["brief_status"] == "reviewed_for_internal_use"
    assert morgan["recommended_action"] == "assign_owner"


def test_planning_safe_only_brief_goes_to_needs_review() -> None:
    bundle = build_demo_bundle()
    plan = build_plan(build_content_briefs_from_bundle(bundle))

    alex = next(
        row
        for row in plan["needs_review"]
        if row["entity_id"] == "person:alex_acme_ai"
    )

    assert alex["brief_status"] == "planning_safe_only"
    assert alex["recommended_action"] == "apply_reviewed_truth_override"


def test_hold_for_review_brief_goes_to_hold() -> None:
    bundle = build_demo_bundle()
    plan = build_plan(build_content_briefs_from_bundle(bundle))

    pelican = next(
        row
        for row in plan["hold"]
        if row["entity_id"] == "org:rec_member_003"
    )

    assert pelican["brief_status"] == "hold_for_review"
    assert pelican["recommended_action"] == "requires_structural_fix"
    assert "review burden" in pelican["reason"]


def test_markdown_output_is_generated(tmp_path: Path) -> None:
    bundle = build_demo_bundle()
    plan = build_plan(build_content_briefs_from_bundle(bundle))

    markdown = render_markdown_plan(plan)
    written_paths = write_outputs(plan, tmp_path)

    assert markdown.startswith("# Weekly Editorial Plan")
    assert "## Use Now" in markdown
    assert "## Needs Review" in markdown
    assert "## Hold" in markdown
    assert {path.name for path in written_paths} == {"editorial_plan.json", "editorial_plan.md"}
