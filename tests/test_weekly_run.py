"""Tests for the weekly operator runner."""

from pathlib import Path

import pytest

from src.reporting.demo_pipeline import build_demo_bundle, write_demo_outputs
from src.reporting.weekly_run import (
    build_weekly_run_summary,
    render_weekly_run_summary,
    verify_expected_outputs,
)


def test_weekly_run_summary_uses_existing_snapshot_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("AIRTABLE_TOKEN", raising=False)
    monkeypatch.delenv("AIRTABLE_BASE_ID", raising=False)
    monkeypatch.delenv("AIRTABLE_EDITORIAL_ASSIGNMENTS_TABLE", raising=False)
    monkeypatch.delenv("AIRTABLE_SYNC_LOGS_TABLE", raising=False)

    bundle = build_demo_bundle()
    write_demo_outputs(bundle, tmp_path)

    summary = build_weekly_run_summary(tmp_path)
    rendered = render_weekly_run_summary(summary)

    assert summary["candidate_count"] >= 1
    assert summary["brief_count"] >= 1
    assert summary["assignment_count"] >= 1
    assert summary["needs_review_count"] >= 1
    assert rendered.startswith("Weekly Operator Run Complete")
    assert "Open first:" in rendered
    assert "- snapshot_manifest.json" in rendered
    assert "Operator Notes:" in rendered
    assert "No use_now items." in rendered
    assert "Jane Founder (Acme AI) x2" in rendered
    assert "Airtable Sync: NOT CONFIGURED" in rendered


def test_weekly_run_summary_reports_configured_airtable_sync(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AIRTABLE_TOKEN", "test-token")
    monkeypatch.setenv("AIRTABLE_BASE_ID", "appExample123")
    monkeypatch.setenv("AIRTABLE_EDITORIAL_ASSIGNMENTS_TABLE", "Editorial Assignments")
    monkeypatch.setenv("AIRTABLE_SYNC_LOGS_TABLE", "Data Source Sync Logs")

    bundle = build_demo_bundle()
    write_demo_outputs(bundle, tmp_path)

    summary = build_weekly_run_summary(tmp_path)
    rendered = render_weekly_run_summary(summary)

    assert summary["airtable_ready"] is True
    assert "Airtable Sync: READY (base appExample123, tables: Editorial Assignments / Data Source Sync Logs)" in rendered


def test_weekly_run_verification_fails_when_expected_output_is_missing(tmp_path: Path) -> None:
    bundle = build_demo_bundle()
    write_demo_outputs(bundle, tmp_path)
    (tmp_path / "editorial_assignments.md").unlink()

    with pytest.raises(FileNotFoundError) as exc_info:
        verify_expected_outputs(tmp_path)

    assert "editorial_assignments.md" in str(exc_info.value)
