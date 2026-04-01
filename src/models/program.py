"""Program domain model."""

from __future__ import annotations

from typing import Optional

from sqlmodel import Field, SQLModel


class Program(SQLModel, table=True):
    """Program record for a reusable OM program."""

    __tablename__ = "programs"

    id: Optional[int] = Field(default=None, primary_key=True)
    program_name: str
    program_type: Optional[str] = None
    active_flag: bool = True
    source_record_id: Optional[str] = None
    source_system: Optional[str] = None

