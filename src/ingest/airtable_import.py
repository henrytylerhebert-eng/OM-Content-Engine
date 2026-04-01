"""Helpers for landing Airtable exports into the raw source layer."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union


@dataclass(frozen=True)
class RawImportRecord:
    """Single landed raw record plus source metadata."""

    source_system: str
    source_table: str
    source_record_id: Optional[str]
    imported_at: str
    file_path: str
    row_hash: str
    raw: dict[str, str]


def _row_hash(row: dict[str, str]) -> str:
    payload = json.dumps(row, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_airtable_csv_export(
    file_path: Union[str, Path],
    source_table: Optional[str] = None,
    source_system: str = "airtable_export",
) -> list[RawImportRecord]:
    """Read a CSV export and preserve enough metadata for replay or review."""

    path = Path(file_path)
    table_name = source_table or path.stem
    imported_at = datetime.now(timezone.utc).isoformat()
    records: list[RawImportRecord] = []

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            cleaned = {key.strip(): (value or "").strip() for key, value in row.items()}
            source_record_id = (
                cleaned.get("Record ID")
                or cleaned.get("Airtable Record ID")
                or cleaned.get("id")
                or None
            )
            records.append(
                RawImportRecord(
                    source_system=source_system,
                    source_table=table_name,
                    source_record_id=source_record_id,
                    imported_at=imported_at,
                    file_path=str(path),
                    row_hash=_row_hash(cleaned),
                    raw=cleaned,
                )
            )

    return records


def records_to_json_ready(records: list[RawImportRecord]) -> list[dict[str, object]]:
    """Convert dataclasses into plain dictionaries for logging or serialization."""

    return [asdict(record) for record in records]
