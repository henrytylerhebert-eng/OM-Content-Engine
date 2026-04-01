"""Tests for the Airtable sync layer over editorial assignments."""

import json
import os
from io import BytesIO
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from typing import Optional
from urllib.error import HTTPError

import pytest

from src.reporting.editorial_assignments_airtable_sync import (
    AirtableClient,
    AirtableSyncConfig,
    AirtableSyncError,
    render_sync_summary,
    sync_editorial_assignments,
)


def _assignment(**overrides: object) -> dict[str, object]:
    row = {
        "assignment_id": "assignment:needs_review:person_jane_acme_ai",
        "entity_id": "person:jane_acme_ai",
        "org_name": "Acme AI",
        "primary_person_name": "Jane Founder",
        "bucket": "needs_review",
        "brief_status": "planning_safe_only",
        "readiness_level": "spotlight_ready",
        "trust_basis": "heuristic_only",
        "public_ready": False,
        "suggested_angle": "founder_journey",
        "suggested_format": "mini_feature",
        "recommended_action": "apply_reviewed_truth_override",
        "owner": "",
        "target_cycle": "next_week",
        "assignment_status": "not_started",
        "priority": "medium",
        "blocking_notes": "",
        "next_step": "apply_reviewed_truth_override",
        "source_hook": "A founder story worth validating.",
        "evidence_summary": "org_type=startup; founder; website",
    }
    row.update(overrides)
    return row


class FakeAirtableClient:
    """In-memory Airtable double for sync tests."""

    def __init__(self, remote_records: Optional[list[dict[str, object]]] = None) -> None:
        self.config = SimpleNamespace(
            editorial_assignments_table="Editorial Assignments",
            sync_logs_table="Data Source Sync Logs",
        )
        self._records_by_id = {
            str(record["id"]): {
                "id": str(record["id"]),
                "fields": dict(record.get("fields", {})),
            }
            for record in remote_records or []
        }
        self.log_records: list[dict[str, object]] = []

    def list_records(self, table_name: str, *, fields: list[str]) -> list[dict[str, object]]:
        if table_name == self.config.editorial_assignments_table:
            return list(self._records_by_id.values())
        if table_name == self.config.sync_logs_table:
            return list(self.log_records)
        raise AssertionError("Unexpected table name: %s" % table_name)

    def create_record(self, table_name: str, fields: dict[str, object]) -> dict[str, object]:
        if table_name == self.config.sync_logs_table:
            record = {
                "id": "log_%s" % (len(self.log_records) + 1),
                "fields": dict(fields),
            }
            self.log_records.append(record)
            return record
        record_id = "rec_%s" % (len(self._records_by_id) + 1)
        record = {
            "id": record_id,
            "fields": dict(fields),
        }
        self._records_by_id[record_id] = record
        return record

    def update_record(self, table_name: str, record_id: str, fields: dict[str, object]) -> dict[str, object]:
        if table_name != self.config.editorial_assignments_table:
            raise AssertionError("Unexpected update table: %s" % table_name)
        record = {
            "id": record_id,
            "fields": dict(fields),
        }
        self._records_by_id[record_id] = record
        return record


def run_cli(*args: str, env: Optional[dict[str, str]] = None) -> SimpleNamespace:
    repo_root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [sys.executable, "-m", "src.reporting.editorial_assignments_airtable_sync", *args],
        cwd=str(repo_root),
        env=env or os.environ.copy(),
        capture_output=True,
        text=True,
    )
    return SimpleNamespace(
        exit_code=completed.returncode,
        output=completed.stdout + completed.stderr,
    )


def test_sync_creates_new_airtable_assignment_and_log(tmp_path: Path) -> None:
    client = FakeAirtableClient()
    source_file = tmp_path / "editorial_assignments.json"
    source_file.write_text(json.dumps([_assignment()]), encoding="utf-8")

    result = sync_editorial_assignments(
        [_assignment()],
        client=client,
        source_file=source_file,
        run_dir=tmp_path,
        state_path=tmp_path / "state.json",
    )

    assert result["counts"]["created"] == 1
    assert result["counts"]["skipped"] == 0
    assert len(client.log_records) == 1
    created = next(iter(client._records_by_id.values()))
    assert created["fields"]["assignment_id"] == "assignment:needs_review:person_jane_acme_ai"
    assert created["fields"]["entity_id"] == "person:jane_acme_ai"
    assert created["fields"]["primary_person_name"] == "Jane Founder"
    assert created["fields"]["bucket"] == "needs_review"
    assert created["fields"]["brief_status"] == "planning_safe_only"
    assert created["fields"]["readiness_level"] == "spotlight_ready"
    assert created["fields"]["trust_basis"] == "heuristic_only"
    assert created["fields"]["public_ready"] == "false"
    assert created["fields"]["suggested_angle"] == "founder_journey"
    assert created["fields"]["recommended_action"] == "apply_reviewed_truth_override"
    assert created["fields"]["priority"] == "medium"
    assert created["fields"]["target_cycle"] == "next_week"
    assert created["fields"]["next_step"] == "apply_reviewed_truth_override"
    assert created["fields"]["blocking_notes"] == ""
    assert created["fields"]["source_hook"] == "A founder story worth validating."
    assert created["fields"]["evidence_summary"] == "org_type=startup; founder; website"
    assert created["fields"]["assignment_status"] == "not_started"
    assert "person_name" not in created["fields"]
    assert "status" not in created["fields"]
    assert (tmp_path / "editorial_assignments_sync_results.json").exists()
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert state["records"]["assignment:needs_review:person_jane_acme_ai"]["record_id"] == created["id"]


def test_sync_skips_remote_manual_edit_without_explicit_overwrite(tmp_path: Path) -> None:
    assignment = _assignment(assignment_status="in_progress")
    remote_record = {
        "id": "rec_1",
        "fields": {
            "assignment_id": assignment["assignment_id"],
            "org_name": "Acme AI",
            "primary_person_name": "Jane Founder",
            "bucket": "needs_review",
            "owner": "",
            "assignment_status": "shipped",
            "priority": "medium",
            "target_cycle": "next_week",
            "next_step": "draft_feature",
            "blocking_notes": "",
        },
    }
    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps(
            {
                "version": 1,
                "records": {
                    assignment["assignment_id"]: {
                        "record_id": "rec_1",
                        "last_synced_fields": {
                            "assignment_id": assignment["assignment_id"],
                            "org_name": "Acme AI",
                            "primary_person_name": "Jane Founder",
                            "bucket": "needs_review",
                            "owner": "",
                            "assignment_status": "not_started",
                            "priority": "medium",
                            "target_cycle": "next_week",
                            "next_step": "apply_reviewed_truth_override",
                            "blocking_notes": "",
                        },
                        "synced_at": "2026-04-01T00:00:00Z",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    client = FakeAirtableClient([remote_record])
    source_file = tmp_path / "editorial_assignments.json"
    source_file.write_text(json.dumps([assignment]), encoding="utf-8")

    result = sync_editorial_assignments(
        [assignment],
        client=client,
        source_file=source_file,
        run_dir=tmp_path,
        state_path=state_path,
    )

    assert result["counts"]["skipped"] == 1
    assert result["records"][0]["reason"] == "remote_fields_changed_since_last_sync"
    assert client._records_by_id["rec_1"]["fields"]["assignment_status"] == "shipped"


def test_sync_allows_per_assignment_overwrite_when_explicitly_requested(tmp_path: Path) -> None:
    assignment = _assignment(assignment_status="in_progress", owner="tylerhebert")
    remote_record = {
        "id": "rec_1",
        "fields": {
            "assignment_id": assignment["assignment_id"],
            "org_name": "Acme AI",
            "primary_person_name": "Jane Founder",
            "bucket": "needs_review",
            "owner": "",
            "assignment_status": "shipped",
            "priority": "medium",
            "target_cycle": "next_week",
            "next_step": "draft_feature",
            "blocking_notes": "",
        },
    }
    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps(
            {
                "version": 1,
                "records": {
                    assignment["assignment_id"]: {
                        "record_id": "rec_1",
                        "last_synced_fields": {
                            "assignment_id": assignment["assignment_id"],
                            "org_name": "Acme AI",
                            "primary_person_name": "Jane Founder",
                            "bucket": "needs_review",
                            "owner": "",
                            "assignment_status": "not_started",
                            "priority": "medium",
                            "target_cycle": "next_week",
                            "next_step": "apply_reviewed_truth_override",
                            "blocking_notes": "",
                        },
                        "synced_at": "2026-04-01T00:00:00Z",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    client = FakeAirtableClient([remote_record])
    source_file = tmp_path / "editorial_assignments.json"
    source_file.write_text(json.dumps([assignment]), encoding="utf-8")

    result = sync_editorial_assignments(
        [assignment],
        client=client,
        source_file=source_file,
        run_dir=tmp_path,
        state_path=state_path,
        allow_overwrite_ids=[str(assignment["assignment_id"])],
    )

    assert result["counts"]["updated"] == 1
    assert client._records_by_id["rec_1"]["fields"]["assignment_status"] == "in_progress"
    assert client._records_by_id["rec_1"]["fields"]["owner"] == "tylerhebert"


def test_sync_skips_existing_manual_airtable_row_without_state(tmp_path: Path) -> None:
    assignment = _assignment()
    remote_record = {
        "id": "rec_1",
        "fields": {
            "assignment_id": assignment["assignment_id"],
            "org_name": "Acme AI",
            "primary_person_name": "Jane Founder",
            "bucket": "use_now",
            "owner": "manual_owner",
            "assignment_status": "drafted",
            "priority": "high",
            "target_cycle": "this_week",
            "next_step": "manual_follow_up",
            "blocking_notes": "Manual Airtable note",
        },
    }
    client = FakeAirtableClient([remote_record])
    source_file = tmp_path / "editorial_assignments.json"
    source_file.write_text(json.dumps([assignment]), encoding="utf-8")

    result = sync_editorial_assignments(
        [assignment],
        client=client,
        source_file=source_file,
        run_dir=tmp_path,
        state_path=tmp_path / "state.json",
    )

    assert result["counts"]["skipped"] == 1
    assert result["records"][0]["reason"] == "existing_airtable_record_has_manual_values"
    assert client._records_by_id["rec_1"]["fields"]["owner"] == "manual_owner"


def test_sync_fails_on_duplicate_assignment_ids_in_airtable(tmp_path: Path) -> None:
    assignment = _assignment()
    remote_records = [
        {
            "id": "rec_1",
            "fields": {
                "assignment_id": assignment["assignment_id"],
            },
        },
        {
            "id": "rec_2",
            "fields": {
                "assignment_id": assignment["assignment_id"],
            },
        },
    ]
    client = FakeAirtableClient(remote_records)
    source_file = tmp_path / "editorial_assignments.json"
    source_file.write_text(json.dumps([assignment]), encoding="utf-8")

    with pytest.raises(AirtableSyncError) as exc_info:
        sync_editorial_assignments(
            [assignment],
            client=client,
            source_file=source_file,
            run_dir=tmp_path,
            state_path=tmp_path / "state.json",
        )

    assert "Duplicate assignment_id rows found in Airtable table Editorial Assignments" in str(exc_info.value)


def test_render_sync_summary_is_operator_facing() -> None:
    rendered = render_sync_summary(
        {
            "source_file": "data/processed/local_run/editorial_assignments.json",
            "rows_read": 7,
            "editorial_assignments_table": "Editorial Assignments",
            "results_file": "data/processed/local_run/editorial_assignments_sync_results.json",
            "counts": {
                "created": 2,
                "updated": 3,
                "unchanged": 1,
                "skipped": 1,
                "errors": 0,
            },
        }
    )

    assert rendered.startswith("Editorial Assignments Airtable Sync Complete")
    assert "Rows read: 7" in rendered
    assert "Rows created: 2" in rendered
    assert "Destination table: Editorial Assignments" in rendered


def test_sync_rerun_is_idempotent(tmp_path: Path) -> None:
    """A second sync of the same data must produce all-unchanged with zero creates."""

    assignment = _assignment()
    client = FakeAirtableClient()
    source_file = tmp_path / "editorial_assignments.json"
    source_file.write_text(json.dumps([assignment]), encoding="utf-8")
    state_path = tmp_path / "state.json"

    first = sync_editorial_assignments(
        [assignment],
        client=client,
        source_file=source_file,
        run_dir=tmp_path,
        state_path=state_path,
    )

    assert first["counts"]["created"] == 1

    second = sync_editorial_assignments(
        [assignment],
        client=client,
        source_file=source_file,
        run_dir=tmp_path,
        state_path=state_path,
    )

    assert second["counts"]["created"] == 0
    assert second["counts"]["updated"] == 0
    assert second["counts"]["unchanged"] == 1
    assert second["counts"]["skipped"] == 0
    assert second["counts"]["errors"] == 0
    assert len(client._records_by_id) == 1


def test_missing_airtable_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The CLI must fail cleanly when Airtable config is missing."""

    source_file = tmp_path / "editorial_assignments.json"
    source_file.write_text(json.dumps([_assignment()]), encoding="utf-8")

    monkeypatch.delenv("AIRTABLE_TOKEN", raising=False)
    monkeypatch.delenv("AIRTABLE_BASE_ID", raising=False)

    result = run_cli(
        "--run-dir", str(tmp_path),
        "--input-file", str(source_file),
        env=os.environ.copy(),
    )

    assert result.exit_code != 0
    assert "Editorial Assignments Airtable Sync Failed" in result.output
    assert "Missing AIRTABLE_TOKEN" in result.output


def test_airtable_http_error_includes_base_table_and_diagnosis() -> None:
    def failing_opener(request: object) -> object:
        raise HTTPError(
            url=str(getattr(request, "full_url", "")),
            code=403,
            msg="Forbidden",
            hdrs=None,
            fp=BytesIO(
                b'{"error":{"type":"INVALID_PERMISSIONS_OR_MODEL_NOT_FOUND","message":"Invalid permissions, or the requested model was not found."}}'
            ),
        )

    client = AirtableClient(
        AirtableSyncConfig(
            token="test-token",
            base_id="appExample123",
            editorial_assignments_table="Editorial Assignments",
            sync_logs_table="Data Source Sync Logs",
        ),
        opener=failing_opener,
    )

    with pytest.raises(AirtableSyncError) as exc_info:
        client.list_records("Editorial Assignments", fields=["assignment_id"])

    message = str(exc_info.value)
    assert "Base ID: appExample123" in message
    assert "Table: Editorial Assignments" in message
    assert "Airtable error type: INVALID_PERMISSIONS_OR_MODEL_NOT_FOUND" in message
    assert "Looks like permissions or model-not-found" in message
