"""Tests for Airtable-aligned portfolio operational export helpers."""

from __future__ import annotations

import json

from src.portfolio.airtable_contract import (
    build_portfolio_airtable_operational_export,
    build_portfolio_airtable_example_summary,
    portfolio_airtable_operational_export_from_payload,
    portfolio_airtable_operational_export_to_payload,
    write_portfolio_airtable_operational_exports,
)
from src.reporting.portfolio_operational_export import main
from src.reporting.portfolio_pipeline import build_local_portfolio_bundle


def test_build_portfolio_airtable_operational_export_from_example_bundle() -> None:
    bundle = build_local_portfolio_bundle()
    export_bundle = build_portfolio_airtable_operational_export(bundle)

    assert export_bundle.organization_id == "org:acme_automation"
    assert len(export_bundle.companies) == 1
    assert export_bundle.companies[0].company_name == "Acme Automation"
    assert export_bundle.companies[0].company_name_inferred is False
    assert len(export_bundle.evidence_items) == 2
    assert len(export_bundle.assumptions) == 2
    assert len(export_bundle.domain_scores) == 2
    assert len(export_bundle.capital_readiness) == 2
    assert len(export_bundle.support_routing) == 1
    assert len(export_bundle.action_items) == 4
    assert len(export_bundle.milestones) == 1

    reviewed_evidence = next(item for item in export_bundle.evidence_items if item.id == "evidence:acme_customer_signal")
    reviewed_score = next(
        item for item in export_bundle.domain_scores if item.id == "domain_score:org_acme_automation:customer_risk"
    )
    internal_support_route = export_bundle.support_routing[0]
    milestone = export_bundle.milestones[0]

    assert reviewed_evidence.truth_stage == "reviewed_evidence"
    assert reviewed_evidence.reviewed_truth_applied is True
    assert reviewed_score.raw_score == 4
    assert reviewed_score.score_status == "review_ready"
    assert internal_support_route.operational_status == "draft_projection"
    assert internal_support_route.route_recommendation == "Route product onboarding support before capital introductions."
    assert internal_support_route.route_source_type == "support_routing_draft"
    assert milestone.source_record_type == "milestone_draft"
    assert milestone.milestone_text == "Validate onboarding improvements with the next three pilots."
    assert export_bundle.companies[0].founder_report_draft_status == "draft"
    assert export_bundle.companies[0].internal_report_draft_status == "draft"


def test_support_routing_and_milestones_export_only_explicit_drafts_for_pilot() -> None:
    bundle = build_local_portfolio_bundle(overrides_path=None)
    bundle["support_routing_drafts"] = []
    bundle["milestone_drafts"] = []

    export_bundle = build_portfolio_airtable_operational_export(bundle)

    assert export_bundle.support_routing == []
    assert export_bundle.milestones == []


def test_build_portfolio_airtable_example_summary_groups_records_by_table() -> None:
    export_bundle = build_portfolio_airtable_operational_export(build_local_portfolio_bundle())

    summary = build_portfolio_airtable_example_summary(export_bundle)
    table_counts = {table.table_name: table.row_count for table in summary.tables}

    assert summary.company_name == "Acme Automation"
    assert summary.founder_report_draft_status == "draft"
    assert summary.internal_report_draft_status == "draft"
    assert table_counts == {
        "Companies": 1,
        "Evidence Items": 2,
        "Assumptions": 2,
        "Domain Scores": 2,
        "Capital Readiness": 2,
        "Support Routing": 1,
        "Action Items": 4,
        "Milestones": 1,
    }


def test_portfolio_airtable_operational_export_round_trips_through_payload() -> None:
    export_bundle = build_portfolio_airtable_operational_export(build_local_portfolio_bundle())

    payload = portfolio_airtable_operational_export_to_payload(export_bundle)
    round_trip = portfolio_airtable_operational_export_from_payload(payload)

    assert round_trip.organization_id == export_bundle.organization_id
    assert len(round_trip.companies) == 1
    assert len(round_trip.support_routing) == len(export_bundle.support_routing)
    assert round_trip.domain_scores[0].organization_id == export_bundle.domain_scores[0].organization_id


def test_write_portfolio_airtable_operational_exports_writes_expected_files(tmp_path) -> None:
    export_bundle = build_portfolio_airtable_operational_export(build_local_portfolio_bundle())

    written_paths = write_portfolio_airtable_operational_exports(export_bundle, tmp_path)

    assert (tmp_path / "airtable_companies.json").exists()
    assert (tmp_path / "airtable_evidence_items.json").exists()
    assert (tmp_path / "airtable_operational_example_summary.json").exists()
    assert (tmp_path / "airtable_operational_export.json").exists()
    assert (tmp_path / "airtable_operational_export_manifest.json").exists()
    assert len(written_paths) == 11

    manifest = json.loads((tmp_path / "airtable_operational_export_manifest.json").read_text(encoding="utf-8"))
    example_summary = json.loads((tmp_path / "airtable_operational_example_summary.json").read_text(encoding="utf-8"))
    assert manifest["artifact_type"] == "portfolio_airtable_operational_export"
    assert manifest["organization_id"] == "org:acme_automation"
    assert example_summary["founder_report_draft_status"] == "draft"
    assert example_summary["internal_report_draft_status"] == "draft"
    assert any(table["table_name"] == "Companies" and table["row_count"] == 1 for table in example_summary["tables"])


def test_portfolio_operational_export_main_writes_example_outputs(tmp_path) -> None:
    exit_code = main(["--output-dir", str(tmp_path)])

    assert exit_code == 0
    assert (tmp_path / "airtable_companies.json").exists()
    assert (tmp_path / "airtable_operational_export.json").exists()
