"""Tests for operator-safe portfolio override authoring helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.portfolio.override_authoring import (
    build_domain_score_adjustment_override,
    build_evidence_review_override,
    build_internal_draft_approval_override,
    build_review_queue_resolution_override,
)
from src.portfolio.reviewed_truth import load_portfolio_override_document, upsert_portfolio_override_rule
from src.reporting.portfolio_override_tool import main


def test_upsert_portfolio_override_rule_creates_then_updates_same_evidence_rule(tmp_path: Path) -> None:
    overrides_path = tmp_path / "portfolio_overrides.json"

    first_rule = build_evidence_review_override(
        evidence_id="evidence:acme_customer_signal",
        reviewed_by="portfolio_operator",
        review_notes="Initial evidence review.",
        reviewed_at="2026-04-03T12:00:00+00:00",
    )
    first_result = upsert_portfolio_override_rule(overrides_path, first_rule, description="Phase-one test overrides.")

    second_rule = build_evidence_review_override(
        evidence_id="evidence:acme_customer_signal",
        reviewed_by="portfolio_operator",
        review_notes="Updated evidence review note.",
        reviewed_at="2026-04-04T12:00:00+00:00",
    )
    second_result = upsert_portfolio_override_rule(overrides_path, second_rule)
    document = load_portfolio_override_document(overrides_path)

    assert first_result.action == "created"
    assert second_result.action == "updated"
    assert len(document.rules) == 1
    assert document.description == "Phase-one test overrides."
    assert document.rules[0].rule_id == "review-evidence-acme-customer-signal"
    assert document.rules[0].set_values["review_notes"] == "Updated evidence review note."


def test_upsert_portfolio_override_rule_rejects_target_change_for_existing_rule_id(tmp_path: Path) -> None:
    overrides_path = tmp_path / "portfolio_overrides.json"
    first_rule = build_evidence_review_override(
        evidence_id="evidence:acme_customer_signal",
        reviewed_by="portfolio_operator",
        review_notes="Reviewed.",
        reviewed_at="2026-04-03T12:00:00+00:00",
        rule_id="shared-rule",
    )
    upsert_portfolio_override_rule(overrides_path, first_rule)

    conflicting_rule = build_domain_score_adjustment_override(
        score_id="domain_score:org_acme_automation:customer_risk",
        reviewed_by="portfolio_operator",
        reviewed_at="2026-04-03T12:10:00+00:00",
        raw_score=4,
        rule_id="shared-rule",
    )

    with pytest.raises(ValueError, match="cannot be reassigned"):
        upsert_portfolio_override_rule(overrides_path, conflicting_rule)


def test_domain_score_adjustment_requires_meaningful_score_fields() -> None:
    with pytest.raises(ValueError, match="require at least one score field"):
        build_domain_score_adjustment_override(
            score_id="domain_score:org_acme_automation:customer_risk",
            reviewed_by="portfolio_operator",
            reviewed_at="2026-04-03T12:10:00+00:00",
        )


def test_portfolio_override_tool_writes_domain_score_adjustment_rule(tmp_path: Path) -> None:
    overrides_path = tmp_path / "portfolio_overrides.json"

    exit_code = main(
        [
            "domain-score-adjustment",
            "--overrides-file",
            str(overrides_path),
            "--score-id",
            "domain_score:org_acme_automation:customer_risk",
            "--reviewed-by",
            "portfolio_operator",
            "--reviewed-at",
            "2026-04-03T12:10:00+00:00",
            "--raw-score",
            "4",
            "--confidence",
            "moderate",
            "--evidence-level",
            "3",
            "--score-status",
            "review_ready",
            "--review-notes",
            "Adjusted from reviewed customer evidence.",
        ]
    )

    document = json.loads(overrides_path.read_text(encoding="utf-8"))
    rule = document["rules"][0]

    assert exit_code == 0
    assert rule["target"] == "domain_scores"
    assert rule["set"]["raw_score"] == 4
    assert rule["set"]["confidence"] == "moderate"
    assert rule["set"]["score_status"] == "review_ready"


def test_portfolio_override_tool_writes_queue_resolution_rule(tmp_path: Path) -> None:
    overrides_path = tmp_path / "portfolio_overrides.json"

    exit_code = main(
        [
            "queue-resolution",
            "--overrides-file",
            str(overrides_path),
            "--linked-evidence-item-id",
            "evidence:acme_customer_signal",
            "--reviewed-by",
            "portfolio_operator",
            "--reviewed-at",
            "2026-04-03T12:05:00+00:00",
            "--resolution-note",
            "Evidence promotion completed.",
        ]
    )

    document = json.loads(overrides_path.read_text(encoding="utf-8"))
    rule = document["rules"][0]

    assert exit_code == 0
    assert rule["target"] == "review_queue_items"
    assert rule["match"]["linked_evidence_item_id"] == "evidence:acme_customer_signal"
    assert rule["set"]["queue_status"] == "resolved"


def test_portfolio_override_tool_writes_internal_draft_approval_rule(tmp_path: Path) -> None:
    overrides_path = tmp_path / "portfolio_overrides.json"

    exit_code = main(
        [
            "internal-draft-approval",
            "--overrides-file",
            str(overrides_path),
            "--target",
            "internal_report_draft",
            "--record-id",
            "internal_report:org_acme_automation:2026_q2",
            "--reviewed-by",
            "portfolio_operator",
            "--reviewed-at",
            "2026-04-03T12:20:00+00:00",
            "--review-notes",
            "Approved for internal operating use.",
        ]
    )

    document = json.loads(overrides_path.read_text(encoding="utf-8"))
    rule = document["rules"][0]

    assert exit_code == 0
    assert rule["target"] == "internal_report_draft"
    assert rule["set"]["draft_status"] == "reviewed"
    assert rule["set"]["review_status"] == "internally_approved"
    assert rule["set"]["truth_stage"] == "internally_approved_output"
