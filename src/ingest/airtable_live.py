"""Read-only Airtable ingest helpers for on-demand pipeline runs."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from src.ingest.airtable_import import RawImportRecord, build_raw_import_records


DEFAULT_AIRTABLE_API_URL = os.getenv("AIRTABLE_API_URL", "https://api.airtable.com/v0")
DEFAULT_ACTIVE_MEMBERS_TABLE = os.getenv("AIRTABLE_ACTIVE_MEMBERS_TABLE", "Active Members")
DEFAULT_MENTORS_TABLE = os.getenv("AIRTABLE_MENTORS_TABLE", "Mentors")
DEFAULT_COHORTS_TABLE = os.getenv("AIRTABLE_COHORTS_TABLE", "Cohorts")


class AirtableReadError(RuntimeError):
    """Raised when the read-only Airtable ingest path fails."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        table_name: str = "",
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.table_name = table_name


@dataclass(frozen=True)
class AirtableReadConfig:
    """Minimal Airtable config surface for live read-only pipeline runs."""

    token: str
    base_id: str
    api_url: str = DEFAULT_AIRTABLE_API_URL

    @classmethod
    def from_env(cls) -> "AirtableReadConfig":
        token = os.getenv("AIRTABLE_TOKEN", "").strip()
        base_id = os.getenv("AIRTABLE_BASE_ID", "").strip()
        if not token:
            raise AirtableReadError("Missing AIRTABLE_TOKEN in the environment.")
        if not base_id:
            raise AirtableReadError("Missing AIRTABLE_BASE_ID in the environment.")
        return cls(token=token, base_id=base_id)


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


class AirtableReadClient:
    """Small read-only Airtable REST client for live ingest."""

    def __init__(self, config: AirtableReadConfig, *, opener: Optional[object] = None) -> None:
        self.config = config
        self._opener = opener or urlopen

    def _url(self, table_name: str, *, params: Optional[dict[str, object]] = None) -> str:
        url = "/".join(
            [
                self.config.api_url.rstrip("/"),
                quote(self.config.base_id, safe=""),
                quote(table_name, safe=""),
            ]
        )
        if params:
            query = urlencode(params, doseq=True)
            if query:
                url = "%s?%s" % (url, query)
        return url

    def _request(self, table_name: str, *, params: Optional[dict[str, object]] = None) -> dict[str, object]:
        request = Request(
            self._url(table_name, params=params),
            headers={
                "Authorization": "Bearer %s" % self.config.token,
                "Accept": "application/json",
            },
            method="GET",
        )
        try:
            with self._opener(request) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise AirtableReadError(
                "Airtable read failed.\nBase ID: %s\nTable: %s\nHTTP status: %s\nAirtable message: %s"
                % (
                    self.config.base_id,
                    table_name,
                    exc.code,
                    _extract_airtable_error_message(details),
                ),
                status_code=exc.code,
                table_name=table_name,
            ) from exc
        except URLError as exc:
            raise AirtableReadError("Airtable read failed: %s" % exc.reason) from exc

        if not body:
            return {}
        return dict(json.loads(body))

    def list_records(self, table_name: str) -> list[dict[str, object]]:
        records: list[dict[str, object]] = []
        offset: Optional[str] = None
        while True:
            params: dict[str, object] = {}
            if offset:
                params["offset"] = offset
            payload = self._request(table_name, params=params)
            chunk = payload.get("records", [])
            if not isinstance(chunk, list):
                raise AirtableReadError("Unexpected Airtable record payload for table %s." % table_name)
            records.extend(dict(record) for record in chunk if isinstance(record, dict))
            offset = payload.get("offset")
            if not offset:
                return records


def load_airtable_live_records(
    client: AirtableReadClient,
    *,
    table_name: str,
    required: bool = True,
) -> list[RawImportRecord]:
    """Load a live Airtable table into RawImportRecord rows for the pipeline."""

    try:
        records = client.list_records(table_name)
    except AirtableReadError as exc:
        message = str(exc).lower()
        if not required and (
            exc.status_code == 404
            or "not found" in message
            or "model was not found" in message
        ):
            return []
        raise

    rows: list[dict[str, object]] = []
    for record in records:
        fields = record.get("fields", {})
        if not isinstance(fields, dict):
            continue
        row = dict(fields)
        record_id = str(record.get("id") or "").strip()
        if record_id:
            row.setdefault("Record ID", record_id)
            row.setdefault("Airtable Record ID", record_id)
            row.setdefault("id", record_id)
        rows.append(row)

    return build_raw_import_records(
        rows,
        source_table=table_name,
        source_system="airtable_live",
        file_path="airtable://%s/%s" % (client.config.base_id, table_name),
    )
