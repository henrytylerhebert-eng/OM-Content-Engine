"""Interaction domain model."""

from __future__ import annotations

from datetime import date as date_type
from typing import Optional

from sqlmodel import Field, SQLModel


class Interaction(SQLModel, table=True):
    """Engagement history record."""

    __tablename__ = "interactions"

    id: Optional[int] = Field(default=None, primary_key=True)
    person_id: Optional[int] = Field(default=None, foreign_key="people.id")
    organization_id: Optional[int] = Field(default=None, foreign_key="organizations.id")
    interaction_type: str
    date: Optional[date_type] = None
    owner: Optional[str] = None
    notes: Optional[str] = None
    follow_up_date: Optional[date_type] = None
    source_record_id: Optional[str] = None
    source_system: Optional[str] = None
