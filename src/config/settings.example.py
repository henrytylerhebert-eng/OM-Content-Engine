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

