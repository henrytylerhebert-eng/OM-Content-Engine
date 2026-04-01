"""One-way sync of editorial assignments into Airtable for team visibility."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from src.reporting.editorial_assignments import DEFAULT_RUN_DIR, OUTPUT_JSON_NAME


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SYNC_STATE_PATH = REPO_ROOT / "data" / "processed" / "airtable_sync" / "editorial_assignments_state.json"
DEFAULT_RESULTS_NAME = "editorial_assignments_sync_results.json"
DEFAULT_AIRTABLE_API_URL = os.getenv("AIRTABLE_API_URL", "https://api.airtable.com/v0")
DEFAULT_EDITORIAL_ASSIGNMENTS_TABLE = os.getenv(
    "AIRTABLE_EDITORIAL_ASSIGNMENTS_TABLE",
    "Editorial Assignments",
)
DEFAULT_SYNC_LOGS_TABLE = os.getenv(
    "AIRTABLE_SYNC_LOGS_TABLE",
    "Data Source Sync Logs",
)
SYNC_NAME = "editorial_assignments_sync"
ASSIGNMENT_FIELD_MAP = {
    "assignment_id": "assignment_id",
    "entity_id": "entity_id",
    "org_name": "org_name",
    "primary_person_name": "primary_person_name",
    "bucket": "bucket",
    "brief_status": "brief_status",
    "readiness_level": "readiness_level",
    "trust_basis": "trust_basis",
    "public_ready": "public_ready",
    "suggested_angle": "suggested_angle",
    "suggested_format": "suggested_format",
    "recommended_action": "recommended_action",
    "owner": "owner",
    "assignment_status": "assignment_status",
    "priority": "priority",
    "target_cycle": "target_cycle",
    "next_step": "next_step",
    "blocking_notes": "blocking_notes",
    "source_hook": "source_hook",
    "evidence_summary": "evidence_summary",
}
SYNC_FIELD_NAMES = list(ASSIGNMENT_FIELD_MAP.values())


class AirtableSyncError(RuntimeError):
    """Raised when an Airtable sync request fails."""


def _extract_airtable_error_type(details: str) -> str:
    try:
        payload = json.loads(details)
    except (TypeError, ValueError):
        payload = {}
    error = payload.get("error", {})
    if isinstance(error, dict):
        error_type = str(error.get("type") or "").strip()
        if error_type:
            return error_type
    if "INVALID_PERMISSIONS_OR_MODEL_NOT_FOUND" in str(details):
        return "INVALID_PERMISSIONS_OR_MODEL_NOT_FOUND"
    return ""


def _extract_airtable_error_message(details: str) -> str:
    try:
        payload = json.loads(details)
    except (TypeError, ValueError):
        payload = {}
    error = payload.get("error", {})
    if isinstance(error, dict):
        message = str(error.get("message") or "").strip()
        if message:
            return message
    return str(details or "").strip()


def _format_airtable_http_error(
    *,
    method: str,
    table_name: str,
    config: "AirtableSyncConfig",
    status_code: int,
    details: str,
) -> str:
    error_type = _extract_airtable_error_type(details)
    error_message = _extract_airtable_error_message(details)

    lines = [
        "Airtable %s failed." % method,
        "Base ID: %s" % config.base_id,
        "Table: %s" % table_name,
        "HTTP status: %s" % status_code,
    ]
    if error_type:
        lines.append("Airtable error type: %s" % error_type)
    if error_message:
        lines.append("Airtable message: %s" % error_message)

    if error_type == "INVALID_PERMISSIONS_OR_MODEL_NOT_FOUND":
        lines.append(
            "Looks like permissions or model-not-found: check base access for AIRTABLE_TOKEN and confirm the table name exists exactly as configured."
        )
    elif status_code == 403:
        lines.append("Looks like a permissions issue for this base or table.")
    elif status_code == 404:
        lines.append("Looks like the base or table name was not found.")

    return "\n".join(lines)


@dataclass(frozen=True)
class AirtableSyncConfig:
    """Small, explicit Airtable sync settings surface."""

    token: str
    base_id: str
    api_url: str = DEFAULT_AIRTABLE_API_URL
    editorial_assignments_table: str = DEFAULT_EDITORIAL_ASSIGNMENTS_TABLE
    sync_logs_table: str = DEFAULT_SYNC_LOGS_TABLE

    @classmethod
    def from_env(cls) -> "AirtableSyncConfig":
        token = os.getenv("AIRTABLE_TOKEN", "").strip()
        base_id = os.getenv("AIRTABLE_BASE_ID", "").strip()
        if not token:
            raise AirtableSyncError("Missing AIRTABLE_TOKEN in the environment.")
        if not base_id:
            raise AirtableSyncError("Missing AIRTABLE_BASE_ID in the environment.")
        return cls(token=token, base_id=base_id)


def _utc_timestamp() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _load_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_editorial_assignments(path: Path) -> list[dict[str, object]]:
    """Load the local editorial assignment tracker that remains source of truth."""

    data = _load_json(path)
    if not isinstance(data, list):
        raise AirtableSyncError("Expected a list of assignment rows in %s." % path)
    for row in data:
        if not isinstance(row, dict):
            raise AirtableSyncError("Expected assignment rows to be objects in %s." % path)
    return [dict(row) for row in data]


def _stringify_field_value(field_name: str, value: object) -> str:
    if field_name == "public_ready":
        return "true" if bool(value) else "false"
    return str(value or "").strip()


def _build_airtable_fields(assignment: dict[str, object]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for local_field, airtable_field in ASSIGNMENT_FIELD_MAP.items():
        fields[airtable_field] = _stringify_field_value(local_field, assignment.get(local_field))
    return fields


def _normalize_remote_fields(fields: dict[str, object]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for name in SYNC_FIELD_NAMES:
        value = fields.get(name)
        if isinstance(value, bool):
            normalized[name] = "true" if value else "false"
        else:
            normalized[name] = str(value or "").strip()
    return normalized


def _has_non_primary_remote_values(fields: dict[str, str]) -> bool:
    return any(value for key, value in fields.items() if key != "assignment_id")


def _load_sync_state(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"version": 1, "records": {}}
    payload = _load_json(path)
    records = payload.get("records", {})
    if not isinstance(records, dict):
        records = {}
    return {
        "version": int(payload.get("version", 1) or 1),
        "records": dict(records),
    }


def _write_sync_state(path: Path, state: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def _summarize_counts(result_rows: Sequence[dict[str, object]]) -> dict[str, int]:
    counts = {
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "skipped": 0,
        "errors": 0,
    }
    for row in result_rows:
        action = str(row.get("action") or "")
        if action in counts:
            counts[action] += 1
    return counts


def _log_notes(result_rows: Sequence[dict[str, object]]) -> str:
    skipped = [row for row in result_rows if row.get("action") == "skipped"]
    errors = [row for row in result_rows if row.get("action") == "errors"]
    notes: list[str] = []
    if skipped:
        notes.append("skipped=%s" % len(skipped))
    if errors:
        notes.append("errors=%s" % len(errors))
    examples = [str(row.get("reason") or "").strip() for row in skipped[:3] if row.get("reason")]
    if examples:
        notes.append("examples=%s" % "; ".join(examples))
    return " | ".join(notes)


def render_sync_summary(sync_result: dict[str, object]) -> str:
    """Render a compact operator-facing sync summary."""

    counts = dict(sync_result.get("counts", {}))
    lines = [
        "Editorial Assignments Airtable Sync Complete",
        "Source file: %s" % sync_result.get("source_file"),
        "Rows read: %s" % sync_result.get("rows_read", 0),
        "Rows created: %s" % counts.get("created", 0),
        "Rows updated: %s" % counts.get("updated", 0),
        "Rows unchanged: %s" % counts.get("unchanged", 0),
        "Rows skipped: %s" % counts.get("skipped", 0),
        "Rows failed: %s" % counts.get("errors", 0),
        "Destination table: %s" % sync_result.get("editorial_assignments_table"),
    ]
    results_file = str(sync_result.get("results_file") or "").strip()
    if results_file:
        lines.append("Results log: %s" % results_file)
    return "\n".join(lines)


class AirtableClient:
    """Minimal Airtable REST client for inspectable one-way syncs."""

    def __init__(
        self,
        config: AirtableSyncConfig,
        *,
        opener: Optional[Callable[..., object]] = None,
    ) -> None:
        self.config = config
        self._opener = opener or urlopen

    def _url(
        self,
        table_name: str,
        *,
        record_id: Optional[str] = None,
        params: Optional[dict[str, object]] = None,
    ) -> str:
        segments = [
            self.config.api_url.rstrip("/"),
            quote(self.config.base_id, safe=""),
            quote(table_name, safe=""),
        ]
        if record_id:
            segments.append(quote(record_id, safe=""))
        url = "/".join(segments)
        if params:
            query = urlencode(params, doseq=True)
            if query:
                url = "%s?%s" % (url, query)
        return url

    def _request(
        self,
        method: str,
        table_name: str,
        *,
        record_id: Optional[str] = None,
        params: Optional[dict[str, object]] = None,
        payload: Optional[dict[str, object]] = None,
    ) -> dict[str, object]:
        data: Optional[bytes] = None
        headers = {
            "Authorization": "Bearer %s" % self.config.token,
            "Accept": "application/json",
        }
        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(payload).encode("utf-8")
        request = Request(
            self._url(table_name, record_id=record_id, params=params),
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with self._opener(request) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise AirtableSyncError(
                _format_airtable_http_error(
                    method=method,
                    table_name=table_name,
                    config=self.config,
                    status_code=exc.code,
                    details=details,
                )
            ) from exc
        except URLError as exc:
            raise AirtableSyncError("Airtable request failed: %s" % exc.reason) from exc
        if not body:
            return {}
        return dict(json.loads(body))

    def list_records(self, table_name: str, *, fields: Sequence[str]) -> list[dict[str, object]]:
        records: list[dict[str, object]] = []
        offset: Optional[str] = None
        while True:
            params: dict[str, object] = {"fields[]": list(fields)}
            if offset:
                params["offset"] = offset
            payload = self._request("GET", table_name, params=params)
            records.extend(payload.get("records", []))
            offset = payload.get("offset")
            if not offset:
                return records

    def create_record(self, table_name: str, fields: dict[str, object]) -> dict[str, object]:
        return self._request("POST", table_name, payload={"fields": fields, "typecast": True})

    def update_record(self, table_name: str, record_id: str, fields: dict[str, object]) -> dict[str, object]:
        return self._request(
            "PATCH",
            table_name,
            record_id=record_id,
            payload={"fields": fields, "typecast": True},
        )


def _build_remote_lookup(records: Sequence[dict[str, object]]) -> tuple[dict[str, dict[str, object]], set[str]]:
    by_assignment_id: dict[str, dict[str, object]] = {}
    duplicates: set[str] = set()
    for record in records:
        fields = _normalize_remote_fields(dict(record.get("fields", {})))
        assignment_id = fields.get("assignment_id", "")
        if not assignment_id:
            continue
        if assignment_id in by_assignment_id:
            duplicates.add(assignment_id)
            continue
        by_assignment_id[assignment_id] = dict(record)
    return by_assignment_id, duplicates


def _overwrite_allowed(
    assignment_id: str,
    *,
    force_overwrite: bool,
    allow_overwrite_ids: set[str],
) -> bool:
    return force_overwrite or assignment_id in allow_overwrite_ids


def sync_editorial_assignments(
    assignments: Sequence[dict[str, object]],
    *,
    client: AirtableClient,
    source_file: Path,
    run_dir: Path,
    state_path: Path = DEFAULT_SYNC_STATE_PATH,
    results_path: Optional[Path] = None,
    force_overwrite: bool = False,
    allow_overwrite_ids: Optional[Sequence[str]] = None,
    editorial_assignments_table: Optional[str] = None,
    sync_logs_table: Optional[str] = None,
) -> dict[str, object]:
    """Upsert local assignment rows into Airtable while protecting manual edits."""

    started_at = _utc_timestamp()
    allow_overwrite_id_set = {str(value).strip() for value in allow_overwrite_ids or [] if str(value).strip()}
    editorial_table = editorial_assignments_table or client.config.editorial_assignments_table
    logs_table = sync_logs_table or client.config.sync_logs_table
    results_path = results_path or (run_dir / DEFAULT_RESULTS_NAME)

    state = _load_sync_state(state_path)
    state_records = dict(state.get("records", {}))

    remote_records = client.list_records(editorial_table, fields=SYNC_FIELD_NAMES)
    remote_lookup, duplicate_assignment_ids = _build_remote_lookup(remote_records)
    if duplicate_assignment_ids:
        raise AirtableSyncError(
            "Duplicate assignment_id rows found in Airtable table %s: %s"
            % (editorial_table, ", ".join(sorted(duplicate_assignment_ids)))
        )

    result_rows: list[dict[str, object]] = []
    next_state_records = dict(state_records)

    for assignment in assignments:
        desired_fields = _build_airtable_fields(dict(assignment))
        assignment_id = desired_fields["assignment_id"]
        if not assignment_id:
            result_rows.append(
                {
                    "assignment_id": "",
                    "action": "errors",
                    "record_id": "",
                    "reason": "missing_assignment_id",
                }
            )
            continue

        remote_record = remote_lookup.get(assignment_id)
        state_record = dict(state_records.get(assignment_id, {}))
        overwrite_allowed = _overwrite_allowed(
            assignment_id,
            force_overwrite=force_overwrite,
            allow_overwrite_ids=allow_overwrite_id_set,
        )

        if remote_record is None:
            created = client.create_record(editorial_table, desired_fields)
            record_id = str(created.get("id") or "")
            remote_lookup[assignment_id] = dict(created)
            next_state_records[assignment_id] = {
                "record_id": record_id,
                "last_synced_fields": desired_fields,
                "synced_at": _utc_timestamp(),
            }
            result_rows.append(
                {
                    "assignment_id": assignment_id,
                    "action": "created",
                    "record_id": record_id,
                    "reason": "created_in_airtable",
                }
            )
            continue

        record_id = str(remote_record.get("id") or "")
        remote_fields = _normalize_remote_fields(dict(remote_record.get("fields", {})))
        if remote_fields == desired_fields:
            next_state_records[assignment_id] = {
                "record_id": record_id,
                "last_synced_fields": desired_fields,
                "synced_at": _utc_timestamp(),
            }
            result_rows.append(
                {
                    "assignment_id": assignment_id,
                    "action": "unchanged",
                    "record_id": record_id,
                    "reason": "already_matches_local_source",
                }
            )
            continue

        last_synced_fields = _normalize_remote_fields(dict(state_record.get("last_synced_fields", {})))
        if state_record and last_synced_fields != remote_fields and not overwrite_allowed:
            result_rows.append(
                {
                    "assignment_id": assignment_id,
                    "action": "skipped",
                    "record_id": record_id,
                    "reason": "remote_fields_changed_since_last_sync",
                }
            )
            continue

        if not state_record and _has_non_primary_remote_values(remote_fields) and not overwrite_allowed:
            result_rows.append(
                {
                    "assignment_id": assignment_id,
                    "action": "skipped",
                    "record_id": record_id,
                    "reason": "existing_airtable_record_has_manual_values",
                }
            )
            continue

        updated = client.update_record(editorial_table, record_id, desired_fields)
        remote_lookup[assignment_id] = dict(updated)
        next_state_records[assignment_id] = {
            "record_id": str(updated.get("id") or record_id),
            "last_synced_fields": desired_fields,
            "synced_at": _utc_timestamp(),
        }
        result_rows.append(
            {
                "assignment_id": assignment_id,
                "action": "updated",
                "record_id": str(updated.get("id") or record_id),
                "reason": "remote_record_updated",
            }
        )

    counts = _summarize_counts(result_rows)
    finished_at = _utc_timestamp()
    notes = _log_notes(result_rows)

    sync_result = {
        "sync_name": SYNC_NAME,
        "started_at": started_at,
        "finished_at": finished_at,
        "source_file": str(source_file),
        "rows_read": len(assignments),
        "run_dir": str(run_dir),
        "editorial_assignments_table": editorial_table,
        "sync_logs_table": logs_table,
        "force_overwrite": force_overwrite,
        "allow_overwrite_ids": sorted(allow_overwrite_id_set),
        "counts": counts,
        "records": result_rows,
        "state_file": str(state_path),
        "results_file": str(results_path),
    }

    _write_sync_state(
        state_path,
        {
            "version": 1,
            "records": next_state_records,
        },
    )

    results_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.write_text(json.dumps(sync_result, indent=2) + "\n", encoding="utf-8")

    log_fields = {
        "sync_name": SYNC_NAME,
        "source_file_path": str(source_file),
        "started_at": started_at,
        "finished_at": finished_at,
        "status": "completed_with_errors" if counts["errors"] or counts["skipped"] else "success",
        "created_count": counts["created"],
        "updated_count": counts["updated"],
        "unchanged_count": counts["unchanged"],
        "skipped_count": counts["skipped"],
        "error_count": counts["errors"],
        "force_overwrite": "yes" if force_overwrite else "no",
        "notes": notes,
    }
    created_log = client.create_record(logs_table, log_fields)
    sync_result["sync_log_record_id"] = str(created_log.get("id") or "")
    results_path.write_text(json.dumps(sync_result, indent=2) + "\n", encoding="utf-8")
    return sync_result


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Sync the local editorial assignment tracker into Airtable."""

    parser = argparse.ArgumentParser(
        description="One-way sync the local editorial assignment tracker into Airtable.",
    )
    parser.add_argument(
        "--run-dir",
        default=str(DEFAULT_RUN_DIR),
        help="Run directory containing editorial_assignments.json.",
    )
    parser.add_argument(
        "--input-file",
        default="",
        help="Optional explicit editorial_assignments.json path. Defaults to <run-dir>/editorial_assignments.json.",
    )
    parser.add_argument(
        "--state-file",
        default=str(DEFAULT_SYNC_STATE_PATH),
        help="Local sync-state path used to protect manual Airtable edits.",
    )
    parser.add_argument(
        "--results-file",
        default="",
        help="Optional explicit sync-results JSON path. Defaults to <run-dir>/editorial_assignments_sync_results.json.",
    )
    parser.add_argument(
        "--force-overwrite",
        action="store_true",
        help="Allow local source-of-truth values to overwrite remote Airtable edits for all assignments.",
    )
    parser.add_argument(
        "--allow-overwrite-id",
        action="append",
        default=[],
        help="Allow local overwrite for a specific assignment_id without forcing every row.",
    )
    args = parser.parse_args(argv)

    try:
        run_dir = Path(args.run_dir)
        input_file = Path(args.input_file) if args.input_file else run_dir / OUTPUT_JSON_NAME
        if not input_file.exists():
            raise AirtableSyncError("Missing editorial assignments input file: %s" % input_file)

        config = AirtableSyncConfig.from_env()
        client = AirtableClient(config)
        sync_result = sync_editorial_assignments(
            load_editorial_assignments(input_file),
            client=client,
            source_file=input_file,
            run_dir=run_dir,
            state_path=Path(args.state_file),
            results_path=Path(args.results_file) if args.results_file else None,
            force_overwrite=args.force_overwrite,
            allow_overwrite_ids=args.allow_overwrite_id,
        )
    except AirtableSyncError as exc:
        print("Editorial Assignments Airtable Sync Failed", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1

    print(render_sync_summary(sync_result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
