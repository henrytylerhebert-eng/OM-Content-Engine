"""Reporting-friendly wrappers around the rule-based segment layer."""

from __future__ import annotations

from src.enrich.audience_segments import select_local_ai_mentors
from src.enrich.ecosystem_segments import (
    build_segment_bundle,
    segment_active_mentors,
    segment_active_startup_members,
    segment_alumni_founders,
    segment_content_ready_organizations,
    segment_content_ready_people,
    segment_current_cohort_founders,
    segment_internal_records,
    segment_local_mentors,
    segment_non_local_mentors,
    segment_partner_organizations,
    segment_review_needed_records,
)


def build_active_founder_segment(people_payloads: list[dict[str, object]]) -> list[dict[str, object]]:
    """Backward-compatible founder filter used by earlier tests and scripts."""

    return [
        payload
        for payload in people_payloads
        if payload.get("person_type") == "founder" and bool(payload.get("active_flag", True))
    ]


def build_content_ready_people_segment(people_payloads: list[dict[str, object]]) -> list[dict[str, object]]:
    """Backward-compatible wrapper for content-ready people."""

    return segment_content_ready_people(people_payloads)


def build_spotlight_ready_organization_segment(
    organizations: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Backward-compatible wrapper for content-ready organizations."""

    return segment_content_ready_organizations(organizations)


def build_local_ai_mentor_segment(
    people_payloads: list[dict[str, object]],
    mentor_profiles: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Backward-compatible local AI mentor filter."""

    return select_local_ai_mentors(people_payloads, mentor_profiles)


__all__ = [
    "build_segment_bundle",
    "build_active_founder_segment",
    "build_content_ready_people_segment",
    "build_spotlight_ready_organization_segment",
    "build_local_ai_mentor_segment",
    "segment_active_startup_members",
    "segment_partner_organizations",
    "segment_active_mentors",
    "segment_local_mentors",
    "segment_non_local_mentors",
    "segment_current_cohort_founders",
    "segment_alumni_founders",
    "segment_internal_records",
    "segment_content_ready_organizations",
    "segment_content_ready_people",
    "segment_review_needed_records",
]
