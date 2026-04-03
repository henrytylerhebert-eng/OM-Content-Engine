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
DEFAULT_RESULTS_MARKDOWN_NAME = "editorial_assignments_sync_results.md"
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
PATCH_FIELD_NAMES = (
    "recommended_action",
    "source_hook",
    "evidence_summary",
    "suggested_angle",
    "suggested_format",
    "readiness_level",
    "trust_basis",
)
PATCH_FIELD_MAP = {
    local_field: airtable_field
    for local_field, airtable_field in ASSIGNMENT_FIELD_MAP.items()
    if airtable_field in PATCH_FIELD_NAMES
}
AIRTABLE_FIELD_NAMES = list(ASSIGNMENT_FIELD_MAP.values())


class AirtableSyncError(RuntimeError):
    """Raised when an Airtable sync request fails."""


class AirtablePreflightError(AirtableSyncError):
    """Raised when a sync preflight check fails before row writes begin."""

    def __init__(
        self,
        message: str,
        *,
        missing_fields: Optional[Sequence[str]] = None,
        table_name: str = "",
        base_id: str = "",
    ) -> None:
        super().__init__(message)
        self.missing_fields = list(missing_fields or [])
        self.table_name = table_name
        self.base_id = base_id


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


def _format_missing_fields_preflight_error(
    *,
    config: "AirtableSyncConfig",
    table_name: str,
    missing_fields: Sequence[str],
) -> str:
    return "\n".join(
        [
            "Airtable sync preflight failed.",
            "Base ID: %s" % config.base_id,
            "Table: %s" % table_name,
            "Missing fields: %s" % ", ".join(missing_fields),
            "Add the missing Airtable field(s) and rerun sync.",
        ]
    )


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


def _build_airtable_fields(
    assignment: dict[str, object],
    *,
    field_map: Optional[dict[str, str]] = None,
) -> dict[str, str]:
    fields: dict[str, str] = {}
    for local_field, airtable_field in (field_map or ASSIGNMENT_FIELD_MAP).items():
        fields[airtable_field] = _stringify_field_value(local_field, assignment.get(local_field))
    return fields


def _normalize_remote_fields(fields: dict[str, object], *, field_names: Sequence[str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for name in field_names:
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


def _status_counts(result_rows: Sequence[dict[str, object]]) -> dict[str, int]:
    counts = {
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "skipped": 0,
        "failed": 0,
    }
    for row in result_rows:
        status = str(row.get("status") or "")
        if status in counts:
            counts[status] += 1
    return counts


def _top_reason_counts(
    result_rows: Sequence[dict[str, object]],
    *,
    statuses: Sequence[str] = ("skipped", "failed"),
    limit: int = 5,
) -> list[dict[str, object]]:
    reason_counts: dict[tuple[str, str, str], int] = {}
    for row in result_rows:
        status = str(row.get("status") or "")
        if status not in statuses:
            continue
        reason = str(row.get("reason") or "").strip()
        reason_summary = str(row.get("reason_summary") or "").strip()
        key = (status, reason, reason_summary)
        reason_counts[key] = reason_counts.get(key, 0) + 1

    ranked = sorted(
        reason_counts.items(),
        key=lambda item: (-item[1], item[0][0], item[0][2], item[0][1]),
    )
    return [
        {
            "status": status,
            "reason": reason,
            "reason_summary": reason_summary,
            "count": count,
        }
        for (status, reason, reason_summary), count in ranked[:limit]
    ]


def _top_changed_rows(
    result_rows: Sequence[dict[str, object]],
    *,
    limit: int = 5,
) -> list[dict[str, object]]:
    rows = [
        row
        for row in result_rows
        if list(row.get("changed_machine_fields") or [])
    ]
    ranked = sorted(
        rows,
        key=lambda row: (
            0 if str(row.get("status") or "") == "updated" else 1,
            str(row.get("assignment_id") or ""),
        ),
    )
    top_rows: list[dict[str, object]] = []
    for row in ranked[:limit]:
        top_rows.append(
            {
                "assignment_id": str(row.get("assignment_id") or ""),
                "status": str(row.get("status") or ""),
                "airtable_record_id": str(row.get("airtable_record_id") or row.get("record_id") or ""),
                "changed_machine_fields": list(row.get("changed_machine_fields") or []),
                "reason_summary": str(row.get("reason_summary") or ""),
            }
        )
    return top_rows


def _aggregate_visibility_summary(result_rows: Sequence[dict[str, object]]) -> dict[str, object]:
    status_counts = _status_counts(result_rows)
    return {
        "status_counts": status_counts,
        "rows_with_changed_machine_fields_count": sum(
            1 for row in result_rows if list(row.get("changed_machine_fields") or [])
        ),
        "overwrite_used_count": sum(1 for row in result_rows if bool(row.get("overwrite_used"))),
        "skipped_row_count": status_counts["skipped"],
        "top_skip_failure_reasons": _top_reason_counts(result_rows),
        "top_changed_rows": _top_changed_rows(result_rows),
    }


def _empty_visibility_summary() -> dict[str, object]:
    return {
        "status_counts": {
            "created": 0,
            "updated": 0,
            "unchanged": 0,
            "skipped": 0,
            "failed": 0,
        },
        "rows_with_changed_machine_fields_count": 0,
        "overwrite_used_count": 0,
        "skipped_row_count": 0,
        "top_skip_failure_reasons": [],
        "top_changed_rows": [],
    }


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


def _record_status(action: str) -> str:
    return "failed" if action == "errors" else action


def _compact_reason(reason: str) -> str:
    reason_map = {
        "created_in_airtable": "created in Airtable",
        "already_matches_local_source": "already matches local sync-owned fields",
        "remote_fields_changed_since_last_sync": "remote sync-owned fields changed since last sync",
        "existing_airtable_record_has_manual_values": "existing Airtable row has manual values",
        "remote_record_updated": "remote sync-owned fields updated",
        "missing_assignment_id": "missing assignment_id in local row",
    }
    return reason_map.get(reason, reason.replace("_", " ").strip())


def _changed_machine_fields(before: dict[str, str], after: dict[str, str]) -> list[str]:
    return [field_name for field_name in PATCH_FIELD_NAMES if before.get(field_name) != after.get(field_name)]


def _result_row(
    *,
    assignment_id: str,
    action: str,
    record_id: str,
    reason: str,
    changed_machine_fields: Optional[Sequence[str]] = None,
    overwrite_used: bool = False,
) -> dict[str, object]:
    return {
        "assignment_id": assignment_id,
        "action": action,
        "status": _record_status(action),
        "record_id": record_id,
        "airtable_record_id": record_id,
        "reason": reason,
        "reason_summary": _compact_reason(reason),
        "changed_machine_fields": list(changed_machine_fields or []),
        "overwrite_used": overwrite_used,
    }


def _build_failed_preflight_result(
    *,
    run_dir: Path,
    source_file: Path,
    results_path: Path,
    state_path: Path,
    error_message: str,
    editorial_assignments_table: str,
    sync_logs_table: str,
    base_id: str = "",
    missing_fields: Optional[Sequence[str]] = None,
    assignments: Optional[Sequence[dict[str, object]]] = None,
    force_overwrite: bool = False,
    allow_overwrite_ids: Optional[Sequence[str]] = None,
) -> dict[str, object]:
    started_at = _utc_timestamp()
    finished_at = _utc_timestamp()
    results_markdown_path = results_path.with_name(DEFAULT_RESULTS_MARKDOWN_NAME)
    summary = _empty_visibility_summary()
    missing_field_list = list(missing_fields or [])
    if error_message:
        summary["top_skip_failure_reasons"] = [
            {
                "status": "failed",
                "reason": "preflight_failed",
                "reason_summary": error_message,
                "count": 1,
            }
        ]
    return {
        "sync_name": SYNC_NAME,
        "status": "failed_preflight",
        "generated_at": finished_at,
        "started_at": started_at,
        "finished_at": finished_at,
        "source_file": str(source_file),
        "rows_read": len(assignments or []),
        "run_dir": str(run_dir),
        "base_id": base_id,
        "editorial_assignments_table": editorial_assignments_table,
        "sync_logs_table": sync_logs_table,
        "force_overwrite": force_overwrite,
        "allow_overwrite_ids": sorted(
            str(value).strip() for value in (allow_overwrite_ids or []) if str(value).strip()
        ),
        "counts": {
            "created": 0,
            "updated": 0,
            "unchanged": 0,
            "skipped": 0,
            "errors": 1,
        },
        "summary": summary,
        "records": [],
        "state_file": str(state_path),
        "results_file": str(results_path),
        "results_markdown_file": str(results_markdown_path),
        "error_message": error_message,
        "missing_fields": missing_field_list,
    }


def _write_sync_results_artifacts(sync_result: dict[str, object], results_path: Path) -> None:
    results_markdown_path = Path(
        str(sync_result.get("results_markdown_file") or results_path.with_name(DEFAULT_RESULTS_MARKDOWN_NAME))
    )
    results_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.write_text(json.dumps(sync_result, indent=2) + "\n", encoding="utf-8")
    results_markdown_path.write_text(render_sync_results_markdown(sync_result), encoding="utf-8")


def render_sync_results_markdown(sync_result: dict[str, object]) -> str:
    """Render a compact markdown companion for the sync results artifact."""

    counts = dict(sync_result.get("counts", {}))
    summary = dict(sync_result.get("summary", {}))
    rows = list(sync_result.get("records", []))
    lines = [
        "# Editorial Assignments Sync Results",
        "",
        "- Sync status: `%s`" % (sync_result.get("status") or "completed"),
        "- Generated at: `%s`" % sync_result.get("generated_at"),
        "- Source file: `%s`" % sync_result.get("source_file"),
        "- Destination table: `%s`" % sync_result.get("editorial_assignments_table"),
        "- Started at: `%s`" % sync_result.get("started_at"),
        "- Finished at: `%s`" % sync_result.get("finished_at"),
        "- Rows read: `%s`" % sync_result.get("rows_read", 0),
        "- Counts: `created=%s`, `updated=%s`, `unchanged=%s`, `skipped=%s`, `failed=%s`"
        % (
            counts.get("created", 0),
            counts.get("updated", 0),
            counts.get("unchanged", 0),
            counts.get("skipped", 0),
            counts.get("errors", 0),
        ),
        "- Status counts: `created=%s`, `updated=%s`, `unchanged=%s`, `skipped=%s`, `failed=%s`"
        % (
            dict(summary.get("status_counts", {})).get("created", 0),
            dict(summary.get("status_counts", {})).get("updated", 0),
            dict(summary.get("status_counts", {})).get("unchanged", 0),
            dict(summary.get("status_counts", {})).get("skipped", 0),
            dict(summary.get("status_counts", {})).get("failed", 0),
        ),
        "- Rows with machine-field changes: `%s`" % summary.get("rows_with_changed_machine_fields_count", 0),
        "- Rows requiring overwrite: `%s`" % summary.get("overwrite_used_count", 0),
        "",
    ]
    base_id = str(sync_result.get("base_id") or "").strip()
    if base_id:
        lines.insert(5, "- Base ID: `%s`" % base_id)
    error_message = str(sync_result.get("error_message") or "").strip()
    if error_message:
        lines.append("- Error: %s" % error_message)
    missing_fields = [str(value).strip() for value in sync_result.get("missing_fields", []) if str(value).strip()]
    if missing_fields:
        lines.append("- Missing fields: `%s`" % ", ".join(missing_fields))
    if error_message or missing_fields:
        lines.append("")

    top_reasons = list(summary.get("top_skip_failure_reasons", []))
    lines.append("## Top Skip/Failure Reasons")
    lines.append("")
    if not top_reasons:
        lines.append("_None_")
    else:
        for row in top_reasons:
            lines.append(
                "- `%s` x%s: %s"
                % (row.get("status"), row.get("count"), row.get("reason_summary"))
            )
    lines.append("")

    top_changed_rows = list(summary.get("top_changed_rows", []))
    lines.append("## Top Changed Rows")
    lines.append("")
    if not top_changed_rows:
        lines.append("_None_")
        lines.append("")
    else:
        for row in top_changed_rows:
            lines.append("### %s" % (row.get("assignment_id") or "unknown"))
            lines.append("")
            lines.append("- Status: `%s`" % row.get("status"))
            record_id = str(row.get("airtable_record_id") or "").strip()
            if record_id:
                lines.append("- Airtable record id: `%s`" % record_id)
            changed_machine_fields = list(row.get("changed_machine_fields", []))
            if changed_machine_fields:
                lines.append("- Changed machine fields: `%s`" % ", ".join(changed_machine_fields))
            lines.append("- Reason: %s" % row.get("reason_summary"))
            lines.append("")

    sections = [
        ("Updated Rows", [row for row in rows if row.get("status") == "updated"]),
        ("Skipped Rows", [row for row in rows if row.get("status") == "skipped"]),
        ("Failed Rows", [row for row in rows if row.get("status") == "failed"]),
    ]

    for title, section_rows in sections:
        lines.append("## %s" % title)
        lines.append("")
        if not section_rows:
            lines.append("_None_")
            lines.append("")
            continue
        for row in section_rows:
            lines.append("### %s" % (row.get("assignment_id") or "unknown"))
            lines.append("")
            record_id = str(row.get("airtable_record_id") or row.get("record_id") or "").strip()
            if record_id:
                lines.append("- Airtable record id: `%s`" % record_id)
            changed_machine_fields = list(row.get("changed_machine_fields", []))
            if changed_machine_fields:
                lines.append("- Changed machine fields: `%s`" % ", ".join(changed_machine_fields))
            if row.get("overwrite_used"):
                lines.append("- Overwrite used: `true`")
            lines.append("- Reason: %s" % row.get("reason_summary"))
            lines.append("")

    return "\n".join(lines).strip() + "\n"


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

    def _metadata_url(self) -> str:
        return "%s/meta/bases/%s/tables" % (
            self.config.api_url.rstrip("/"),
            quote(self.config.base_id, safe=""),
        )

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

    def _request_url(
        self,
        method: str,
        url: str,
        *,
        table_name: str,
        record_id: Optional[str] = None,
        params: Optional[dict[str, object]] = None,
        payload: Optional[dict[str, object]] = None,
    ) -> dict[str, object]:
        if params:
            query = urlencode(params, doseq=True)
            if query:
                separator = "&" if "?" in url else "?"
                url = "%s%s%s" % (url, separator, query)
        data: Optional[bytes] = None
        headers = {
            "Authorization": "Bearer %s" % self.config.token,
            "Accept": "application/json",
        }
        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(payload).encode("utf-8")
        request = Request(url, data=data, headers=headers, method=method)
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

    def _request(
        self,
        method: str,
        table_name: str,
        *,
        record_id: Optional[str] = None,
        params: Optional[dict[str, object]] = None,
        payload: Optional[dict[str, object]] = None,
    ) -> dict[str, object]:
        return self._request_url(
            method,
            self._url(table_name, record_id=record_id),
            table_name=table_name,
            record_id=record_id,
            params=params,
            payload=payload,
        )

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

    def get_table_field_names(self, table_name: str) -> list[str]:
        payload = self._request_url(
            "GET",
            self._metadata_url(),
            table_name=table_name,
        )
        tables = payload.get("tables", [])
        if not isinstance(tables, list):
            raise AirtableSyncError(
                "Airtable metadata lookup returned an unexpected table payload for %s." % table_name
            )
        for table in tables:
            if not isinstance(table, dict):
                continue
            if str(table.get("name") or "").strip() != table_name:
                continue
            fields = table.get("fields", [])
            if not isinstance(fields, list):
                raise AirtableSyncError(
                    "Airtable metadata lookup returned an unexpected field payload for %s." % table_name
                )
            return [
                str(field.get("name") or "").strip()
                for field in fields
                if isinstance(field, dict) and str(field.get("name") or "").strip()
            ]
        raise AirtableSyncError(
            "Airtable metadata lookup did not find table %s in base %s."
            % (table_name, self.config.base_id)
        )

    def ensure_required_fields(self, table_name: str, *, required_fields: Sequence[str]) -> None:
        present_field_names = set(self.get_table_field_names(table_name))
        missing_fields = [field_name for field_name in required_fields if field_name not in present_field_names]
        if missing_fields:
            raise AirtablePreflightError(
                _format_missing_fields_preflight_error(
                    config=self.config,
                    table_name=table_name,
                    missing_fields=missing_fields,
                ),
                missing_fields=missing_fields,
                table_name=table_name,
                base_id=self.config.base_id,
            )


def _build_remote_lookup(records: Sequence[dict[str, object]]) -> tuple[dict[str, dict[str, object]], set[str]]:
    by_assignment_id: dict[str, dict[str, object]] = {}
    duplicates: set[str] = set()
    for record in records:
        fields = _normalize_remote_fields(dict(record.get("fields", {})), field_names=AIRTABLE_FIELD_NAMES)
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
    results_markdown_path = results_path.with_name(DEFAULT_RESULTS_MARKDOWN_NAME)

    state = _load_sync_state(state_path)
    state_records = dict(state.get("records", {}))

    client.ensure_required_fields(editorial_table, required_fields=AIRTABLE_FIELD_NAMES)
    remote_records = client.list_records(editorial_table, fields=AIRTABLE_FIELD_NAMES)
    remote_lookup, duplicate_assignment_ids = _build_remote_lookup(remote_records)
    if duplicate_assignment_ids:
        raise AirtableSyncError(
            "Duplicate assignment_id rows found in Airtable table %s: %s"
            % (editorial_table, ", ".join(sorted(duplicate_assignment_ids)))
        )

    result_rows: list[dict[str, object]] = []
    next_state_records = dict(state_records)

    for assignment in assignments:
        assignment_fields = dict(assignment)
        desired_fields = _build_airtable_fields(assignment_fields)
        desired_patch_fields = _build_airtable_fields(assignment_fields, field_map=PATCH_FIELD_MAP)
        assignment_id = desired_fields["assignment_id"]
        if not assignment_id:
            result_rows.append(_result_row(
                assignment_id="",
                action="errors",
                record_id="",
                reason="missing_assignment_id",
            ))
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
                "last_synced_fields": desired_patch_fields,
                "synced_at": _utc_timestamp(),
            }
            result_rows.append(_result_row(
                assignment_id=assignment_id,
                action="created",
                record_id=record_id,
                reason="created_in_airtable",
            ))
            continue

        record_id = str(remote_record.get("id") or "")
        remote_fields = _normalize_remote_fields(
            dict(remote_record.get("fields", {})),
            field_names=AIRTABLE_FIELD_NAMES,
        )
        remote_patch_fields = _normalize_remote_fields(
            dict(remote_record.get("fields", {})),
            field_names=PATCH_FIELD_NAMES,
        )
        changed_machine_fields = _changed_machine_fields(remote_patch_fields, desired_patch_fields)
        if remote_patch_fields == desired_patch_fields:
            next_state_records[assignment_id] = {
                "record_id": record_id,
                "last_synced_fields": desired_patch_fields,
                "synced_at": _utc_timestamp(),
            }
            result_rows.append(_result_row(
                assignment_id=assignment_id,
                action="unchanged",
                record_id=record_id,
                reason="already_matches_local_source",
            ))
            continue

        last_synced_fields = _normalize_remote_fields(
            dict(state_record.get("last_synced_fields", {})),
            field_names=PATCH_FIELD_NAMES,
        )
        if state_record and last_synced_fields != remote_patch_fields and not overwrite_allowed:
            result_rows.append(_result_row(
                assignment_id=assignment_id,
                action="skipped",
                record_id=record_id,
                reason="remote_fields_changed_since_last_sync",
                changed_machine_fields=changed_machine_fields,
            ))
            continue

        if not state_record and _has_non_primary_remote_values(remote_fields) and not overwrite_allowed:
            result_rows.append(_result_row(
                assignment_id=assignment_id,
                action="skipped",
                record_id=record_id,
                reason="existing_airtable_record_has_manual_values",
                changed_machine_fields=changed_machine_fields,
            ))
            continue

        overwrite_used = False
        if state_record and last_synced_fields != remote_patch_fields:
            overwrite_used = overwrite_allowed
        elif not state_record and _has_non_primary_remote_values(remote_fields):
            overwrite_used = overwrite_allowed
        updated = client.update_record(editorial_table, record_id, desired_patch_fields)
        remote_lookup[assignment_id] = dict(updated)
        next_state_records[assignment_id] = {
            "record_id": str(updated.get("id") or record_id),
            "last_synced_fields": desired_patch_fields,
            "synced_at": _utc_timestamp(),
        }
        result_rows.append(_result_row(
            assignment_id=assignment_id,
            action="updated",
            record_id=str(updated.get("id") or record_id),
            reason="remote_record_updated",
            changed_machine_fields=changed_machine_fields,
            overwrite_used=overwrite_used,
        ))

    counts = _summarize_counts(result_rows)
    finished_at = _utc_timestamp()
    notes = _log_notes(result_rows)
    summary = _aggregate_visibility_summary(result_rows)

    sync_result = {
        "sync_name": SYNC_NAME,
        "generated_at": finished_at,
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
        "summary": summary,
        "records": result_rows,
        "state_file": str(state_path),
        "results_file": str(results_path),
        "results_markdown_file": str(results_markdown_path),
    }

    _write_sync_state(
        state_path,
        {
            "version": 1,
            "records": next_state_records,
        },
    )

    _write_sync_results_artifacts(sync_result, results_path)

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
    _write_sync_results_artifacts(sync_result, results_path)
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

    run_dir = Path(args.run_dir)
    input_file = Path(args.input_file) if args.input_file else run_dir / OUTPUT_JSON_NAME
    results_path = Path(args.results_file) if args.results_file else run_dir / DEFAULT_RESULTS_NAME
    state_path = Path(args.state_file)
    assignments: list[dict[str, object]] = []
    config: Optional[AirtableSyncConfig] = None

    try:
        if not input_file.exists():
            raise AirtableSyncError("Missing editorial assignments input file: %s" % input_file)

        assignments = load_editorial_assignments(input_file)
        config = AirtableSyncConfig.from_env()
        client = AirtableClient(config)
        sync_result = sync_editorial_assignments(
            assignments,
            client=client,
            source_file=input_file,
            run_dir=run_dir,
            state_path=state_path,
            results_path=results_path,
            force_overwrite=args.force_overwrite,
            allow_overwrite_ids=args.allow_overwrite_id,
        )
    except AirtableSyncError as exc:
        if isinstance(exc, AirtablePreflightError):
            failed_result = _build_failed_preflight_result(
                run_dir=run_dir,
                source_file=input_file,
                results_path=results_path,
                state_path=state_path,
                error_message=str(exc),
                editorial_assignments_table=(
                    exc.table_name
                    or (config.editorial_assignments_table if config else DEFAULT_EDITORIAL_ASSIGNMENTS_TABLE)
                ),
                sync_logs_table=config.sync_logs_table if config else DEFAULT_SYNC_LOGS_TABLE,
                base_id=exc.base_id or (config.base_id if config else os.getenv("AIRTABLE_BASE_ID", "").strip()),
                missing_fields=exc.missing_fields,
                assignments=assignments,
                force_overwrite=args.force_overwrite,
                allow_overwrite_ids=args.allow_overwrite_id,
            )
            _write_sync_results_artifacts(failed_result, results_path)
        print("Editorial Assignments Airtable Sync Failed", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1

    print(render_sync_summary(sync_result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
