"""Helpers for landing Airtable exports into the raw source layer."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Optional, Sequence, Union


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


def _stringify_cell_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        return ", ".join(_stringify_cell_value(item) for item in value if _stringify_cell_value(item))
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True, default=str)
    return str(value).strip()


def build_raw_import_records(
    rows: Sequence[Mapping[str, object]],
    *,
    source_table: str,
    source_system: str,
    file_path: str,
) -> list[RawImportRecord]:
    """Convert row dictionaries into RawImportRecord entries with consistent provenance."""

    imported_at = datetime.now(timezone.utc).isoformat()
    records: list[RawImportRecord] = []

    for row in rows:
        cleaned = {
            str(key).strip(): _stringify_cell_value(value)
            for key, value in row.items()
            if str(key).strip()
        }
        source_record_id = (
            cleaned.get("Record ID")
            or cleaned.get("Airtable Record ID")
            or cleaned.get("id")
            or None
        )
        if source_record_id:
            cleaned.setdefault("Record ID", source_record_id)
            cleaned.setdefault("Airtable Record ID", source_record_id)
        records.append(
            RawImportRecord(
                source_system=source_system,
                source_table=source_table,
                source_record_id=source_record_id,
                imported_at=imported_at,
                file_path=file_path,
                row_hash=_row_hash(cleaned),
                raw=cleaned,
            )
        )

    return records


def load_airtable_csv_export(
    file_path: Union[str, Path],
    source_table: Optional[str] = None,
    source_system: str = "airtable_export",
) -> list[RawImportRecord]:
    """Read a CSV export and preserve enough metadata for replay or review."""

    path = Path(file_path)
    table_name = source_table or path.stem

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return build_raw_import_records(
            list(reader),
            source_table=table_name,
            source_system=source_system,
            file_path=str(path),
        )


def records_to_json_ready(records: list[RawImportRecord]) -> list[dict[str, object]]:
    """Convert dataclasses into plain dictionaries for logging or serialization."""

    return [asdict(record) for record in records]
