"""Tests for the phase-one portfolio reviewed-truth override layer."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.portfolio.pipeline import build_portfolio_snapshot_bundle_from_file
from src.portfolio.reviewed_truth import (
    apply_portfolio_overrides,
    build_portfolio_reviewed_truth_artifact,
    load_portfolio_override_document,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_INPUT_PATH = REPO_ROOT / "data" / "raw" / "portfolio_example" / "acme_phase_one.json"
EXAMPLE_OVERRIDE_PATH = REPO_ROOT / "data" / "reviewed_truth" / "portfolio_example_overrides.json"


def _write_override_file(tmp_path: Path, payload: dict[str, object]) -> Path:
    path = tmp_path / "portfolio_overrides.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def test_portfolio_reviewed_truth_applies_patch_only_example_rules() -> None:
    source_bundle = build_portfolio_snapshot_bundle_from_file(EXAMPLE_INPUT_PATH)
    override_document = load_portfolio_override_document(EXAMPLE_OVERRIDE_PATH)

    reviewed_bundle, applications = apply_portfolio_overrides(source_bundle, override_document)

    reviewed_customer_signal = next(
        item for item in reviewed_bundle["evidence_items"] if item["id"] == "evidence:acme_customer_signal"
    )
    reviewed_customer_score = next(
        item for item in reviewed_bundle["domain_scores"] if item["id"] == "domain_score:org_acme_automation:customer_risk"
    )
    resolved_queue_item = next(
        item for item in reviewed_bundle["review_queue_items"] if item["linked_evidence_item_id"] == "evidence:acme_customer_signal"
    )

    assert reviewed_customer_signal["truth_stage"] == "reviewed_evidence"
    assert reviewed_customer_signal["review_status"] == "reviewed"
    assert reviewed_customer_signal["reviewed_truth_applied"] is True
    assert reviewed_customer_score["raw_score"] == 4
    assert reviewed_customer_score["confidence"] == "moderate"
    assert reviewed_customer_score["score_status"] == "review_ready"
    assert reviewed_bundle["internal_report_draft"]["draft_status"] == "draft"
    assert reviewed_bundle["internal_report_draft"]["review_status"] == "pending_review"
    assert resolved_queue_item["queue_status"] == "resolved"
    assert any(row["matched_count"] == 1 for row in applications)

    reviewed_truth_artifact = build_portfolio_reviewed_truth_artifact(
        override_document=override_document,
        applications=applications,
        snapshot_summary=reviewed_bundle["portfolio_snapshot"],
    )
    assert reviewed_truth_artifact["rule_count"] == 3
    assert reviewed_truth_artifact["applied_rule_count"] == 3


def test_portfolio_reviewed_truth_rejects_suppress_rules(tmp_path: Path) -> None:
    overrides_path = _write_override_file(
        tmp_path,
        {
            "version": 1,
            "rules": [
                {
                    "id": "bad-suppress",
                    "target": "evidence_items",
                    "match": {"id": "evidence:example"},
                    "suppress": True,
                }
            ],
        },
    )

    with pytest.raises(ValueError, match="patch-only"):
        load_portfolio_override_document(overrides_path)


def test_portfolio_reviewed_truth_rejects_external_states(tmp_path: Path) -> None:
    overrides_path = _write_override_file(
        tmp_path,
        {
            "version": 1,
            "rules": [
                {
                    "id": "bad-external-state",
                    "target": "internal_report_draft",
                    "match": {"id": "internal_report:org_example:2026_q2"},
                    "set": {
                        "truth_stage": "externally_approved_output",
                        "review_status": "externally_approved",
                    },
                }
            ],
        },
    )

    with pytest.raises(ValueError, match="cannot use external"):
        load_portfolio_override_document(overrides_path)
