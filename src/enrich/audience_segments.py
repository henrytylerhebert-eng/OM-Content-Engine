"""Helpers for simple audience and campaign segmentation."""

from __future__ import annotations

from typing import Optional, Set


def _split_tags(value: Optional[str]) -> Set[str]:
    if not value:
        return set()
    return {part.strip().lower() for part in value.replace(";", ",").split(",") if part.strip()}


def filter_people_by_expertise(
    people_payloads: list[dict[str, object]],
    required_tags: set[str],
) -> list[dict[str, object]]:
    """Return people whose expertise tags include all required tags."""

    required = {tag.lower() for tag in required_tags}
    matches: list[dict[str, object]] = []
    for payload in people_payloads:
        expertise = _split_tags(payload.get("expertise_tags"))  # type: ignore[arg-type]
        if required.issubset(expertise):
            matches.append(payload)
    return matches


def select_local_ai_mentors(
    people_payloads: list[dict[str, object]],
    mentor_profiles: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Return mentor payloads that look local and have AI expertise."""

    mentor_names = {
        payload.get("source_record_id"): payload
        for payload in people_payloads
        if payload.get("person_type") == "mentor"
    }
    selected: list[dict[str, object]] = []
    for profile in mentor_profiles:
        person_payload = mentor_names.get(profile.get("source_record_id"))
        if not person_payload:
            continue
        expertise = _split_tags(person_payload.get("expertise_tags"))  # type: ignore[arg-type]
        if "ai" in expertise and profile.get("mentor_location_type") == "local":
            selected.append(person_payload)
    return selected
