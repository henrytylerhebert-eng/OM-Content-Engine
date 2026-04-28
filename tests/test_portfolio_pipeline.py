"""Tests for the runnable local portfolio pipeline."""

import json
from pathlib import Path

from src.portfolio.pipeline import build_portfolio_snapshot_bundle_from_file
from src.reporting.portfolio_pipeline import build_local_portfolio_bundle, main


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_INPUT_PATH = REPO_ROOT / "data" / "raw" / "portfolio_example" / "acme_phase_one.json"
EXAMPLE_OVERRIDE_PATH = REPO_ROOT / "data" / "reviewed_truth" / "portfolio_example_overrides.json"


def test_build_portfolio_snapshot_bundle_from_example_file() -> None:
    bundle = build_portfolio_snapshot_bundle_from_file(EXAMPLE_INPUT_PATH)

    assert bundle["company_name"] == "Acme Automation"
    assert bundle["portfolio_snapshot"]["organization_id"] == "org:acme_automation"
    assert bundle["portfolio_snapshot"]["discovery_source_count"] == 2
    assert bundle["portfolio_snapshot"]["evidence_item_count"] == 2
    assert bundle["portfolio_snapshot"]["reviewed_evidence_count"] == 0
    assert bundle["portfolio_snapshot"]["pending_evidence_count"] == 2
    assert bundle["portfolio_snapshot"]["domain_score_count"] == 2
    assert bundle["portfolio_snapshot"]["review_ready_domain_score_count"] == 0
    assert bundle["portfolio_snapshot"]["capital_readiness_draft_count"] == 2
    assert bundle["portfolio_snapshot"]["review_ready_capital_readiness_draft_count"] == 0
    assert bundle["portfolio_snapshot"]["support_routing_draft_count"] == 1
    assert bundle["portfolio_snapshot"]["review_ready_support_routing_draft_count"] == 0
    assert bundle["portfolio_snapshot"]["milestone_draft_count"] == 1
    assert bundle["portfolio_snapshot"]["review_ready_milestone_draft_count"] == 0
    assert bundle["portfolio_snapshot"]["portfolio_recommendation_draft_status"] == "draft"
    assert any(
        risk.startswith("Product Risk:")
        for risk in bundle["portfolio_recommendation_draft"]["top_risks"]
    )
    assert bundle["founder_report_draft"]["draft_status"] == "draft"
    assert bundle["internal_report_draft"]["draft_status"] == "draft"
    assert all(item["queue_status"] == "open" for item in bundle["review_queue_items"])


def test_build_local_portfolio_bundle_uses_default_example_input_and_overrides() -> None:
    bundle = build_local_portfolio_bundle()

    assert bundle["company_name"] == "Acme Automation"
    assert bundle["portfolio_snapshot"]["organization_id"] == "org:acme_automation"
    assert bundle["portfolio_snapshot"]["report_period"] == "2026-Q2"
    assert bundle["portfolio_snapshot"]["reviewed_evidence_count"] == 1
    assert bundle["portfolio_snapshot"]["review_ready_domain_score_count"] == 1
    assert bundle["portfolio_snapshot"]["support_routing_draft_count"] == 1
    assert bundle["portfolio_snapshot"]["review_ready_support_routing_draft_count"] == 0
    assert bundle["portfolio_snapshot"]["milestone_draft_count"] == 1
    assert bundle["portfolio_snapshot"]["review_ready_milestone_draft_count"] == 0
    assert bundle["portfolio_snapshot"]["portfolio_recommendation_draft_status"] == "draft"
    assert bundle["portfolio_recommendation_draft"]["top_risks"][0].startswith("Product Risk:")
    assert bundle["portfolio_recommendation_draft"]["likely_near_term_capital_path_label"] == "pre-seed venture (emerging draft)"
    assert bundle["founder_report_draft"]["draft_status"] == "draft"
    assert bundle["internal_report_draft"]["draft_status"] == "draft"
    assert bundle["internal_report_draft"]["review_status"] == "pending_review"
    assert "portfolio_reviewed_truth" in bundle


def test_build_local_portfolio_bundle_can_skip_overrides() -> None:
    bundle = build_local_portfolio_bundle(EXAMPLE_INPUT_PATH, overrides_path=None)

    assert bundle["portfolio_snapshot"]["reviewed_evidence_count"] == 0
    assert "portfolio_reviewed_truth" not in bundle


def test_portfolio_pipeline_main_writes_example_outputs(tmp_path: Path) -> None:
    exit_code = main(
        [
            "--input-file",
            str(EXAMPLE_INPUT_PATH),
            "--overrides",
            str(EXAMPLE_OVERRIDE_PATH),
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    assert (tmp_path / "portfolio_snapshot.json").exists()
    assert (tmp_path / "support_routing_drafts.json").exists()
    assert (tmp_path / "milestone_drafts.json").exists()
    assert (tmp_path / "portfolio_recommendation_draft.json").exists()
    assert (tmp_path / "snapshot_manifest.json").exists()
    assert (tmp_path / "portfolio_reviewed_truth.json").exists()

    snapshot = json.loads((tmp_path / "portfolio_snapshot.json").read_text(encoding="utf-8"))
    manifest = json.loads((tmp_path / "snapshot_manifest.json").read_text(encoding="utf-8"))
    reviewed_truth = json.loads((tmp_path / "portfolio_reviewed_truth.json").read_text(encoding="utf-8"))

    assert snapshot["organization_id"] == "org:acme_automation"
    assert snapshot["review_ready_capital_readiness_draft_count"] == 0
    assert snapshot["support_routing_draft_count"] == 1
    assert snapshot["milestone_draft_count"] == 1
    assert snapshot["portfolio_recommendation_draft_status"] == "draft"
    assert manifest["artifact_type"] == "portfolio_snapshot"
    assert manifest["organization_id"] == "org:acme_automation"
    assert reviewed_truth["rule_count"] == 3
