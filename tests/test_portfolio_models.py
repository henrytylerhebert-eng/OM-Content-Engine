"""Tests for portfolio workflow schema objects."""

from pydantic import ValidationError

from src.models.discovery_source import DiscoverySource
from src.models.capital_readiness_draft import CapitalReadinessDraft
from src.models.evidence_item import EvidenceItem
from src.models.founder_report_draft import FounderReportDraft
from src.models.internal_report_draft import InternalReportDraft
from src.models.milestone_draft import MilestoneDraft
from src.models.portfolio_recommendation_draft import PortfolioRecommendationDraft
from src.models.review_queue_item import ReviewQueueItem
from src.models.support_routing_draft import SupportRoutingDraft
from src.portfolio.constants import (
    CapitalReadinessStatus,
    DiscoverySourceKind,
    DraftStatus,
    DomainKey,
    QueueStatus,
    ReportAudience,
    ReviewSeverity,
    ReviewStatus,
    TruthStage,
)


def test_discovery_source_defaults_to_raw_input_and_pending_review() -> None:
    source = DiscoverySource(id="discovery_source:test-1")

    assert source.source_kind == DiscoverySourceKind.AIRTABLE_RECORD
    assert source.truth_stage == TruthStage.RAW_INPUT
    assert source.review_status == ReviewStatus.PENDING_REVIEW
    assert source.simulation_flag is False


def test_evidence_item_rejects_invalid_evidence_level() -> None:
    try:
        EvidenceItem(
            id="evidence:test-1",
            organization_id="org:1",
            discovery_source_id="discovery_source:test-1",
            primary_domain=DomainKey.PROBLEM_RISK,
            evidence_statement="Demand evidence exists.",
            evidence_level=8,
        )
    except ValidationError:
        return

    raise AssertionError("EvidenceItem accepted an evidence level above the approved range.")


def test_review_queue_item_tracks_stage_targets() -> None:
    item = ReviewQueueItem(
        id="review:test-1",
        entity_type="evidence_item",
        entity_id="evidence:test-1",
        queue_reason_code="review_stage_promotion",
        severity=ReviewSeverity.MEDIUM,
        current_stage=TruthStage.EXTRACTED_SIGNAL,
        target_stage=TruthStage.REVIEWED_EVIDENCE,
        queue_status=QueueStatus.OPEN,
    )

    assert item.current_stage == TruthStage.EXTRACTED_SIGNAL
    assert item.target_stage == TruthStage.REVIEWED_EVIDENCE
    assert item.queue_status == QueueStatus.OPEN


def test_founder_report_draft_defaults_to_founder_audience() -> None:
    draft = FounderReportDraft(
        id="founder_report:org_1:2026_q2",
        organization_id="org:1",
        report_period="2026-Q2",
    )

    assert draft.audience == ReportAudience.FOUNDER
    assert draft.draft_status == DraftStatus.DRAFT
    assert draft.truth_stage == TruthStage.INTERPRETED_EVIDENCE
    assert draft.review_status == ReviewStatus.PENDING_REVIEW


def test_capital_readiness_draft_defaults_to_internal_draft_state() -> None:
    draft = CapitalReadinessDraft(
        id="capital_readiness:org_1:internal:2026_q2",
        organization_id="org:1",
        report_period="2026-Q2",
    )

    assert draft.audience == ReportAudience.INTERNAL
    assert draft.draft_status == DraftStatus.DRAFT
    assert draft.readiness_status == CapitalReadinessStatus.NOT_YET_ASSESSED
    assert draft.truth_stage == TruthStage.INTERPRETED_EVIDENCE
    assert draft.review_status == ReviewStatus.PENDING_REVIEW


def test_internal_report_draft_defaults_to_internal_audience() -> None:
    draft = InternalReportDraft(
        id="internal_report:org_1:2026_q2",
        organization_id="org:1",
        report_period="2026-Q2",
    )

    assert draft.audience == ReportAudience.INTERNAL
    assert draft.draft_status == DraftStatus.DRAFT
    assert draft.truth_stage == TruthStage.INTERPRETED_EVIDENCE


def test_support_routing_draft_defaults_to_internal_draft_state() -> None:
    draft = SupportRoutingDraft(
        id="support_routing:org_1:2026_q2",
        organization_id="org:1",
        report_period="2026-Q2",
        route_recommendation="Route onboarding support next.",
    )

    assert draft.audience == ReportAudience.INTERNAL
    assert draft.draft_status == DraftStatus.DRAFT
    assert draft.truth_stage == TruthStage.INTERPRETED_EVIDENCE
    assert draft.review_status == ReviewStatus.PENDING_REVIEW


def test_milestone_draft_defaults_to_internal_draft_state() -> None:
    draft = MilestoneDraft(
        id="milestone:org_1:2026_q2",
        organization_id="org:1",
        report_period="2026-Q2",
        milestone_statement="Validate onboarding improvements with the next three pilots.",
    )

    assert draft.audience == ReportAudience.INTERNAL
    assert draft.draft_status == DraftStatus.DRAFT
    assert draft.truth_stage == TruthStage.INTERPRETED_EVIDENCE
    assert draft.review_status == ReviewStatus.PENDING_REVIEW


def test_portfolio_recommendation_draft_defaults_to_internal_draft_state() -> None:
    draft = PortfolioRecommendationDraft(
        id="portfolio_recommendation:org_1:2026_q2",
        organization_id="org:1",
        report_period="2026-Q2",
    )

    assert draft.audience == ReportAudience.INTERNAL
    assert draft.draft_status == DraftStatus.DRAFT
    assert draft.recommendation_method == "rules_based"
    assert draft.truth_stage == TruthStage.INTERPRETED_EVIDENCE
    assert draft.review_status == ReviewStatus.PENDING_REVIEW


def test_capital_readiness_draft_requires_company_and_period() -> None:
    try:
        CapitalReadinessDraft(id="capital_readiness:test")
    except ValidationError:
        return

    raise AssertionError("CapitalReadinessDraft accepted missing required identity fields.")
