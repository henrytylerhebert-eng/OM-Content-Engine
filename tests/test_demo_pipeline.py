"""Tests for the local sample-data demo pipeline."""

import json
from pathlib import Path

from src.reporting.demo_pipeline import build_demo_bundle, write_demo_outputs


def test_demo_bundle_builds_expected_sections() -> None:
    bundle = build_demo_bundle()

    assert bundle["raw_sources"]["active_members"]["row_count"] == 6
    assert bundle["raw_sources"]["mentors"]["row_count"] == 3
    assert bundle["raw_sources"]["cohorts"]["row_count"] == 4
    assert len(bundle["normalized"]["organizations"]) == 6
    assert len(bundle["normalized"]["mentor_profiles"]) == 3
    assert len(bundle["normalized"]["participations"]) == 4
    assert bundle["ecosystem_summary"]["organization_count"] == 6
    assert bundle["ecosystem_summary"]["mentor_profile_count"] == 3
    assert bundle["ecosystem_summary"]["participation_count"] == 4
    assert bundle["reporting_snapshot"]["active_mentor_summary"][0]["count"] == 3
    assert any(
        row["flag_code"] == "review_multi_value_cohort_parse"
        for row in bundle["review_rows"]
    )
    assert any(
        row["flag_code"] == "review_participation_link_unresolved"
        for row in bundle["review_rows"]
    )
    assert all("," not in str(row["cohort_name"]) for row in bundle["normalized"]["cohorts"])
    assert all("," not in str(row["cohort_name"]) for row in bundle["normalized"]["participations"])


def test_demo_bundle_prefers_explicit_cohort_source_when_reconciling_duplicates() -> None:
    bundle = build_demo_bundle()

    participations = bundle["normalized"]["participations"]
    acme_participation = next(
        record
        for record in participations
        if record["organization_id"] == "org:rec_member_001" and record["cohort_id"] == "cohort:spring_2026"
    )

    assert acme_participation["participation_origin"] == "explicit_cohort"
    assert {entry["source_table"] for entry in acme_participation["source_provenance"]} == {
        "Active Members",
        "Cohorts",
    }


def test_demo_outputs_are_written_to_disk(tmp_path: Path) -> None:
    bundle = build_demo_bundle()

    written_paths = write_demo_outputs(bundle, tmp_path)

    expected_files = {
        "normalized_bundle.json",
        "reviewed_truth.json",
        "review_flags.json",
        "content_intelligence.json",
        "content_candidates.json",
        "content_candidates.csv",
        "content_briefs.json",
        "content_briefs.md",
        "editorial_plan.json",
        "editorial_plan.md",
        "editorial_assignments.json",
        "editorial_assignments.md",
        "editorial_assignments.csv",
        "weekly_export_summary.md",
        "reporting_snapshot.json",
        "ecosystem_summary.json",
        "ecosystem_report.md",
        "snapshot_manifest.json",
    }
    assert {path.name for path in written_paths} == expected_files
    assert (tmp_path / "ecosystem_report.md").read_text(encoding="utf-8").startswith("# Ecosystem Report")

    manifest = json.loads((tmp_path / "snapshot_manifest.json").read_text(encoding="utf-8"))
    assert manifest["snapshot_name"] == tmp_path.name
    assert manifest["raw_sources"]["active_members"]["row_count"] == 6
    assert manifest["summary"]["organization_count"] == 6
    assert {artifact["file_name"] for artifact in manifest["artifacts"]} == expected_files
    assert (tmp_path / "content_candidates.csv").read_text(encoding="utf-8").startswith("entity_id,")
    assert "content_ready_people" in manifest["reporting_sections"]
