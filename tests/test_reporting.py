"""Tests for the first-pass reporting outputs."""

from src.enrich.content_intelligence import build_content_intelligence_bundle
from src.reporting.ecosystem_reports import (
    build_reporting_snapshot,
    render_csv_section,
    render_markdown_report,
    report_active_mentor_summary,
    report_active_people_by_source_path,
    report_internally_usable_people,
    report_missing_content_asset_counts,
    report_mentor_derived_people,
    report_organizations_by_cohort,
    report_readiness_trust_summary,
    report_review_burden_by_flag,
    report_review_needed_people_candidates,
    report_semi_structured_auto_created_people,
    report_spotlight_ready_people,
    report_structured_people,
)


def _sample_reporting_data() -> dict:
    organizations = [
        {
            "id": 1,
            "name": "Acme AI",
            "org_type": "startup",
            "active_flag": True,
            "membership_tier": "Builder Plus",
            "website": "https://acme.ai",
            "description": "Workflow software for industrial teams.",
            "content_eligible": True,
            "spotlight_priority": 50,
            "reviewed_truth_applied": True,
            "reviewed_override_ids": ["fix-acme-profile"],
            "source_record_id": "rec_org_001",
            "source_system": "airtable_export",
        },
        {
            "id": 2,
            "name": "Gulf Partner",
            "org_type": "partner",
            "active_flag": True,
            "membership_tier": "Partner",
            "description": "Regional ecosystem partner.",
            "website": "https://partner.org",
            "source_record_id": "rec_org_002",
            "source_system": "airtable_export",
        },
        {
            "id": 3,
            "name": "Dormant Startup",
            "org_type": "startup",
            "active_flag": False,
            "membership_tier": "Builder Plus",
            "source_record_id": "rec_org_003",
            "source_system": "airtable_export",
        },
        {
            "id": 4,
            "name": "Lean Service",
            "org_type": "service_provider",
            "active_flag": True,
            "membership_tier": "Standard",
            "description": "Fractional operations support for founders.",
            "industry": "Operations",
            "source_record_id": "rec_org_004",
            "source_system": "airtable_export",
        },
        {
            "id": 5,
            "name": "Quiet Partner",
            "org_type": "partner",
            "active_flag": True,
            "membership_tier": "Associate",
            "headquarters_location": "Baton Rouge, LA",
            "source_record_id": "rec_org_005",
            "source_system": "airtable_export",
        },
    ]
    people = [
        {
            "id": 10,
            "full_name": "Morgan Local",
            "person_type": "mentor",
            "active_flag": True,
            "bio": "AI mentor for founders.",
            "expertise_tags": "AI, Go-to-market",
            "location": "Lafayette, LA",
            "speaker_ready": True,
            "person_resolution_basis": "structured_field",
            "source_record_id": "rec_person_010",
            "source_system": "airtable_export",
        },
        {
            "id": 11,
            "full_name": "Priya Founder",
            "person_type": "founder",
            "active_flag": True,
            "bio": "Founder building an AI operations startup.",
            "headshot_url": "https://example.com/priya.jpg",
            "person_resolution_basis": "structured_field",
            "reviewed_truth_applied": True,
            "reviewed_override_ids": ["confirm-priya-founder"],
            "source_record_id": "rec_person_011",
            "source_system": "airtable_export",
        },
        {
            "id": 12,
            "full_name": "Taylor Remote",
            "person_type": "mentor",
            "active_flag": True,
            "bio": "Remote mentor.",
            "expertise_tags": "Operations",
            "location": "Houston, TX",
            "person_resolution_basis": "structured_field",
            "source_record_id": "rec_person_012",
            "source_system": "airtable_export",
        },
        {
            "id": 13,
            "full_name": "Dana Planner",
            "person_type": "operator",
            "active_flag": True,
            "email": "dana@example.com",
            "person_resolution_basis": "semi_structured_member_side",
            "source_record_id": "rec_person_013",
            "source_system": "airtable_export",
        },
    ]
    mentor_profiles = [
        {"person_id": 10, "mentor_active_flag": True, "mentor_location_type": "local"},
        {"person_id": 12, "mentor_active_flag": True, "mentor_location_type": "remote"},
    ]
    affiliations = [{"person_id": 11, "organization_id": 1, "founder_flag": True}]
    cohorts = [
        {"id": 100, "cohort_name": "Builder Spring 2026", "active_flag": True},
        {"id": 101, "cohort_name": "Builder Fall 2024", "active_flag": False},
    ]
    participations = [
        {"organization_id": 1, "cohort_id": 100, "participation_status": "active"},
        {"organization_id": 2, "cohort_id": 101, "participation_status": "alumni"},
    ]
    review_rows = [
        {
            "source_table": "Active Members",
            "source_record_id": "rec_org_999",
            "flag_code": "review_missing_org_type",
            "severity": "medium",
            "record_label": "Unknown Org",
            "note": None,
        },
        {
            "source_table": "Active Members",
            "source_record_id": "rec_person_013",
            "flag_code": "review_member_side_person_generic_email",
            "severity": "medium",
            "record_label": "Dana Planner",
            "source_field": "Email",
            "note": "Example member-side person review row.",
        },
    ]
    return {
        "organizations": organizations,
        "people": people,
        "mentor_profiles": mentor_profiles,
        "affiliations": affiliations,
        "participations": participations,
        "cohorts": cohorts,
        "review_rows": review_rows,
    }


def test_active_mentor_summary_counts_local_and_non_local() -> None:
    sample = _sample_reporting_data()

    rows = report_active_mentor_summary(sample["people"], sample["mentor_profiles"])

    assert rows == [
        {"metric": "active_mentors", "count": 2},
        {"metric": "local_mentors", "count": 1},
        {"metric": "non_local_mentors", "count": 1},
    ]


def test_people_provenance_reports_cover_structured_semi_structured_and_mentor_paths() -> None:
    sample = _sample_reporting_data()

    count_rows = report_active_people_by_source_path(sample["people"])
    structured_rows = report_structured_people(sample["people"])
    semi_structured_rows = report_semi_structured_auto_created_people(sample["people"])
    mentor_rows = report_mentor_derived_people(sample["people"])

    assert {
        "person_source_path": "structured_member_fields",
        "count": 1,
        "reviewed_truth_backed_count": 1,
        "source_derived_count": 0,
    } in count_rows
    assert {
        "person_source_path": "semi_structured_member_side",
        "count": 1,
        "reviewed_truth_backed_count": 0,
        "source_derived_count": 1,
    } in count_rows
    assert {
        "person_source_path": "mentor_structured",
        "count": 2,
        "reviewed_truth_backed_count": 0,
        "source_derived_count": 2,
    } in count_rows
    assert [row["full_name"] for row in structured_rows] == ["Priya Founder"]
    assert [row["full_name"] for row in semi_structured_rows] == ["Dana Planner"]
    assert [row["full_name"] for row in mentor_rows] == ["Morgan Local", "Taylor Remote"]
    assert structured_rows[0]["review_state"] == "reviewed_truth_backed"
    assert structured_rows[0]["reviewed_override_count"] == 1


def test_review_needed_people_candidates_filters_person_creation_flags() -> None:
    rows = report_review_needed_people_candidates(
        [
            {
                "source_table": "Active Members",
                "source_record_id": "rec_member_201",
                "flag_code": "review_member_side_person_generic_email",
                "severity": "medium",
                "record_label": "Signal Works",
                "source_field": "Email",
                "note": None,
            },
            {
                "source_table": "Active Members",
                "source_record_id": "rec_member_202",
                "flag_code": "review_missing_org_type",
                "severity": "medium",
                "record_label": "Unknown Org",
                "source_field": "Member Type",
                "note": None,
            },
        ]
    )

    assert rows == [
        {
            "source_table": "Active Members",
            "source_record_id": "rec_member_201",
            "flag_code": "review_member_side_person_generic_email",
            "severity": "medium",
            "record_label": "Signal Works",
            "source_field": "Email",
            "note": None,
        }
    ]


def test_readiness_trust_summary_separates_reviewed_truth_from_heuristics() -> None:
    sample = _sample_reporting_data()
    content_bundle = build_content_intelligence_bundle(
        organizations=sample["organizations"],
        people_payloads=sample["people"],
        affiliations=sample["affiliations"],
        participations=sample["participations"],
        cohorts=sample["cohorts"],
    )
    content_bundle["people"][0]["externally_publishable"] = True

    rows = report_readiness_trust_summary(
        content_bundle,
        sample["organizations"],
        sample["people"],
    )

    assert {
        "record_type": "organization",
        "trust_basis": "reviewed_truth_backed",
        "row_count": 1,
        "internally_usable_count": 1,
        "content_ready_count": 1,
        "spotlight_ready_count": 1,
        "externally_publishable_count": 0,
    } in rows
    assert {
        "record_type": "person",
        "trust_basis": "human_approved",
        "row_count": 1,
        "internally_usable_count": 1,
        "content_ready_count": 1,
        "spotlight_ready_count": 0,
        "externally_publishable_count": 1,
    } in rows


def test_review_burden_by_flag_summarizes_counts_and_scope() -> None:
    rows = report_review_burden_by_flag(
        [
            {
                "source_table": "Active Members",
                "source_record_id": "rec_1",
                "flag_code": "review_member_side_person_generic_email",
                "flag_type": "sparse_record",
                "severity": "medium",
            },
            {
                "source_table": "Active Members",
                "source_record_id": "rec_2",
                "flag_code": "review_member_side_person_generic_email",
                "flag_type": "sparse_record",
                "severity": "medium",
            },
            {
                "source_table": "Active Members",
                "source_record_id": "rec_3",
                "flag_code": "review_missing_org_type",
                "flag_type": "missing_org_type",
                "severity": "medium",
            },
        ]
    )

    assert rows[0] == {
        "flag_code": "review_member_side_person_generic_email",
        "flag_type": "sparse_record",
        "severity": "medium",
        "review_scope": "people_candidate",
        "count": 2,
        "source_tables": "Active Members",
    }


def test_organizations_by_cohort_groups_names_and_counts() -> None:
    sample = _sample_reporting_data()

    rows = report_organizations_by_cohort(
        sample["organizations"],
        sample["participations"],
        sample["cohorts"],
    )

    assert rows[0]["cohort_name"] == "Builder Fall 2024"
    assert rows[0]["organization_count"] == 1
    assert rows[1]["cohort_name"] == "Builder Spring 2026"
    assert "Acme AI" in str(rows[1]["organization_names"])


def test_reporting_snapshot_includes_requested_sections() -> None:
    sample = _sample_reporting_data()

    snapshot = build_reporting_snapshot(
        organizations=sample["organizations"],
        people_payloads=sample["people"],
        mentor_profiles=sample["mentor_profiles"],
        affiliations=sample["affiliations"],
        participations=sample["participations"],
        cohorts=sample["cohorts"],
        review_rows=sample["review_rows"],
    )

    assert snapshot["active_organizations_by_type"][0]["org_type"] == "partner"
    assert snapshot["active_people_by_type"][0]["person_type"] == "mentor"
    assert snapshot["active_people_by_source_path"] == [
        {
            "person_source_path": "mentor_structured",
            "count": 2,
            "reviewed_truth_backed_count": 0,
            "source_derived_count": 2,
        },
        {
            "person_source_path": "semi_structured_member_side",
            "count": 1,
            "reviewed_truth_backed_count": 0,
            "source_derived_count": 1,
        },
        {
            "person_source_path": "structured_member_fields",
            "count": 1,
            "reviewed_truth_backed_count": 1,
            "source_derived_count": 0,
        },
    ]
    assert [row["full_name"] for row in snapshot["structured_people"]] == ["Priya Founder"]
    assert [row["full_name"] for row in snapshot["semi_structured_auto_created_people"]] == ["Dana Planner"]
    assert [row["full_name"] for row in snapshot["mentor_derived_people"]] == ["Morgan Local", "Taylor Remote"]
    assert len(snapshot["readiness_trust_summary"]) >= 2
    assert len(snapshot["review_needed_people_candidates"]) >= 1
    assert len(snapshot["review_burden_by_flag"]) >= 1
    assert {row["membership_tier"] for row in snapshot["organizations_by_membership_tier"]} == {
        "Builder Plus",
        "Partner",
        "Standard",
        "Associate",
    }
    assert len(snapshot["internally_usable_organizations"]) == 4
    assert len(snapshot["internally_usable_people"]) == 4
    assert len(snapshot["content_ready_organizations"]) == 3
    assert len(snapshot["content_ready_people"]) == 3
    assert len(snapshot["spotlight_ready_organizations"]) == 2
    assert len(snapshot["spotlight_ready_people"]) == 1
    assert len(snapshot["externally_publishable_records"]) == 0
    assert len(snapshot["missing_content_asset_counts"]) >= 1
    assert len(snapshot["review_needed_records"]) >= 1


def test_spotlight_ready_people_is_narrower_than_content_ready_people() -> None:
    sample = _sample_reporting_data()
    snapshot = build_reporting_snapshot(
        organizations=sample["organizations"],
        people_payloads=sample["people"],
        mentor_profiles=sample["mentor_profiles"],
        affiliations=sample["affiliations"],
        participations=sample["participations"],
        cohorts=sample["cohorts"],
        review_rows=sample["review_rows"],
    )
    content_bundle = build_content_intelligence_bundle(
        organizations=sample["organizations"],
        people_payloads=sample["people"],
        affiliations=sample["affiliations"],
        participations=sample["participations"],
        cohorts=sample["cohorts"],
    )

    spotlight_rows = report_spotlight_ready_people(
        content_bundle,
        sample["people"],
    )
    internally_usable_rows = report_internally_usable_people(
        content_bundle,
        sample["people"],
    )

    assert len(internally_usable_rows) > len(snapshot["content_ready_people"])
    assert len(snapshot["content_ready_people"]) > len(snapshot["spotlight_ready_people"])
    assert [row["full_name"] for row in snapshot["spotlight_ready_people"]] == ["Priya Founder"]
    assert [row["full_name"] for row in spotlight_rows] == ["Priya Founder"]
    assert any(row["full_name"] == "Dana Planner" for row in internally_usable_rows)


def test_missing_content_asset_counts_roll_up_people_and_organizations() -> None:
    sample = _sample_reporting_data()
    snapshot = build_reporting_snapshot(
        organizations=sample["organizations"],
        people_payloads=sample["people"],
        mentor_profiles=sample["mentor_profiles"],
        affiliations=sample["affiliations"],
        participations=sample["participations"],
        cohorts=sample["cohorts"],
        review_rows=sample["review_rows"],
    )

    content_bundle = {
        "people": [
            {
                "content_eligible": True,
                "internally_usable": True,
                "content_ready": True,
                "spotlight_ready": False,
                "externally_publishable": False,
                "missing_content_assets": "headshot, linkedin",
            },
            {
                "content_eligible": True,
                "internally_usable": True,
                "content_ready": True,
                "spotlight_ready": False,
                "externally_publishable": False,
                "missing_content_assets": "headshot",
            },
        ],
        "organizations": [
            {
                "content_eligible": True,
                "internally_usable": True,
                "content_ready": True,
                "spotlight_ready": False,
                "externally_publishable": False,
                "missing_content_assets": "website, spokesperson",
            }
        ],
    }
    rows = report_missing_content_asset_counts(content_bundle)

    assert rows[0] == {
        "record_type": "person",
        "trust_basis": "heuristic_only",
        "readiness_level": "content_ready",
        "asset_name": "headshot",
        "count": 2,
    }
    assert {
        "record_type": "organization",
        "trust_basis": "heuristic_only",
        "readiness_level": "content_ready",
        "asset_name": "website",
        "count": 1,
    } in rows
    assert snapshot["missing_content_asset_counts"][0]["count"] >= 1


def test_reporting_snapshot_can_render_externally_publishable_records() -> None:
    sample = _sample_reporting_data()
    content_bundle = build_content_intelligence_bundle(
        organizations=sample["organizations"],
        people_payloads=sample["people"],
        affiliations=sample["affiliations"],
        participations=sample["participations"],
        cohorts=sample["cohorts"],
    )
    content_bundle["people"][0]["externally_publishable"] = True
    content_bundle["organizations"][0]["externally_publishable"] = True

    snapshot = build_reporting_snapshot(
        organizations=sample["organizations"],
        people_payloads=sample["people"],
        mentor_profiles=sample["mentor_profiles"],
        affiliations=sample["affiliations"],
        participations=sample["participations"],
        cohorts=sample["cohorts"],
        review_rows=sample["review_rows"],
        content_bundle=content_bundle,
    )

    labels = [row["label"] for row in snapshot["externally_publishable_records"]]
    assert "Acme AI" in labels
    assert "Morgan Local" in labels
    assert all(row["trust_basis"] == "human_approved" for row in snapshot["externally_publishable_records"])


def test_markdown_report_renders_expected_sections() -> None:
    sample = _sample_reporting_data()
    snapshot = build_reporting_snapshot(
        organizations=sample["organizations"],
        people_payloads=sample["people"],
        mentor_profiles=sample["mentor_profiles"],
        affiliations=sample["affiliations"],
        participations=sample["participations"],
        cohorts=sample["cohorts"],
        review_rows=sample["review_rows"],
    )

    markdown = render_markdown_report(snapshot)

    assert "# Ecosystem Report" in markdown
    assert "## Active Organizations By Type" in markdown
    assert "## Internally Usable Organizations" in markdown
    assert "## Internally Usable People" in markdown
    assert "## Active People By Source Path" in markdown
    assert "## Readiness Trust Summary" in markdown
    assert "## Structured People" in markdown
    assert "## Semi-Structured Auto-Created People" in markdown
    assert "## Mentor-Derived People" in markdown
    assert "## Review-Needed People Candidates" in markdown
    assert "## Spotlight-Ready People" in markdown
    assert "## Externally Publishable Records" in markdown
    assert "## Missing Content Asset Counts" in markdown
    assert "## Review Burden By Flag" in markdown
    assert "## Records Requiring Review" in markdown
    assert "Acme AI" in markdown


def test_csv_section_renders_headers_and_rows() -> None:
    sample = _sample_reporting_data()
    snapshot = build_reporting_snapshot(
        organizations=sample["organizations"],
        people_payloads=sample["people"],
        mentor_profiles=sample["mentor_profiles"],
        affiliations=sample["affiliations"],
        participations=sample["participations"],
        cohorts=sample["cohorts"],
        review_rows=sample["review_rows"],
    )

    csv_output = render_csv_section(snapshot, "active_organizations_by_type")
    provenance_csv = render_csv_section(snapshot, "semi_structured_auto_created_people")

    assert "org_type,count" in csv_output
    assert "startup,1" in csv_output
    assert "full_name,person_type,person_resolution_basis,person_source_path,review_state,reviewed_override_count" in provenance_csv
    assert "Dana Planner,operator,semi_structured_member_side,semi_structured_member_side,source_derived,0" in provenance_csv
