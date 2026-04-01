"""Tests for the internal content candidate export."""

import json
from pathlib import Path

from src.reporting.content_candidates import build_content_candidates, build_content_candidates_from_bundle
from src.reporting.demo_pipeline import build_demo_bundle


def test_spotlight_ready_records_are_included_for_internal_planning() -> None:
    bundle = build_demo_bundle()

    candidates = build_content_candidates_from_bundle(bundle)
    labels = {(row["record_type"], row["org_name"], row["primary_person_name"]) for row in candidates}

    assert ("organization", "Acme AI", "Jane Founder") in labels
    assert ("person", "Acme AI", "Jane Founder") in labels
    assert ("person", None, "Morgan Guide") in labels


def test_reviewed_truth_backed_record_can_enter_candidates_without_becoming_public_ready(tmp_path: Path) -> None:
    overrides_path = tmp_path / "overrides.json"
    overrides_path.write_text(
        json.dumps(
            {
                "version": 1,
                "rules": [
                    {
                        "id": "confirm-riley-for-planning",
                        "target": "person_content",
                        "match": {
                            "linked_person_id": "person:riley_gcmn_org",
                        },
                        "set": {},
                        "reason": "Keep Riley in planning exports after manual review.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    bundle = build_demo_bundle(overrides_path=overrides_path)
    candidates = build_content_candidates_from_bundle(bundle)

    riley = next(
        row
        for row in candidates
        if row["record_type"] == "person" and row["primary_person_name"] == "Riley Partner"
    )

    assert riley["reviewed_truth_applied"] is True
    assert riley["readiness_level"] == "internally_usable"
    assert riley["planning_safe"] is True
    assert riley["public_ready"] is False
    assert riley["suggested_use"] == "hold_for_review"


def test_internal_and_untrusted_records_stay_out_of_candidate_export() -> None:
    bundle = build_demo_bundle()

    candidates = build_content_candidates_from_bundle(bundle)
    labels = {row["org_name"] or row["primary_person_name"] for row in candidates}

    assert "Opportunity Machine Internal Ops" not in labels
    assert "Taylor Staff" not in labels
    assert "Jordan Sparse" not in labels


def test_public_ready_requires_explicit_reviewed_truth(tmp_path: Path) -> None:
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
    candidates = build_content_candidates_from_bundle(bundle)

    jane = next(row for row in candidates if row["primary_person_name"] == "Jane Founder")
    morgan = next(row for row in candidates if row["primary_person_name"] == "Morgan Guide")

    assert jane["planning_safe"] is True
    assert jane["public_ready"] is True
    assert jane["trust_basis"] == "human_approved"
    assert morgan["planning_safe"] is True
    assert morgan["public_ready"] is False


def test_build_content_candidates_from_snapshot_inputs_matches_bundle_shape() -> None:
    bundle = build_demo_bundle()
    snapshot = {
        "content_intelligence": bundle["content_intelligence"],
        "reporting_snapshot": bundle["reporting_snapshot"],
        "reviewed_truth": bundle["reviewed_truth"],
        "review_flags": bundle["review_rows"],
        "ecosystem_summary": bundle["ecosystem_summary"],
    }

    candidates = build_content_candidates(snapshot)

    assert all("why_it_matters" in row for row in candidates)
    assert all("supporting_evidence_summary" in row for row in candidates)
    assert all("review_flag_summary" in row for row in candidates)
