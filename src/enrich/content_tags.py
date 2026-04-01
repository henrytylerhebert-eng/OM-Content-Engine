"""Backward-compatible wrappers around the content intelligence layer."""

from __future__ import annotations

from typing import Optional

from src.enrich.content_intelligence import (
    build_organization_content_intelligence,
    build_person_content_intelligence,
)


def build_content_intelligence_seed(
    person_payload: Optional[dict[str, object]],
    organization_payload: Optional[dict[str, object]] = None,
    *,
    source_system: str = "derived",
) -> dict[str, object]:
    """Create a lightweight derived content-intelligence payload."""

    if person_payload is not None:
        result = build_person_content_intelligence(
            person_payload,
            source_system=source_system,
        )
        return result.intelligence

    if organization_payload is not None:
        result = build_organization_content_intelligence(
            organization_payload,
            source_system=source_system,
        )
        return result.intelligence

    return {
        "linked_person_id": None,
        "linked_organization_id": None,
        "audience_tags": None,
        "industry_tags": None,
        "proof_tags": None,
        "content_eligible": False,
        "narrative_theme": None,
        "message_pillar": None,
        "story_type": None,
        "spotlight_ready": False,
        "spokesperson_candidate": False,
        "founder_story_candidate": False,
        "mentor_story_candidate": False,
        "ecosystem_proof_candidate": False,
        "missing_content_assets": None,
        "profile_completeness_score": 0,
        "last_featured_date": None,
        "priority_score": 0,
        "source_record_id": None,
        "source_system": source_system,
    }
