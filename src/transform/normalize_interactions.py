"""Starter interaction normalization for connections, meeting requests, and feedback."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Mapping, Optional

from src.transform.review_flags import ReviewFlag, add_review_flag


@dataclass
class InteractionNormalizationResult:
    """Interaction payloads plus review flags."""

    interactions: list[dict[str, object]] = field(default_factory=list)
    review_flags: list[ReviewFlag] = field(default_factory=list)


def _value(row: Mapping[str, object], *keys: str) -> Optional[str]:
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        cleaned = str(value).strip()
        if cleaned:
            return cleaned
    return None


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    cleaned = value.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    try:
        return date.fromisoformat(cleaned)
    except ValueError:
        return None


def _interaction_type(source_table: str, row: Mapping[str, object]) -> str:
    explicit = _value(row, "Interaction Type")
    if explicit:
        return explicit.strip().lower().replace(" ", "_")
    mapping = {
        "Connections": "connection",
        "Meeting Requests": "meeting_request",
        "Feedback": "feedback",
    }
    return mapping.get(source_table, "interaction")


def normalize_interaction_row(
    row: Mapping[str, object],
    source_table: str,
    source_system: str = "airtable_export",
) -> InteractionNormalizationResult:
    """Create an interaction payload from a raw source row."""

    flags: list[ReviewFlag] = []
    interaction_date = _parse_date(
        _value(row, "Date", "Meeting Date", "Request Date", "Submitted At", "Created At")
    )
    if interaction_date is None:
        add_review_flag(
            flags,
            "review_missing_interaction_date",
            source_table=source_table,
            row=row,
            source_system=source_system,
            source_field="Date",
        )

    subject = _value(
        row,
        "Person Name",
        "Contact Name",
        "Founder Name",
        "Organization Name",
        "Company Name",
        "Requestor Name",
        "Name",
    )
    if subject is None:
        add_review_flag(
            flags,
            "review_missing_interaction_subject",
            source_table=source_table,
            row=row,
            source_system=source_system,
            source_field="Contact Name",
        )

    payload = {
        "person_id": None,
        "organization_id": None,
        "interaction_type": _interaction_type(source_table, row),
        "date": interaction_date,
        "owner": _value(row, "Owner", "Assigned To", "Requested To"),
        "notes": _value(row, "Notes", "Feedback", "Request Details", "Summary"),
        "follow_up_date": _parse_date(_value(row, "Follow Up Date")),
        "source_record_id": _value(row, "Record ID", "Airtable Record ID", "id"),
        "source_system": _value(row, "Source System") or source_system,
    }
    return InteractionNormalizationResult(interactions=[payload], review_flags=flags)
