"""Rule-based ecosystem segmentation for reporting and future automations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Sequence


@dataclass(frozen=True)
class SegmentDefinition:
    """Human-readable rule metadata for a segment."""

    name: str
    label: str
    record_type: str
    rule: str
    description: str


def _record_id(record: dict[str, object]) -> Optional[object]:
    value = record.get("id")
    if value is not None:
        return value
    return record.get("source_record_id")


def _is_truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "active"}


def _status(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _mentor_index(
    people_payloads: Sequence[dict[str, object]],
    mentor_profiles: Sequence[dict[str, object]],
) -> Dict[object, tuple[dict[str, object], dict[str, object]]]:
    people_by_key: Dict[object, dict[str, object]] = {}
    for person in people_payloads:
        key = person.get("id") if person.get("id") is not None else person.get("source_record_id")
        if key is not None and person.get("person_type") == "mentor":
            people_by_key[key] = person

    joined: Dict[object, tuple[dict[str, object], dict[str, object]]] = {}
    for profile in mentor_profiles:
        key = profile.get("person_id") if profile.get("person_id") is not None else profile.get("source_record_id")
        if key in people_by_key:
            joined[key] = (people_by_key[key], profile)
    return joined


def segment_active_startup_members(
    organizations: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Return active startup member organizations."""

    return [
        org
        for org in organizations
        if org.get("org_type") == "startup" and _is_truthy(org.get("active_flag"))
    ]


def segment_partner_organizations(
    organizations: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Return partner organizations.

    Partner membership can be represented either as an org type or a membership
    tier, depending on how specifically the organization was classified.
    """

    return [
        org
        for org in organizations
        if org.get("org_type") == "partner"
        or str(org.get("membership_tier") or "").strip().lower() == "partner"
    ]


def segment_active_mentors(
    people_payloads: Sequence[dict[str, object]],
    mentor_profiles: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Return active mentors with a mentor profile."""

    records: list[dict[str, object]] = []
    for person, profile in _mentor_index(people_payloads, mentor_profiles).values():
        if _is_truthy(person.get("active_flag")) and _is_truthy(profile.get("mentor_active_flag")):
            records.append(person)
    return records


def segment_local_mentors(
    people_payloads: Sequence[dict[str, object]],
    mentor_profiles: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Return mentors explicitly marked local."""

    records: list[dict[str, object]] = []
    for person, profile in _mentor_index(people_payloads, mentor_profiles).values():
        if (
            _is_truthy(person.get("active_flag"))
            and _is_truthy(profile.get("mentor_active_flag"))
            and profile.get("mentor_location_type") == "local"
        ):
            records.append(person)
    return records


def segment_non_local_mentors(
    people_payloads: Sequence[dict[str, object]],
    mentor_profiles: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Return mentors explicitly marked remote or hybrid."""

    records: list[dict[str, object]] = []
    for person, profile in _mentor_index(people_payloads, mentor_profiles).values():
        if (
            _is_truthy(person.get("active_flag"))
            and _is_truthy(profile.get("mentor_active_flag"))
            and profile.get("mentor_location_type") in {"remote", "hybrid"}
        ):
            records.append(person)
    return records


def _founder_people_by_org(
    people_payloads: Sequence[dict[str, object]],
    affiliations: Sequence[dict[str, object]],
) -> Dict[object, list[dict[str, object]]]:
    people_by_id = {_record_id(person): person for person in people_payloads if _record_id(person) is not None}
    founders_by_org: Dict[object, list[dict[str, object]]] = {}

    for affiliation in affiliations:
        if not _is_truthy(affiliation.get("founder_flag")):
            continue
        person = people_by_id.get(affiliation.get("person_id"))
        org_id = affiliation.get("organization_id")
        if person is None or org_id is None:
            continue
        founders_by_org.setdefault(org_id, []).append(person)
    return founders_by_org


def segment_current_cohort_founders(
    people_payloads: Sequence[dict[str, object]],
    affiliations: Sequence[dict[str, object]],
    participations: Sequence[dict[str, object]],
    cohorts: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Return founders attached to active cohort participation."""

    founders_by_org = _founder_people_by_org(people_payloads, affiliations)
    cohorts_by_id = {_record_id(cohort): cohort for cohort in cohorts if _record_id(cohort) is not None}
    selected: Dict[object, dict[str, object]] = {}

    for participation in participations:
        if _status(participation.get("participation_status")) != "active":
            continue
        cohort = cohorts_by_id.get(participation.get("cohort_id"))
        if cohort is not None and not _is_truthy(cohort.get("active_flag")):
            continue
        org_id = participation.get("organization_id")
        for founder in founders_by_org.get(org_id, []):
            founder_key = _record_id(founder)
            if founder_key is not None:
                selected[founder_key] = founder

    return list(selected.values())


def segment_alumni_founders(
    people_payloads: Sequence[dict[str, object]],
    affiliations: Sequence[dict[str, object]],
    participations: Sequence[dict[str, object]],
    cohorts: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Return founders attached to alumni participation or inactive cohorts."""

    founders_by_org = _founder_people_by_org(people_payloads, affiliations)
    cohorts_by_id = {_record_id(cohort): cohort for cohort in cohorts if _record_id(cohort) is not None}
    selected: Dict[object, dict[str, object]] = {}

    for participation in participations:
        cohort = cohorts_by_id.get(participation.get("cohort_id"))
        participation_status = _status(participation.get("participation_status"))
        is_alumni = participation_status == "alumni"
        if cohort is not None and not _is_truthy(cohort.get("active_flag")):
            is_alumni = True
        if not is_alumni:
            continue

        org_id = participation.get("organization_id")
        for founder in founders_by_org.get(org_id, []):
            founder_key = _record_id(founder)
            if founder_key is not None:
                selected[founder_key] = founder

    return list(selected.values())


def segment_internal_records(
    organizations: Sequence[dict[str, object]],
    people_payloads: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Return internal organizations and internal-facing people."""

    records: list[dict[str, object]] = []
    for org in organizations:
        if org.get("org_type") == "internal":
            records.append({"record_type": "organization", "record": org})
    for person in people_payloads:
        if person.get("person_type") == "staff":
            records.append({"record_type": "person", "record": person})
    return records


def segment_content_ready_organizations(
    organizations: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Return organizations suitable for storytelling or public-facing use."""

    return [
        org
        for org in organizations
        if _is_truthy(org.get("active_flag"))
        and _is_truthy(org.get("content_eligible"))
        and int(org.get("spotlight_priority", 0) or 0) > 0
    ]


def segment_content_ready_people(
    people_payloads: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Return people suitable for storytelling or public-facing use."""

    return [
        person
        for person in people_payloads
        if _is_truthy(person.get("active_flag")) and _is_truthy(person.get("content_ready"))
    ]


def segment_review_needed_records(
    review_rows: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Return review queue rows that still need human attention."""

    return [row for row in review_rows if row.get("flag_code")]


SEGMENT_DEFINITIONS = {
    "active_startup_members": SegmentDefinition(
        name="active_startup_members",
        label="Active startup members",
        record_type="organization",
        rule="Organization.org_type == 'startup' and Organization.active_flag is truthy.",
        description="Startup member organizations that are currently active.",
    ),
    "partner_organizations": SegmentDefinition(
        name="partner_organizations",
        label="Partner organizations",
        record_type="organization",
        rule="Organization.org_type == 'partner'.",
        description="Partner organizations regardless of cohort status.",
    ),
    "active_mentors": SegmentDefinition(
        name="active_mentors",
        label="Active mentors",
        record_type="person",
        rule="Person.person_type == 'mentor' and both Person.active_flag and MentorProfile.mentor_active_flag are truthy.",
        description="Mentors that are active in both the person and mentor-profile layers.",
    ),
    "local_mentors": SegmentDefinition(
        name="local_mentors",
        label="Local mentors",
        record_type="person",
        rule="Active mentor with MentorProfile.mentor_location_type == 'local'.",
        description="Mentors explicitly marked local.",
    ),
    "non_local_mentors": SegmentDefinition(
        name="non_local_mentors",
        label="Non-local mentors",
        record_type="person",
        rule="Active mentor with MentorProfile.mentor_location_type in {'remote', 'hybrid'}.",
        description="Mentors explicitly marked remote or hybrid.",
    ),
    "current_cohort_founders": SegmentDefinition(
        name="current_cohort_founders",
        label="Current cohort founders",
        record_type="person",
        rule="Founder affiliation joined to organization participation where Participation.participation_status == 'active' and the cohort is active when present.",
        description="Founders whose organizations are in an active cohort run.",
    ),
    "alumni_founders": SegmentDefinition(
        name="alumni_founders",
        label="Alumni founders",
        record_type="person",
        rule="Founder affiliation joined to organization participation where Participation.participation_status == 'alumni' or the linked cohort is inactive.",
        description="Founders whose organizations are tied to alumni or completed cohort participation.",
    ),
    "internal_records": SegmentDefinition(
        name="internal_records",
        label="Internal records",
        record_type="mixed",
        rule="Organization.org_type == 'internal' or Person.person_type == 'staff'.",
        description="Internal Opportunity Machine organizations and staff records.",
    ),
    "content_ready_organizations": SegmentDefinition(
        name="content_ready_organizations",
        label="Content-ready organizations",
        record_type="organization",
        rule="Organization.active_flag is truthy, Organization.content_eligible is truthy, and Organization.spotlight_priority > 0.",
        description="Organizations ready to be considered for storytelling or public-facing use.",
    ),
    "content_ready_people": SegmentDefinition(
        name="content_ready_people",
        label="Content-ready people",
        record_type="person",
        rule="Person.active_flag is truthy and Person.content_ready is truthy.",
        description="People ready to be considered for storytelling or public-facing use.",
    ),
    "review_needed_records": SegmentDefinition(
        name="review_needed_records",
        label="Review-needed records",
        record_type="review_row",
        rule="Any row already in the review queue.",
        description="Rows that need a human pass before being trusted downstream.",
    ),
}


def build_segment_bundle(
    *,
    organizations: Sequence[dict[str, object]],
    people_payloads: Sequence[dict[str, object]],
    mentor_profiles: Sequence[dict[str, object]],
    affiliations: Sequence[dict[str, object]],
    participations: Sequence[dict[str, object]],
    cohorts: Sequence[dict[str, object]],
    review_rows: Sequence[dict[str, object]],
) -> dict[str, dict[str, object]]:
    """Return all first-pass segments in a reporting-friendly bundle."""

    segment_records = {
        "active_startup_members": segment_active_startup_members(organizations),
        "partner_organizations": segment_partner_organizations(organizations),
        "active_mentors": segment_active_mentors(people_payloads, mentor_profiles),
        "local_mentors": segment_local_mentors(people_payloads, mentor_profiles),
        "non_local_mentors": segment_non_local_mentors(people_payloads, mentor_profiles),
        "current_cohort_founders": segment_current_cohort_founders(
            people_payloads, affiliations, participations, cohorts
        ),
        "alumni_founders": segment_alumni_founders(
            people_payloads, affiliations, participations, cohorts
        ),
        "internal_records": segment_internal_records(organizations, people_payloads),
        "content_ready_organizations": segment_content_ready_organizations(organizations),
        "content_ready_people": segment_content_ready_people(people_payloads),
        "review_needed_records": segment_review_needed_records(review_rows),
    }

    bundle: dict[str, dict[str, object]] = {}
    for name, records in segment_records.items():
        definition = SEGMENT_DEFINITIONS[name]
        bundle[name] = {
            "name": definition.name,
            "label": definition.label,
            "record_type": definition.record_type,
            "rule": definition.rule,
            "description": definition.description,
            "count": len(records),
            "records": list(records),
        }
    return bundle
