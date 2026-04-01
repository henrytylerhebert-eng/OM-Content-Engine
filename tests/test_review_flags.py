"""Tests for structured review flag behavior."""

from src.transform.normalize_interactions import normalize_interaction_row
from src.transform.normalize_organizations import normalize_organization_row
from src.transform.normalize_participation import normalize_participation_row
from src.transform.normalize_people import normalize_people_from_row
from src.transform.review_flags import (
    REVIEW_FLAG_CATEGORIES,
    build_review_flag,
    build_review_queue_rows,
    review_flag_codes,
)
from tests.fixtures.pilot_rows import (
    ACTIVE_MEMBER_GROUPED_PERSONNEL_ROW,
    ACTIVE_MEMBER_MULTI_COHORT_ROW,
    ACTIVE_MEMBER_SEMI_STRUCTURED_GENERIC_EMAIL_ROW,
    ACTIVE_MEMBER_SEMI_STRUCTURED_MULTI_CONTEXT_ROW,
)


def test_build_review_flag_preserves_source_context() -> None:
    row = {
        "Record ID": "rec_flag_001",
        "Company Name": "Unknown Org",
        "Member Type": "",
    }

    flag = build_review_flag(
        "review_org_type",
        source_table="Active Members",
        row=row,
        source_field="Member Type",
        raw_value="",
        note="No usable org type value was provided.",
    )

    assert flag.code == "review_org_type"
    assert flag.category == "missing_org_type"
    assert flag.source_table == "Active Members"
    assert flag.source_record_id == "rec_flag_001"
    assert flag.record_label == "Unknown Org"
    assert flag.source_field == "Member Type"
    assert flag.raw_value == ""
    assert flag.description


def test_required_review_flag_categories_are_registered() -> None:
    assert {
        "unknown_entity_type",
        "ambiguous_personnel_parse",
        "sparse_record",
        "placeholder_record",
        "duplicate_suspected",
        "invalid_cohort_parse",
        "missing_name",
        "missing_org_type",
        "internal_record_detected",
        "grouped_record_detected",
    }.issubset(REVIEW_FLAG_CATEGORIES)


def test_grouped_personnel_flag_keeps_raw_value_and_field_context() -> None:
    result = normalize_people_from_row(ACTIVE_MEMBER_GROUPED_PERSONNEL_ROW, source_table="Active Members")
    flag = next(flag for flag in result.review_flags if flag.code == "review_personnel_parse")

    assert flag.source_table == "Active Members"
    assert flag.source_record_id == "rec_member_003"
    assert flag.source_field == "Personnel"
    assert "Builder Intern Team" in str(flag.raw_value)


def test_generic_email_review_flag_keeps_member_side_context() -> None:
    result = normalize_people_from_row(
        ACTIVE_MEMBER_SEMI_STRUCTURED_GENERIC_EMAIL_ROW,
        source_table="Active Members",
    )
    flag = next(flag for flag in result.review_flags if flag.code == "review_member_side_person_generic_email")

    assert flag.source_table == "Active Members"
    assert flag.source_record_id == "rec_member_semi_003"
    assert flag.source_field == "Email"
    assert flag.raw_value == "info@signalworks.example"


def test_multi_context_review_flag_keeps_member_side_context() -> None:
    result = normalize_people_from_row(
        ACTIVE_MEMBER_SEMI_STRUCTURED_MULTI_CONTEXT_ROW,
        source_table="Active Members",
    )
    flag = next(flag for flag in result.review_flags if flag.code == "review_member_side_person_context_ambiguous")

    assert flag.source_table == "Active Members"
    assert flag.source_record_id == "rec_member_semi_004"
    assert flag.source_field == "Company Name"
    assert "Signal Works" in str(flag.raw_value)


def test_duplicate_people_are_flagged_before_dedupe() -> None:
    row = {
        "Record ID": "rec_duplicate_001",
        "Company Name": "Mirror Works",
        "Founder Name": "Jamie Wells",
        "Founder Email": "jamie@mirrorworks.example",
        "Primary Contact Name": "Jamie Wells",
        "Primary Contact Email": "jamie@mirrorworks.example",
        "Status": "Active",
    }

    result = normalize_people_from_row(row, source_table="Active Members")

    assert len(result.people) == 1
    assert "review_duplicate_suspected" in review_flag_codes(result.review_flags)


def test_multi_value_cohort_flag_preserves_raw_value() -> None:
    result = normalize_participation_row(ACTIVE_MEMBER_MULTI_COHORT_ROW, source_table="Active Members")
    flag = result.review_flags[0]

    assert flag.code == "review_multi_value_cohort_parse"
    assert flag.source_table == "Active Members"
    assert flag.source_field == "Cohort"
    assert "Builder Spring 2025" in str(flag.raw_value)


def test_missing_org_type_flag_is_exportable_as_review_queue_row() -> None:
    result = normalize_organization_row(
        {
            "Record ID": "rec_org_ambiguous_001",
            "Company Name": "Community Network",
            "Status": "Active",
        },
        source_table="Active Members",
    )

    rows = build_review_queue_rows(
        source_table="Active Members",
        source_record_id="rec_org_ambiguous_001",
        flag_codes=result.review_flags,
        record_label="Community Network",
    )

    org_type_row = next(row for row in rows if row["flag_code"] == "review_org_type")
    assert org_type_row["flag_type"] == "missing_org_type"
    assert org_type_row["source_field"] == "Member Type"
    assert org_type_row["description"] is not None


def test_interaction_flags_capture_missing_date_and_subject() -> None:
    result = normalize_interaction_row(
        {
            "Record ID": "rec_interaction_001",
            "Owner": "Opportunity Machine",
            "Summary": "Follow-up still needs context.",
        },
        source_table="Connections",
    )

    assert review_flag_codes(result.review_flags) == [
        "review_missing_interaction_date",
        "review_missing_interaction_subject",
    ]
    assert result.review_flags[0].source_table == "Connections"
    assert result.review_flags[0].source_field == "Date"
