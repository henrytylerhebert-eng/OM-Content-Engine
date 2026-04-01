"""Content intelligence model."""

from __future__ import annotations

from datetime import date as date_type
from typing import Optional

from sqlmodel import Field, SQLModel


class ContentIntelligence(SQLModel, table=True):
    """Derived storytelling and communications fields."""

    __tablename__ = "content_intelligence"

    id: Optional[int] = Field(default=None, primary_key=True)
    linked_person_id: Optional[int] = Field(default=None, foreign_key="people.id")
    linked_organization_id: Optional[int] = Field(default=None, foreign_key="organizations.id")
    audience_tags: Optional[str] = Field(
        default=None,
        description="Comma-separated tags in Phase 1.",
    )
    industry_tags: Optional[str] = Field(
        default=None,
        description="Comma-separated tags in Phase 1.",
    )
    proof_tags: Optional[str] = Field(
        default=None,
        description="Comma-separated tags in Phase 1.",
    )
    content_eligible: bool = False
    internally_usable: bool = False
    content_ready: bool = False
    narrative_theme: Optional[str] = None
    message_pillar: Optional[str] = None
    story_type: Optional[str] = None
    spotlight_ready: bool = False
    externally_publishable: bool = False
    spokesperson_candidate: bool = False
    founder_story_candidate: bool = False
    mentor_story_candidate: bool = False
    ecosystem_proof_candidate: bool = False
    missing_content_assets: Optional[str] = Field(
        default=None,
        description="Comma-separated list of content assets still missing.",
    )
    profile_completeness_score: int = 0
    last_featured_date: Optional[date_type] = None
    priority_score: int = 0
    source_record_id: Optional[str] = None
    source_system: Optional[str] = None
