"""Simple ecosystem summary helpers."""

from __future__ import annotations

from collections import Counter
from typing import Sequence


def build_ecosystem_summary(
    organizations: Sequence[dict[str, object]],
    people: Sequence[dict[str, object]],
    mentor_profiles: Sequence[dict[str, object]],
    participation_records: Sequence[dict[str, object]],
) -> dict[str, object]:
    """Build a compact count-based summary for early reporting."""

    org_types = Counter(str(org.get("org_type", "other")) for org in organizations)
    person_types = Counter(str(person.get("person_type", "other")) for person in people)
    participation_status = Counter(
        str(record.get("participation_status", "unknown")) for record in participation_records
    )

    return {
        "organization_count": len(organizations),
        "people_count": len(people),
        "mentor_profile_count": len(mentor_profiles),
        "participation_count": len(participation_records),
        "organization_types": dict(org_types),
        "person_types": dict(person_types),
        "participation_status": dict(participation_status),
    }

