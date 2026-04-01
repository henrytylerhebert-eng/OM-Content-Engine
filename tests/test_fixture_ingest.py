"""Tests for file-backed synthetic export fixtures."""

from src.ingest.airtable_import import load_airtable_csv_export
from tests.fixtures.pilot_rows import (
    ACTIVE_MEMBER_ROWS,
    MENTOR_ROWS,
    fixture_path,
)


def test_active_members_fixture_loads_with_source_provenance() -> None:
    records = load_airtable_csv_export(
        fixture_path("active_members.csv"),
        source_table="Active Members",
    )

    assert len(records) == len(ACTIVE_MEMBER_ROWS)
    startup = next(record for record in records if record.source_record_id == "rec_member_001")
    grouped = next(record for record in records if record.source_record_id == "rec_member_003")
    internal = next(record for record in records if record.source_record_id == "rec_member_005")

    assert startup.source_table == "Active Members"
    assert startup.source_system == "airtable_export"
    assert startup.file_path.endswith("tests/fixtures/active_members.csv")
    assert startup.row_hash
    assert grouped.raw["Personnel"].startswith("Jamie Wells")
    assert internal.raw["Member Type"] == "Internal"


def test_mentors_fixture_loads_with_source_provenance() -> None:
    records = load_airtable_csv_export(
        fixture_path("mentors.csv"),
        source_table="Mentors",
    )

    assert len(records) == len(MENTOR_ROWS)
    mentor = next(record for record in records if record.source_record_id == "rec_mentor_001")
    sparse = next(record for record in records if record.source_record_id == "rec_mentor_003")

    assert mentor.raw["Full Name"] == "Morgan Guide"
    assert mentor.raw["Mentor Location Type"] == "Local"
    assert mentor.row_hash
    assert sparse.raw["Email"] == ""


def test_fixture_exports_cover_requested_sample_shapes() -> None:
    active_member_record_ids = {row["Record ID"] for row in ACTIVE_MEMBER_ROWS}
    mentor_record_ids = {row["Record ID"] for row in MENTOR_ROWS}

    assert active_member_record_ids == {
        "rec_member_001",
        "rec_member_002",
        "rec_member_003",
        "rec_member_004",
        "rec_member_005",
        "rec_member_006",
    }
    assert mentor_record_ids == {
        "rec_mentor_001",
        "rec_mentor_002",
        "rec_mentor_003",
    }
