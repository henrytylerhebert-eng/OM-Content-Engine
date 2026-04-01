"""Participation join model."""

from __future__ import annotations

from typing import Optional

from sqlmodel import Field, SQLModel


class Participation(SQLModel, table=True):
    """Person or organization participation in a cohort."""

    __tablename__ = "participation"

    id: Optional[int] = Field(default=None, primary_key=True)
    person_id: Optional[int] = Field(default=None, foreign_key="people.id")
    organization_id: Optional[int] = Field(default=None, foreign_key="organizations.id")
    cohort_id: Optional[int] = Field(default=None, foreign_key="cohorts.id")
    participation_status: str = Field(
        default="unknown",
        description="active, alumni, pending, withdrawn, unknown",
    )
    notes: Optional[str] = None
    source_record_id: Optional[str] = None
    source_system: Optional[str] = None

