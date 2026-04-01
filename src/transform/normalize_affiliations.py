"""Starter affiliation normalization for people-to-organization relationships."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Mapping, Optional, Sequence

from src.transform.normalize_people import PersonDraft
from src.transform.review_flags import ReviewFlag, add_review_flag


@dataclass
class AffiliationNormalizationResult:
    """Affiliation payloads plus review flags."""

    affiliations: list[dict[str, object]] = field(default_factory=list)
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
            if fmt == "%Y-%m-%d":
                return date.fromisoformat(cleaned)
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


def normalize_affiliations_from_row(
    row: Mapping[str, object],
    source_table: str,
    people: Sequence[PersonDraft],
    organization: Optional[dict[str, object]],
    source_system: str = "airtable_export",
) -> AffiliationNormalizationResult:
    """Create affiliation payloads using person hints gathered during normalization."""

    flags: list[ReviewFlag] = []
    affiliations: list[dict[str, object]] = []
    if not people:
        add_review_flag(
            flags,
            "review_no_affiliation_people",
            source_table=source_table,
            row=row,
            source_system=source_system,
        )
        return AffiliationNormalizationResult(affiliations=affiliations, review_flags=flags)

    if not organization:
        expected_org = source_table in {"Active Members", "Member Companies", "Personnel"}
        if expected_org:
            add_review_flag(
                flags,
                "review_affiliation_missing_organization",
                source_table=source_table,
                row=row,
                source_system=source_system,
            )
        return AffiliationNormalizationResult(affiliations=affiliations, review_flags=flags)

    for person in people:
        affiliations.append(
            {
                "person_id": None,
                "organization_id": None,
                "role_title": person.role_title,
                "role_category": person.role_category,
                "founder_flag": person.founder_flag,
                "primary_contact_flag": person.primary_contact_flag,
                "spokesperson_flag": person.spokesperson_flag,
                "active_flag": bool(organization.get("active_flag", True)),
                "start_date": _parse_date(_value(row, "Start Date", "Joined Date")),
                "end_date": _parse_date(_value(row, "End Date", "Exited Date")),
                "source_record_id": _value(row, "Record ID", "Airtable Record ID", "id"),
                "source_system": _value(row, "Source System") or source_system,
            }
        )

    return AffiliationNormalizationResult(affiliations=affiliations, review_flags=flags)
