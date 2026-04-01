"""Mentor-specific profile model."""

from __future__ import annotations

from typing import Optional

from sqlmodel import Field, SQLModel


class MentorProfile(SQLModel, table=True):
    """Attributes layered on top of a person record for mentors."""

    __tablename__ = "mentor_profiles"

    id: Optional[int] = Field(default=None, primary_key=True)
    person_id: Optional[int] = Field(default=None, foreign_key="people.id")
    mentor_program_type: Optional[str] = None
    mentor_location_type: Optional[str] = None
    expertise_summary: Optional[str] = None
    share_email_permission: bool = False
    booking_link: Optional[str] = None
    mentor_active_flag: bool = True
    source_record_id: Optional[str] = None
    source_system: Optional[str] = None

