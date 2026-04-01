"""Affiliation join model."""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlmodel import Field, SQLModel


class Affiliation(SQLModel, table=True):
    """Link between a person and an organization."""

    __tablename__ = "affiliations"

    id: Optional[int] = Field(default=None, primary_key=True)
    person_id: Optional[int] = Field(default=None, foreign_key="people.id")
    organization_id: Optional[int] = Field(default=None, foreign_key="organizations.id")
    role_title: Optional[str] = None
    role_category: str = Field(
        default="other",
        description="founder, executive, staff, mentor, sponsor, advisor, other",
    )
    founder_flag: bool = False
    primary_contact_flag: bool = False
    spokesperson_flag: bool = False
    active_flag: bool = True
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    source_record_id: Optional[str] = None
    source_system: Optional[str] = None

