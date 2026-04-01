"""Cohort domain model."""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlmodel import Field, SQLModel


class Cohort(SQLModel, table=True):
    """Program cohort or run."""

    __tablename__ = "cohorts"

    id: Optional[int] = Field(default=None, primary_key=True)
    cohort_name: str
    program_id: Optional[int] = Field(default=None, foreign_key="programs.id")
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    active_flag: bool = True
    source_record_id: Optional[str] = None
    source_system: Optional[str] = None

