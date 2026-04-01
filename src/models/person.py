"""Person domain model."""

from __future__ import annotations

from typing import Optional

from sqlmodel import Field, SQLModel


class Person(SQLModel, table=True):
    """Normalized person record."""

    __tablename__ = "people"

    id: Optional[int] = Field(default=None, primary_key=True)
    full_name: str
    email: Optional[str] = None
    linkedin: Optional[str] = None
    bio: Optional[str] = None
    headshot_url: Optional[str] = None
    location: Optional[str] = None
    timezone: Optional[str] = None
    person_type: str = Field(
        default="other",
        description="founder, mentor, staff, operator, partner_contact, other",
    )
    expertise_tags: Optional[str] = Field(
        default=None,
        description="Comma-separated tags in Phase 1.",
    )
    public_facing_ready: bool = False
    speaker_ready: bool = False
    content_ready: bool = False
    active_flag: bool = True
    person_resolution_basis: Optional[str] = Field(
        default=None,
        description="How the person was created, such as structured_field or semi_structured_member_side.",
    )
    source_record_id: Optional[str] = None
    source_system: Optional[str] = None
