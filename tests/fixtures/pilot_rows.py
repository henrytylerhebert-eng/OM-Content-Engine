"""Representative pilot-style rows loaded from safe synthetic CSV exports."""

from __future__ import annotations

import csv
from pathlib import Path


FIXTURE_DIR = Path(__file__).resolve().parent


def fixture_path(file_name: str) -> Path:
    """Return the absolute path for a file-backed fixture."""

    return FIXTURE_DIR / file_name


def load_csv_fixture(file_name: str) -> list[dict[str, str]]:
    """Load a synthetic Airtable-style export fixture."""

    path = fixture_path(file_name)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            {key.strip(): (value or "").strip() for key, value in row.items()}
            for row in reader
        ]


def _rows_by_id(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row["Record ID"]: row for row in rows}


ACTIVE_MEMBER_ROWS = load_csv_fixture("active_members.csv")
ACTIVE_MEMBER_ROWS_BY_ID = _rows_by_id(ACTIVE_MEMBER_ROWS)

ACTIVE_MEMBER_STARTUP_ROW = ACTIVE_MEMBER_ROWS_BY_ID["rec_member_001"]
ACTIVE_MEMBER_PARTNER_ROW = ACTIVE_MEMBER_ROWS_BY_ID["rec_member_002"]
ACTIVE_MEMBER_GROUPED_PERSONNEL_ROW = ACTIVE_MEMBER_ROWS_BY_ID["rec_member_003"]
ACTIVE_MEMBER_SPARSE_ROW = ACTIVE_MEMBER_ROWS_BY_ID["rec_member_004"]
ACTIVE_MEMBER_INTERNAL_ROW = ACTIVE_MEMBER_ROWS_BY_ID["rec_member_005"]
ACTIVE_MEMBER_MULTI_COHORT_ROW = ACTIVE_MEMBER_ROWS_BY_ID["rec_member_006"]

MENTOR_ROWS = load_csv_fixture("mentors.csv")
MENTOR_ROWS_BY_ID = _rows_by_id(MENTOR_ROWS)

MENTOR_ROW = MENTOR_ROWS_BY_ID["rec_mentor_001"]
MENTOR_REMOTE_ROW = MENTOR_ROWS_BY_ID["rec_mentor_002"]
MENTOR_SPARSE_ROW = MENTOR_ROWS_BY_ID["rec_mentor_003"]

COHORT_EXPORT_ROWS = load_csv_fixture("cohorts.csv")
COHORT_EXPORT_ROWS_BY_COMPANY = {row["Company Name"]: row for row in COHORT_EXPORT_ROWS}

COHORT_EXPORT_ACME_ROW = COHORT_EXPORT_ROWS_BY_COMPANY["Acme AI"]
COHORT_EXPORT_DELTA_ROW = COHORT_EXPORT_ROWS_BY_COMPANY["Delta Dynamics"]
COHORT_EXPORT_UNRESOLVED_ROW = COHORT_EXPORT_ROWS_BY_COMPANY["Ghost Orbit"]

COHORT_ROW = {
    "Record ID": "rec_cohort_001",
    "Program Name": "Builder",
    "Cohort Name": "Builder Spring 2026",
    "Start Date": "2026-01-15",
    "End Date": "2026-05-30",
    "Participation Status": "active",
    "Notes": "Current builder cohort member.",
}

CONNECTION_ROW = {
    "Record ID": "rec_connection_001",
    "Contact Name": "Jane Founder",
    "Date": "2026-02-10",
    "Owner": "Opportunity Machine",
    "Summary": "Warm founder introduction from a partner.",
}

AMBIGUOUS_MEMBER_ROW = {
    "Record ID": "rec_ambiguous_001",
    "Organization Name": "Community Network",
    "Status": "Active",
}

ACTIVE_MEMBER_SEMI_STRUCTURED_SINGLE_ROW = {
    "Record ID": "rec_member_semi_001",
    "Company Name": "Signal Works",
    "Membership Status": "Active",
    "Personnel": "Morgan Rivers - CEO",
    "Primary Email (from Link to Application)": "morgan@signalworks.example",
    "Cohort": "Builder Spring 2026",
}

ACTIVE_MEMBER_SEMI_STRUCTURED_FIRST_NAME_ROW = {
    "Record ID": "rec_member_semi_002",
    "Company Name": "Signal Works",
    "Membership Status": "Active",
    "Personnel": "Morgan",
    "Primary Email (from Link to Application)": "morgan@signalworks.example",
}

ACTIVE_MEMBER_SEMI_STRUCTURED_GENERIC_EMAIL_ROW = {
    "Record ID": "rec_member_semi_003",
    "Company Name": "Signal Works",
    "Membership Status": "Active",
    "Personnel": "Morgan Rivers - CEO",
    "Primary Email (from Link to Application)": "info@signalworks.example",
}

ACTIVE_MEMBER_SEMI_STRUCTURED_MULTI_CONTEXT_ROW = {
    "Record ID": "rec_member_semi_004",
    "Company Name": "Signal Works",
    "Organization Name": "Signal Works Labs",
    "Membership Status": "Active",
    "Personnel": "Morgan Rivers - CEO",
    "Primary Email (from Link to Application)": "morgan@signalworks.example",
}
