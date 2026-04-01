"""Organization domain model."""

from __future__ import annotations

from typing import Optional

from sqlmodel import Field, SQLModel


class Organization(SQLModel, table=True):
    """Normalized organization record."""

    __tablename__ = "organizations"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    org_type: str = Field(
        default="other",
        description="startup, partner, internal, university, investor, mentor_org, service_provider, government, nonprofit, other, unknown",
    )
    membership_status: Optional[str] = None
    membership_tier: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    stage: Optional[str] = None
    headquarters_location: Optional[str] = None
    active_flag: bool = True
    source_record_id: Optional[str] = None
    source_system: Optional[str] = None
    content_eligible: bool = False
    spotlight_priority: int = 0
