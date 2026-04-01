"""Tests for the reviewed-truth override layer."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.reporting.demo_pipeline import build_demo_bundle
from src.review.reviewed_truth import (
    apply_content_bundle_overrides,
    apply_normalized_overrides,
    apply_review_row_overrides,
    build_reviewed_truth_artifact,
    load_override_document,
)


def _write_override_file(tmp_path: Path, payload: dict[str, object]) -> Path:
    path = tmp_path / "overrides.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def test_reviewed_truth_supports_common_override_cases(tmp_path: Path) -> None:
    overrides_path = _write_override_file(
        tmp_path,
        {
            "version": 1,
            "rules": [
                {
                    "id": "fix-org-type",
                    "target": "organizations",
                    "match": {"source_record_id": "rec_org_1"},
                    "set": {"org_type": "startup"},
                },
                {
                    "id": "mark-internal",
                    "target": "organizations",
                    "match": {"source_record_id": "rec_org_2"},
                    "set": {"org_type": "internal"},
                },
                {
                    "id": "suppress-grouped-person",
                    "target": "people",
                    "match": {
                        "source_record_id": "rec_person_1",
                        "person_resolution_basis": "semi_structured_member_side",
                    },
                    "suppress": True,
                },
                {
                    "id": "confirm-semi-structured-person",
                    "target": "people",
                    "match": {
                        "source_record_id": "rec_person_2",
                        "person_resolution_basis": "semi_structured_member_side",
                    },
                    "set": {},
                },
                {
                    "id": "designate-spokesperson",
                    "target": "affiliations",
                    "match": {"id": "aff:1"},
                    "set": {"spokesperson_flag": True},
                },
                {
                    "id": "confirm-content-use",
                    "target": "organization_content",
                    "match": {"linked_organization_id": "org:1"},
                    "set": {
                        "content_eligible": True,
                        "content_ready": True,
                        "externally_publishable": True,
                    },
                },
                {
                    "id": "deny-person-content-use",
                    "target": "person_content",
                    "match": {"linked_person_id": "person:2"},
                    "set": {"content_eligible": False, "content_ready": False},
                },
                {
                    "id": "confirm-person-spotlight",
                    "target": "person_content",
                    "match": {"linked_person_id": "person:3"},
                    "set": {"spotlight_ready": True, "story_type": "speaker_profile"},
                },
                {
                    "id": "resolve-cohort-identity",
                    "target": "cohorts",
                    "match": {"id": "cohort:1"},
                    "set": {"cohort_name": "Builder Fall 2025"},
                },
                {
                    "id": "resolve-participation-status",
                    "target": "participations",
                    "match": {"id": "part:1"},
                    "set": {"participation_status": "withdrawn"},
                },
                {
                    "id": "suppress-resolved-review-row",
                    "target": "review_rows",
                    "match": {
                        "source_record_id": "rec_org_1",
                        "flag_code": "review_missing_org_type",
                    },
                    "suppress": True,
                },
            ],
        },
    )

    override_document = load_override_document(overrides_path)
    normalized = {
        "organizations": [
            {"id": "org:1", "source_record_id": "rec_org_1", "name": "Bayou Build", "org_type": "unknown"},
            {"id": "org:2", "source_record_id": "rec_org_2", "name": "OM Internal", "org_type": "partner"},
        ],
        "people": [
            {
                "id": "person:1",
                "source_record_id": "rec_person_1",
                "full_name": "Founder Team",
                "person_resolution_basis": "semi_structured_member_side",
            },
            {
                "id": "person:2",
                "source_record_id": "rec_person_2",
                "full_name": "Dana Voice",
                "person_resolution_basis": "semi_structured_member_side",
            },
        ],
        "affiliations": [{"id": "aff:1", "person_id": "person:2", "organization_id": "org:1", "spokesperson_flag": False}],
        "programs": [],
        "cohorts": [{"id": "cohort:1", "cohort_name": "Fall 2025,Dropout"}],
        "participations": [{"id": "part:1", "organization_id": "org:1", "cohort_id": "cohort:1", "participation_status": "active"}],
        "mentor_profiles": [],
    }
    reviewed_normalized, normalized_applications = apply_normalized_overrides(normalized, override_document)

    reviewed_org_1 = next(record for record in reviewed_normalized["organizations"] if record["id"] == "org:1")
    reviewed_org_2 = next(record for record in reviewed_normalized["organizations"] if record["id"] == "org:2")
    reviewed_person_2 = next(record for record in reviewed_normalized["people"] if record["id"] == "person:2")
    reviewed_affiliation = reviewed_normalized["affiliations"][0]
    reviewed_cohort = reviewed_normalized["cohorts"][0]
    reviewed_participation = reviewed_normalized["participations"][0]

    assert reviewed_org_1["org_type"] == "startup"
    assert reviewed_org_2["org_type"] == "internal"
    assert [record["id"] for record in reviewed_normalized["people"]] == ["person:2"]
    assert reviewed_person_2["reviewed_truth_applied"] is True
    assert "confirm-semi-structured-person" in reviewed_person_2["reviewed_override_ids"]
    assert reviewed_affiliation["spokesperson_flag"] is True
    assert reviewed_cohort["cohort_name"] == "Builder Fall 2025"
    assert reviewed_participation["participation_status"] == "withdrawn"

    content_bundle = {
        "organizations": [
            {
                "linked_organization_id": "org:1",
                "content_eligible": False,
                "content_ready": False,
                "externally_publishable": False,
            }
        ],
        "people": [
            {
                "linked_person_id": "person:2",
                "content_eligible": True,
                "content_ready": True,
                "externally_publishable": False,
            },
            {
                "linked_person_id": "person:3",
                "content_eligible": True,
                "content_ready": True,
                "spotlight_ready": False,
                "story_type": "profile",
                "externally_publishable": False,
            }
        ],
        "review_rows": [],
    }
    reviewed_content_bundle, content_applications = apply_content_bundle_overrides(content_bundle, override_document)
    assert reviewed_content_bundle["organizations"][0]["content_eligible"] is True
    assert reviewed_content_bundle["organizations"][0]["content_ready"] is True
    assert reviewed_content_bundle["organizations"][0]["externally_publishable"] is True
    assert reviewed_content_bundle["people"][0]["content_eligible"] is False
    assert reviewed_content_bundle["people"][0]["content_ready"] is False
    assert reviewed_content_bundle["people"][0]["externally_publishable"] is False
    assert reviewed_content_bundle["people"][1]["spotlight_ready"] is True
    assert reviewed_content_bundle["people"][1]["story_type"] == "speaker_profile"

    raw_review_rows = [
        {
            "source_table": "Active Members",
            "source_record_id": "rec_org_1",
            "flag_code": "review_missing_org_type",
            "severity": "medium",
        },
        {
            "source_table": "Active Members",
            "source_record_id": "rec_person_1",
            "flag_code": "review_grouped_record_detected",
            "severity": "medium",
        },
    ]
    reviewed_review_rows, review_row_applications = apply_review_row_overrides(raw_review_rows, override_document)
    assert len(reviewed_review_rows) == 1
    assert reviewed_review_rows[0]["flag_code"] == "review_grouped_record_detected"

    reviewed_truth = build_reviewed_truth_artifact(
        override_document=override_document,
        reviewed_collections=reviewed_normalized,
        review_rows=reviewed_review_rows,
        applications=normalized_applications + content_applications + review_row_applications,
    )
    assert reviewed_truth["rule_count"] == 11
    assert reviewed_truth["applied_rule_count"] == 11


def test_reviewed_truth_rejects_externally_publishable_on_non_content_targets(tmp_path: Path) -> None:
    overrides_path = _write_override_file(
        tmp_path,
        {
            "version": 1,
            "rules": [
                {
                    "id": "bad-external-flag",
                    "target": "people",
                    "match": {"source_record_id": "rec_person_2"},
                    "set": {"externally_publishable": True},
                }
            ],
        },
    )

    with pytest.raises(ValueError, match="externally publishable decisions"):
        load_override_document(overrides_path)


def test_demo_pipeline_preserves_normalized_truth_and_uses_reviewed_truth_downstream(tmp_path: Path) -> None:
    overrides_path = _write_override_file(
        tmp_path,
        {
            "version": 1,
            "rules": [
                {
                    "id": "fix-bayou-org-type",
                    "target": "organizations",
                    "match": {"source_record_id": "rec_member_004"},
                    "set": {"org_type": "service_provider"},
                },
                {
                    "id": "promote-riley-profile",
                    "target": "people",
                    "match": {"id": "person:riley_gcmn_org"},
                    "set": {
                        "bio": "Partner ecosystem connector for manufacturing founders.",
                        "linkedin": "https://linkedin.com/in/rileypartner",
                        "public_facing_ready": True,
                        "speaker_ready": True,
                    },
                },
                {
                    "id": "suppress-bayou-org-flag",
                    "target": "review_rows",
                    "match": {
                        "source_record_id": "rec_member_004",
                        "flag_code": "review_missing_org_type",
                    },
                    "suppress": True,
                },
                {
                    "id": "approve-riley-for-public-use",
                    "target": "person_content",
                    "match": {"linked_person_id": "person:riley_gcmn_org"},
                    "set": {"externally_publishable": True},
                },
            ],
        },
    )

    bundle = build_demo_bundle(overrides_path=overrides_path)

    raw_bayou = next(
        organization
        for organization in bundle["normalized"]["organizations"]
        if organization["source_record_id"] == "rec_member_004"
    )
    reviewed_bayou = next(
        organization
        for organization in bundle["reviewed_truth"]["collections"]["organizations"]
        if organization["source_record_id"] == "rec_member_004"
    )

    assert raw_bayou["org_type"] == "unknown"
    assert reviewed_bayou["org_type"] == "service_provider"
    assert "fix-bayou-org-type" in reviewed_bayou["reviewed_override_ids"]

    assert not any(
        row["source_record_id"] == "rec_member_004" and row["flag_code"] == "review_missing_org_type"
        for row in bundle["review_rows"]
    )

    active_org_rows = bundle["reporting_snapshot"]["active_organizations_by_type"]
    assert {"org_type": "service_provider", "count": 1} in active_org_rows
    assert any(row["full_name"] == "Riley Partner" for row in bundle["reporting_snapshot"]["content_ready_people"])
    reviewed_riley = next(
        person
        for person in bundle["content_intelligence"]["people"]
        if person["linked_person_id"] == "person:riley_gcmn_org"
    )
    assert reviewed_riley["externally_publishable"] is True
