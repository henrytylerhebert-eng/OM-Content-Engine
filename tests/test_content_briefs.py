"""Tests for the internal content brief export."""

import json
from pathlib import Path

from src.reporting.content_briefs import (
    build_content_briefs,
    build_content_briefs_from_bundle,
    render_markdown_briefs,
    write_content_brief_outputs,
)
from src.reporting.demo_pipeline import build_demo_bundle


def test_brief_generation_from_planning_safe_candidate() -> None:
    bundle = build_demo_bundle()

    briefs = build_content_briefs_from_bundle(bundle)
    morgan = next(brief for brief in briefs if brief["primary_person_name"] == "Morgan Guide")

    assert morgan["brief_status"] == "planning_safe_only"
    assert morgan["suggested_angle"] == "ecosystem_proof"
    assert morgan["suggested_format"] == "mini_feature"
    assert morgan["public_ready"] is False
    assert "mentor" in morgan["core_story"].lower()


def test_public_ready_candidate_retains_public_ready_in_brief(tmp_path: Path) -> None:
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
    briefs = build_content_briefs_from_bundle(bundle)
    jane = next(
        brief
        for brief in briefs
        if brief["primary_person_name"] == "Jane Founder" and brief["entity_id"] == "person:jane_acme_ai"
    )

    assert jane["public_ready"] is True
    assert jane["brief_status"] == "public_ready"


def test_unresolved_high_risk_candidate_becomes_hold_for_review() -> None:
    bundle = build_demo_bundle()

    briefs = build_content_briefs_from_bundle(bundle)
    pelican = next(brief for brief in briefs if brief["org_name"] == "Pelican Robotics")

    assert pelican["brief_status"] == "hold_for_review"
    assert pelican["suggested_format"] == "internal_note"
    assert pelican["suggested_angle"] == "hold_for_review"


def test_guardrails_reflect_trust_limits() -> None:
    bundle = build_demo_bundle()

    briefs = build_content_briefs_from_bundle(bundle)
    morgan = next(brief for brief in briefs if brief["primary_person_name"] == "Morgan Guide")

    assert any("publication approval" in item.lower() for item in morgan["guardrails"])
    assert any("manual approval" in item.lower() for item in morgan["guardrails"])


def test_markdown_output_is_generated(tmp_path: Path) -> None:
    bundle = build_demo_bundle()
    snapshot = {
        "content_intelligence": bundle["content_intelligence"],
        "reporting_snapshot": bundle["reporting_snapshot"],
        "reviewed_truth": bundle["reviewed_truth"],
        "review_flags": bundle["review_rows"],
        "ecosystem_summary": bundle["ecosystem_summary"],
    }
    briefs = build_content_briefs(snapshot)

    markdown = render_markdown_briefs(briefs)
    written_paths = write_content_brief_outputs(briefs, tmp_path)

    assert markdown.startswith("# Content Brief Pack")
    assert "Core story:" in markdown
    assert {path.name for path in written_paths} == {"content_briefs.json", "content_briefs.md"}
    assert (tmp_path / "content_briefs.md").read_text(encoding="utf-8").startswith("# Content Brief Pack")
