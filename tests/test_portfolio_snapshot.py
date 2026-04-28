"""Tests for minimal portfolio snapshot assembly."""

import json

from src.models.assumption import Assumption
from src.models.discovery_source import DiscoverySource
from src.models.domain_score import DomainScore
from src.models.evidence_item import EvidenceItem
from src.portfolio.capital_readiness import CapitalReadinessInput, build_capital_readiness_draft
from src.portfolio.constants import (
    CapitalReadinessStatus,
    DiscoverySourceKind,
    DomainKey,
    DraftStatus,
    EvidenceType,
    ScoreStatus,
    TruthStage,
)
from src.portfolio.milestones import MilestoneInput, build_milestone_draft
from src.portfolio.pipeline import write_portfolio_snapshot_outputs
from src.portfolio.report_drafts import (
    FounderSummaryInput,
    InternalSummaryInput,
    build_founder_report_draft,
    build_internal_report_draft,
)
from src.portfolio.review_queue import build_stage_promotion_item
from src.portfolio.snapshot import build_portfolio_snapshot_bundle
from src.portfolio.support_routing import SupportRoutingInput, build_support_routing_draft


def test_build_portfolio_snapshot_bundle_groups_one_company_records() -> None:
    discovery_source = DiscoverySource(
        id="discovery_source:acme_founder_call",
        organization_id="org:acme",
        source_kind=DiscoverySourceKind.GOOGLE_DOC,
        title="Acme founder call",
        source_document_id="doc_001",
        source_url="https://docs.example.com/doc_001",
    )
    reviewed_evidence = EvidenceItem(
        id="evidence:acme_customer_signal",
        organization_id="org:acme",
        discovery_source_id=discovery_source.id,
        evidence_type=EvidenceType.INTERVIEW_QUOTE,
        primary_domain=DomainKey.CUSTOMER_RISK,
        evidence_statement="Three customers repeated the same workflow bottleneck.",
        evidence_level=3,
        excerpt="Repeated workflow bottleneck described in interviews.",
        truth_stage=TruthStage.REVIEWED_EVIDENCE,
    )
    assumption = Assumption(
        id="assumption:acme_onboarding",
        organization_id="org:acme",
        domain_key=DomainKey.PRODUCT_RISK,
        title="Onboarding still needs support",
        statement="Self-serve onboarding still requires operator help in week two.",
        linked_evidence_ids=[reviewed_evidence.id],
    )
    domain_score = DomainScore(
        id="domain_score:org_acme:customer_risk",
        organization_id="org:acme",
        domain_key=DomainKey.CUSTOMER_RISK,
        score_status=ScoreStatus.REVIEW_READY,
        evidence_level=3,
        score_basis_evidence_ids=[reviewed_evidence.id],
        generated_by="portfolio_snapshot_test",
    )
    capital_readiness_draft = build_capital_readiness_draft(
        CapitalReadinessInput(
            organization_id="org:acme",
            report_period="2026-Q2",
            readiness_status=CapitalReadinessStatus.EMERGING,
            draft_status=DraftStatus.REVIEW_READY,
            readiness_rationale="Customer demand evidence is reviewed, but the capital path is still a draft.",
            linked_domain_score_ids=[domain_score.id],
            linked_discovery_source_ids=[discovery_source.id],
            linked_evidence_ids=[reviewed_evidence.id],
            generated_by="portfolio_snapshot_test",
        )
    )
    founder_report_draft = build_founder_report_draft(
        FounderSummaryInput(
            organization_id="org:acme",
            report_period="2026-Q2",
            strengths=["Customer signal is getting clearer"],
            linked_domain_score_ids=[domain_score.id],
            linked_discovery_source_ids=[discovery_source.id],
            linked_evidence_ids=[reviewed_evidence.id],
            linked_capital_readiness_draft_ids=[capital_readiness_draft.id],
            draft_status=DraftStatus.REVIEW_READY,
            generated_by="portfolio_snapshot_test",
        )
    )
    internal_report_draft = build_internal_report_draft(
        InternalSummaryInput(
            organization_id="org:acme",
            report_period="2026-Q2",
            current_strengths=["Founder responds quickly to customer feedback"],
            linked_domain_score_ids=[domain_score.id],
            linked_discovery_source_ids=[discovery_source.id],
            linked_evidence_ids=[reviewed_evidence.id],
            linked_capital_readiness_draft_ids=[capital_readiness_draft.id],
            draft_status=DraftStatus.REVIEW_READY,
            generated_by="portfolio_snapshot_test",
        )
    )
    support_routing_draft = build_support_routing_draft(
        SupportRoutingInput(
            organization_id="org:acme",
            report_period="2026-Q2",
            route_recommendation="Route product onboarding support before capital introductions.",
            route_category="product_support",
            route_rationale="Onboarding friction still blocks better activation evidence.",
            priority_domain=DomainKey.PRODUCT_RISK,
            linked_domain_score_ids=[domain_score.id],
            linked_capital_readiness_draft_ids=[capital_readiness_draft.id],
            linked_discovery_source_ids=[discovery_source.id],
            linked_evidence_ids=[reviewed_evidence.id],
            draft_status=DraftStatus.REVIEW_READY,
            generated_by="portfolio_snapshot_test",
        )
    )
    milestone_draft = build_milestone_draft(
        MilestoneInput(
            organization_id="org:acme",
            report_period="2026-Q2",
            milestone_statement="Validate onboarding improvements with the next three pilots.",
            milestone_category="product_activation",
            milestone_rationale="This is the next internal milestone before a stronger capital conversation.",
            target_window="next_30_days",
            priority_domain=DomainKey.PRODUCT_RISK,
            linked_domain_score_ids=[domain_score.id],
            linked_capital_readiness_draft_ids=[capital_readiness_draft.id],
            linked_discovery_source_ids=[discovery_source.id],
            linked_evidence_ids=[reviewed_evidence.id],
            draft_status=DraftStatus.REVIEW_READY,
            generated_by="portfolio_snapshot_test",
        )
    )
    review_queue_item = build_stage_promotion_item(
        organization_id="org:acme",
        entity_type="evidence_item",
        entity_id=reviewed_evidence.id,
        current_stage=TruthStage.EXTRACTED_SIGNAL,
        target_stage=TruthStage.REVIEWED_EVIDENCE,
        linked_discovery_source_id=discovery_source.id,
        linked_evidence_item_id=reviewed_evidence.id,
    )

    bundle = build_portfolio_snapshot_bundle(
        organization_id="org:acme",
        report_period="2026-Q2",
        discovery_sources=[discovery_source],
        evidence_items=[reviewed_evidence],
        assumptions=[assumption],
        domain_scores=[domain_score],
        capital_readiness_drafts=[capital_readiness_draft],
        support_routing_drafts=[support_routing_draft],
        milestone_drafts=[milestone_draft],
        review_queue_items=[review_queue_item],
        founder_report_draft=founder_report_draft,
        internal_report_draft=internal_report_draft,
        assembled_by="portfolio_snapshot_test",
    )

    assert bundle["portfolio_snapshot"]["organization_id"] == "org:acme"
    assert bundle["portfolio_snapshot"]["discovery_source_count"] == 1
    assert bundle["portfolio_snapshot"]["reviewed_evidence_count"] == 1
    assert bundle["portfolio_snapshot"]["review_ready_domain_score_count"] == 1
    assert bundle["portfolio_snapshot"]["review_ready_capital_readiness_draft_count"] == 1
    assert bundle["portfolio_snapshot"]["review_ready_support_routing_draft_count"] == 1
    assert bundle["portfolio_snapshot"]["review_ready_milestone_draft_count"] == 1
    assert bundle["portfolio_snapshot"]["founder_report_draft_status"] == DraftStatus.REVIEW_READY
    assert bundle["portfolio_snapshot"]["internal_report_draft_status"] == DraftStatus.REVIEW_READY
    assert bundle["founder_report_draft"]["linked_domain_score_ids"] == [domain_score.id]
    assert bundle["internal_report_draft"]["linked_evidence_ids"] == [reviewed_evidence.id]
    assert bundle["support_routing_drafts"][0]["draft_status"] == DraftStatus.REVIEW_READY
    assert bundle["milestone_drafts"][0]["draft_status"] == DraftStatus.REVIEW_READY


def test_build_portfolio_snapshot_bundle_rejects_mismatched_organization_ids() -> None:
    discovery_source = DiscoverySource(
        id="discovery_source:acme_founder_call",
        organization_id="org:other",
        source_kind=DiscoverySourceKind.MANUAL_ENTRY,
        title="Wrong company record",
        source_path="notes/acme.txt",
    )

    try:
        build_portfolio_snapshot_bundle(
            organization_id="org:acme",
            report_period="2026-Q2",
            discovery_sources=[discovery_source],
        )
    except ValueError as exc:
        assert "does not belong to organization org:acme" in str(exc)
        return

    raise AssertionError("Snapshot bundle accepted records from the wrong organization.")


def test_build_portfolio_snapshot_bundle_rejects_review_ready_reports_with_missing_bundle_links() -> None:
    domain_score = DomainScore(
        id="domain_score:org_acme:customer_risk",
        organization_id="org:acme",
        domain_key=DomainKey.CUSTOMER_RISK,
        score_status=ScoreStatus.REVIEW_READY,
        evidence_level=3,
    )
    founder_report_draft = build_founder_report_draft(
        FounderSummaryInput(
            organization_id="org:acme",
            report_period="2026-Q2",
            linked_domain_score_ids=[domain_score.id],
            linked_evidence_ids=["evidence:missing"],
            draft_status=DraftStatus.REVIEW_READY,
            generated_by="portfolio_snapshot_test",
        )
    )

    try:
        build_portfolio_snapshot_bundle(
            organization_id="org:acme",
            report_period="2026-Q2",
            domain_scores=[domain_score],
            founder_report_draft=founder_report_draft,
        )
    except ValueError as exc:
        assert "missing from the snapshot bundle" in str(exc)
        return

    raise AssertionError("Snapshot bundle accepted a review-ready founder draft without bundled provenance links.")


def test_build_portfolio_snapshot_bundle_rejects_review_ready_capital_draft_with_draft_scores() -> None:
    discovery_source = DiscoverySource(
        id="discovery_source:acme_founder_call",
        organization_id="org:acme",
        source_kind=DiscoverySourceKind.GOOGLE_DOC,
        title="Acme founder call",
        source_document_id="doc_001",
        source_url="https://docs.example.com/doc_001",
    )
    reviewed_evidence = EvidenceItem(
        id="evidence:acme_customer_signal",
        organization_id="org:acme",
        discovery_source_id=discovery_source.id,
        primary_domain=DomainKey.CUSTOMER_RISK,
        evidence_statement="Customers confirm a repeat pain point.",
        evidence_level=3,
        truth_stage=TruthStage.REVIEWED_EVIDENCE,
    )
    domain_score = DomainScore(
        id="domain_score:org_acme:customer_risk",
        organization_id="org:acme",
        domain_key=DomainKey.CUSTOMER_RISK,
        score_status=ScoreStatus.DRAFT,
        evidence_level=3,
    )
    capital_readiness_draft = build_capital_readiness_draft(
        CapitalReadinessInput(
            organization_id="org:acme",
            report_period="2026-Q2",
            readiness_status=CapitalReadinessStatus.EMERGING,
            draft_status=DraftStatus.REVIEW_READY,
            readiness_rationale="There is some support for a future capital conversation.",
            linked_domain_score_ids=[domain_score.id],
            linked_discovery_source_ids=[discovery_source.id],
            linked_evidence_ids=[reviewed_evidence.id],
        )
    )

    try:
        build_portfolio_snapshot_bundle(
            organization_id="org:acme",
            report_period="2026-Q2",
            discovery_sources=[discovery_source],
            evidence_items=[reviewed_evidence],
            domain_scores=[domain_score],
            capital_readiness_drafts=[capital_readiness_draft],
        )
    except ValueError as exc:
        assert "linked domain scores remain draft" in str(exc)
        return

    raise AssertionError("Snapshot bundle accepted a review-ready capital draft supported only by draft scores.")


def test_build_portfolio_snapshot_bundle_rejects_review_ready_support_routing_with_unreviewed_evidence() -> None:
    discovery_source = DiscoverySource(
        id="discovery_source:acme_onboarding_review",
        organization_id="org:acme",
        source_kind=DiscoverySourceKind.MANUAL_ENTRY,
        title="Acme onboarding review",
        source_path="notes/acme_onboarding_review.md",
    )
    extracted_evidence = EvidenceItem(
        id="evidence:acme_onboarding_gap",
        organization_id="org:acme",
        discovery_source_id=discovery_source.id,
        primary_domain=DomainKey.PRODUCT_RISK,
        evidence_statement="New users still require manual onboarding support.",
        evidence_level=2,
        truth_stage=TruthStage.EXTRACTED_SIGNAL,
    )
    review_ready_score = DomainScore(
        id="domain_score:org_acme:product_risk",
        organization_id="org:acme",
        domain_key=DomainKey.PRODUCT_RISK,
        score_status=ScoreStatus.REVIEW_READY,
        evidence_level=2,
        score_basis_evidence_ids=[extracted_evidence.id],
    )
    support_routing_draft = build_support_routing_draft(
        SupportRoutingInput(
            organization_id="org:acme",
            report_period="2026-Q2",
            route_recommendation="Route onboarding support next.",
            route_rationale="Onboarding remains the clearest blocker to cleaner evidence.",
            linked_domain_score_ids=[review_ready_score.id],
            linked_discovery_source_ids=[discovery_source.id],
            linked_evidence_ids=[extracted_evidence.id],
            draft_status=DraftStatus.REVIEW_READY,
        )
    )

    try:
        build_portfolio_snapshot_bundle(
            organization_id="org:acme",
            report_period="2026-Q2",
            discovery_sources=[discovery_source],
            evidence_items=[extracted_evidence],
            domain_scores=[review_ready_score],
            support_routing_drafts=[support_routing_draft],
        )
    except ValueError as exc:
        assert "linked evidence is not reviewed" in str(exc)
        return

    raise AssertionError("Snapshot bundle accepted a review-ready support-routing draft backed by unreviewed evidence.")


def test_write_portfolio_snapshot_outputs_writes_expected_json_artifacts(tmp_path) -> None:
    bundle = {
        "portfolio_snapshot": {
            "id": "portfolio_snapshot:org_acme:2026_q2",
            "organization_id": "org:acme",
            "report_period": "2026-Q2",
            "review_ready_capital_readiness_draft_count": 1,
            "review_ready_support_routing_draft_count": 1,
            "review_ready_milestone_draft_count": 1,
        },
        "discovery_sources": [{"id": "discovery_source:acme_founder_call"}],
        "evidence_items": [{"id": "evidence:acme_customer_signal"}],
        "assumptions": [{"id": "assumption:acme_onboarding"}],
        "domain_scores": [{"id": "domain_score:org_acme:customer_risk"}],
        "capital_readiness_drafts": [{"id": "capital_readiness:org_acme:internal:2026_q2"}],
        "support_routing_drafts": [{"id": "support_routing:org_acme:2026_q2"}],
        "milestone_drafts": [{"id": "milestone:org_acme:2026_q2"}],
        "review_queue_items": [{"id": "review:evidence_item:acme_customer_signal:review_stage_promotion"}],
        "portfolio_recommendation_draft": {"id": "portfolio_recommendation:org_acme:2026_q2"},
        "founder_report_draft": {"id": "founder_report:org_acme:2026_q2"},
        "internal_report_draft": {"id": "internal_report:org_acme:2026_q2"},
    }

    written_paths = write_portfolio_snapshot_outputs(bundle, tmp_path)

    assert {path.name for path in written_paths} == {
        "portfolio_snapshot.json",
        "discovery_sources.json",
        "evidence_items.json",
        "assumptions.json",
        "domain_scores.json",
        "capital_readiness_drafts.json",
        "support_routing_drafts.json",
        "milestone_drafts.json",
        "review_queue_items.json",
        "portfolio_recommendation_draft.json",
        "founder_report_draft.json",
        "internal_report_draft.json",
        "snapshot_manifest.json",
    }

    manifest = json.loads((tmp_path / "snapshot_manifest.json").read_text(encoding="utf-8"))
    assert manifest["artifact_type"] == "portfolio_snapshot"
    assert manifest["organization_id"] == "org:acme"
    assert manifest["summary"]["review_ready_capital_readiness_draft_count"] == 1
    assert manifest["summary"]["review_ready_support_routing_draft_count"] == 1
    assert manifest["summary"]["review_ready_milestone_draft_count"] == 1
