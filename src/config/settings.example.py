"""Example local settings.

Copy this file to `settings.py` if a project-specific configuration file is
needed later. For now, environment variables are enough.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    """Small, explicit settings surface for the first pass."""

    database_url: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{ROOT_DIR / 'data' / 'om_content_engine.db'}",
    )
    raw_data_dir: Path = ROOT_DIR / "data" / "raw"
    processed_data_dir: Path = ROOT_DIR / "data" / "processed"
    default_source_system: str = os.getenv("SOURCE_SYSTEM", "airtable_export")
    airtable_token: str = os.getenv("AIRTABLE_TOKEN", "")
    airtable_base_id: str = os.getenv("AIRTABLE_BASE_ID", "")
    airtable_api_url: str = os.getenv("AIRTABLE_API_URL", "https://api.airtable.com/v0")
    airtable_editorial_assignments_table: str = os.getenv(
        "AIRTABLE_EDITORIAL_ASSIGNMENTS_TABLE",
        "Editorial Assignments",
    )
    airtable_sync_logs_table: str = os.getenv(
        "AIRTABLE_SYNC_LOGS_TABLE",
        "Data Source Sync Logs",
    )
