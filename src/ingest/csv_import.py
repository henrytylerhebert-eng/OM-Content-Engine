"""Helpers for landing non-Airtable CSV exports into the raw source layer."""

from __future__ import annotations

from pathlib import Path
from typing import Union

from src.ingest.airtable_import import RawImportRecord, load_airtable_csv_export


def load_csv_export(
    file_path: Union[str, Path],
    source_table: str,
    source_system: str = "csv_sync",
) -> list[RawImportRecord]:
    """Load a generic CSV export using the same landed record shape."""

    return load_airtable_csv_export(
        file_path=file_path,
        source_table=source_table,
        source_system=source_system,
    )
