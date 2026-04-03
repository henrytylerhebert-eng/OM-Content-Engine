"""Tests for portfolio workflow service shells."""

from src.ingest.airtable_import import RawImportRecord
from src.models.discovery_source import DiscoverySource
from src.portfolio.constants import DiscoverySourceKind, DomainKey, EvidenceType, TruthStage
from src.portfolio.capital_readiness import CapitalReadinessInput, build_capital_readiness_draft
from src.portfolio.constants import CapitalReadinessStatus, DraftStatus, ReportAudience
from src.portfolio.discovery_ingest import DiscoverySourceInput, ingest_discovery_sources
from src.portfolio.evidence_normalize import EvidenceExtractionTarget, normalize_evidence_targets
from src.portfolio.milestones import MilestoneInput, build_milestone_draft
from src.portfolio.report_drafts import (
    FounderSummaryInput,
    InternalSummaryInput,
    build_founder_report_draft,
    build_internal_report_draft,
)
from src.portfolio.review_queue import build_review_queue_item_from_flag
from src.portfolio.support_routing import SupportRoutingInput, build_support_routing_draft
from src.transform.review_flags import build_review_flag


def test_ingest_discovery_sources_from_raw_record_preserves_provenance() -> None:
    raw_record = RawImportRecord(
        source_system="airtable_export",
        source_table="Discovery Intake",
        source_record_id="rec_disc_001",
        imported_at="2026-04-03T12:00:00+00:00",
        file_path="data/raw/discovery_intake.csv",
        row_hash="hash-disc-001",
        raw={"Company Name": "Acme AI", "Notes": "Founder interview complete."},
    )

    result = ingest_discovery_sources(raw_records=[raw_record])

    assert len(result.discovery_sources) == 1
    assert result.discovery_sources[0].source_record_id == "rec_disc_001"
    assert result.discovery_sources[0].raw_payload_excerpt["Company Name"] == "Acme AI"
    assert result.discovery_sources[0].truth_stage == TruthStage.RAW_INPUT
    assert any(item.queue_reason_code == "missing_organization_link" for item in result.review_queue_items)


def test_manual_discovery_input_without_locator_enters_review_queue() -> None:
    result = ingest_discovery_sources(
        inputs=[
            DiscoverySourceInput(
                source_kind=DiscoverySourceKind.MANUAL_ENTRY,
                title="Founder debrief",
                organization_id="org:1",
            )
        ]
    )

    assert len(result.discovery_sources) == 1
    assert any(item.queue_reason_code == "missing_source_locator" for item in result.review_queue_items)


def test_normalize_evidence_targets_creates_extracted_evidence_and_review_flow() -> None:
    discovery_source = DiscoverySource(
        id="discovery_source:acme_interview",
        organization_id="org:acme",
        title="Acme founder interview",
        source_system="google_doc",
        source_document_id="doc_001",
    )
    result = normalize_evidence_targets(
        discovery_source,
        [
            EvidenceExtractionTarget(
                evidence_type=EvidenceType.INTERVIEW_QUOTE,
                primary_domain=DomainKey.CUSTOMER_RISK,
                evidence_statement="Three customers described the same workflow bottleneck.",
                excerpt="Customers independently named the same urgent pain point.",
                evidence_level=2,
            )
        ],
    )

    assert len(result.evidence_items) == 1
    assert result.evidence_items[0].truth_stage == TruthStage.EXTRACTED_SIGNAL
    assert result.evidence_items[0].review_status == "pending_review"
    assert any(item.queue_reason_code == "review_stage_promotion" for item in result.review_queue_items)
    assert all(item.target_stage == TruthStage.REVIEWED_EVIDENCE for item in result.review_queue_items)


def test_normalize_evidence_targets_routes_missing_domain_to_review() -> None:
    discovery_source = DiscoverySource(
        id="discovery_source:acme_notes",
        organization_id="org:acme",
        title="Acme notes",
        source_system="manual_entry",
    )

    result = normalize_evidence_targets(
        discovery_source,
        [EvidenceExtractionTarget(evidence_statement="Customers are asking for integrations.")],
    )

    assert not result.evidence_items
    assert any(item.queue_reason_code == "missing_primary_domain" for item in result.review_queue_items)


def test_normalize_evidence_targets_can_emit_assumption_shell() -> None:
    discovery_source = DiscoverySource(
        id="discovery_source:acme_followup",
        organization_id="org:acme",
        title="Acme follow-up",
        source_system="google_doc",
    )

    result = normalize_evidence_targets(
        discovery_source,
        [
            EvidenceExtractionTarget(
                primary_domain=DomainKey.PRODUCT_RISK,
                evidence_statement="Users still need onboarding help after week two.",
                assumption_statement="Self-serve onboarding is not yet strong enough to reduce support load.",
            )
        ],
    )

    assert len(result.assumptions) == 1
    assert result.assumptions[0].linked_evidence_ids == [result.evidence_items[0].id]
    assert result.assumptions[0].truth_stage == TruthStage.INTERPRETED_EVIDENCE


def test_review_queue_items_can_be_built_from_existing_flags() -> None:
    flag = build_review_flag(
        "review_missing_org_type",
        source_table="Active Members",
        source_record_id="rec_member_010",
        record_label="Unknown Startup",
        source_field="Member Type",
        raw_value="",
    )

    item = build_review_queue_item_from_flag(
        flag,
        organization_id="org:unknown",
        entity_type="discovery_source",
        entity_id="discovery_source:unknown_startup",
        current_stage=TruthStage.RAW_INPUT,
        target_stage=TruthStage.EXTRACTED_SIGNAL,
        linked_discovery_source_id="discovery_source:unknown_startup",
    )

    assert item.queue_reason_code == "review_missing_org_type"
    assert item.source_table == "Active Members"
    assert item.source_record_id == "rec_member_010"
    assert item.source_field == "Member Type"


def test_report_draft_builders_preserve_linked_inputs() -> None:
    founder_draft = build_founder_report_draft(
        FounderSummaryInput(
            organization_id="org:acme",
            report_period="2026-Q2",
            strengths=["Customer demand is clearer", "Customer demand is clearer"],
            top_gaps=["Need stronger retention proof"],
            linked_domain_score_ids=["domain_score:org_acme:customer_risk"],
            linked_capital_readiness_draft_ids=["capital_readiness:org_acme:internal:2026_q2"],
            linked_discovery_source_ids=["discovery_source:acme_interview"],
            linked_evidence_ids=["evidence:acme_1", "evidence:acme_1"],
            generated_by="portfolio_pipeline",
        )
    )
    internal_draft = build_internal_report_draft(
        InternalSummaryInput(
            organization_id="org:acme",
            report_period="2026-Q2",
            current_strengths=["Founder is highly responsive"],
            stuck_reasons=["No repeatable onboarding yet"],
            priority_domains=[DomainKey.PRODUCT_RISK, DomainKey.CUSTOMER_RISK],
            linked_domain_score_ids=["domain_score:org_acme:product_risk"],
            linked_capital_readiness_draft_ids=["capital_readiness:org_acme:internal:2026_q2"],
            linked_review_queue_ids=["review:evidence_item:acme_1:review_stage_promotion"],
        )
    )

    assert founder_draft.linked_evidence_ids == ["evidence:acme_1"]
    assert founder_draft.linked_domain_score_ids == ["domain_score:org_acme:customer_risk"]
    assert founder_draft.linked_capital_readiness_draft_ids == ["capital_readiness:org_acme:internal:2026_q2"]
    assert founder_draft.truth_stage == TruthStage.INTERPRETED_EVIDENCE
    assert internal_draft.priority_domains == [DomainKey.PRODUCT_RISK, DomainKey.CUSTOMER_RISK]
    assert internal_draft.linked_domain_score_ids == ["domain_score:org_acme:product_risk"]
    assert internal_draft.linked_capital_readiness_draft_ids == ["capital_readiness:org_acme:internal:2026_q2"]
    assert internal_draft.review_status == "pending_review"


def test_founder_report_review_ready_requires_score_links_and_provenance_links() -> None:
    try:
        build_founder_report_draft(
            FounderSummaryInput(
                organization_id="org:acme",
                report_period="2026-Q2",
                draft_status=DraftStatus.REVIEW_READY,
                generated_by="portfolio_pipeline",
            )
        )
    except ValueError as exc:
        assert "linked domain score draft ids" in str(exc)
        return

    raise AssertionError("Founder report draft accepted review_ready without linked score ids.")


def test_internal_report_review_ready_requires_provenance_links() -> None:
    try:
        build_internal_report_draft(
            InternalSummaryInput(
                organization_id="org:acme",
                report_period="2026-Q2",
                linked_domain_score_ids=["domain_score:org_acme:customer_risk"],
                draft_status=DraftStatus.REVIEW_READY,
                generated_by="portfolio_pipeline",
            )
        )
    except ValueError as exc:
        assert "linked discovery source ids or linked evidence ids" in str(exc)
        return

    raise AssertionError("Internal report draft accepted review_ready without provenance links.")


def test_report_draft_builders_allow_review_ready_when_links_are_present() -> None:
    founder_draft = build_founder_report_draft(
        FounderSummaryInput(
            organization_id="org:acme",
            report_period="2026-Q2",
            linked_domain_score_ids=["domain_score:org_acme:customer_risk"],
            linked_discovery_source_ids=["discovery_source:acme_interview"],
            linked_evidence_ids=["evidence:acme_1"],
            draft_status=DraftStatus.REVIEW_READY,
            generated_by="portfolio_pipeline",
        )
    )
    internal_draft = build_internal_report_draft(
        InternalSummaryInput(
            organization_id="org:acme",
            report_period="2026-Q2",
            linked_domain_score_ids=["domain_score:org_acme:customer_risk"],
            linked_discovery_source_ids=["discovery_source:acme_interview"],
            draft_status=DraftStatus.REVIEW_READY,
            generated_by="portfolio_pipeline",
        )
    )

    assert founder_draft.draft_status == DraftStatus.REVIEW_READY
    assert internal_draft.draft_status == DraftStatus.REVIEW_READY


def test_capital_readiness_builder_preserves_audience_and_linked_inputs() -> None:
    draft = build_capital_readiness_draft(
        CapitalReadinessInput(
            organization_id="org:acme",
            report_period="2026-Q2",
            audience=ReportAudience.FOUNDER,
            readiness_status=CapitalReadinessStatus.EMERGING,
            primary_capital_path="venture",
            secondary_capital_paths=["revenue-based financing", "venture"],
            readiness_rationale="Some evidence of demand exists, but the story still needs review.",
            blocking_gaps=["Need stronger revenue consistency", "Need stronger revenue consistency"],
            required_evidence=["More retention evidence"],
            linked_domain_score_ids=["domain_score:org_acme:customer_risk"],
            linked_evidence_ids=["evidence:acme_1"],
            linked_review_queue_ids=["review:evidence_item:acme_1:review_stage_promotion"],
            draft_status=DraftStatus.REVIEW_READY,
        )
    )

    assert draft.audience == ReportAudience.FOUNDER
    assert draft.draft_status == DraftStatus.REVIEW_READY
    assert draft.readiness_status == CapitalReadinessStatus.EMERGING
    assert draft.secondary_capital_paths == ["revenue-based financing", "venture"]
    assert draft.blocking_gaps == ["Need stronger revenue consistency"]
    assert draft.linked_domain_score_ids == ["domain_score:org_acme:customer_risk"]
    assert draft.linked_evidence_ids == ["evidence:acme_1"]


def test_capital_readiness_builder_defaults_to_draft_even_when_status_is_set() -> None:
    draft = build_capital_readiness_draft(
        CapitalReadinessInput(
            organization_id="org:acme",
            report_period="2026-Q2",
            audience=ReportAudience.INTERNAL,
            readiness_status=CapitalReadinessStatus.EMERGING,
            linked_domain_score_ids=["domain_score:org_acme:customer_risk"],
            linked_discovery_source_ids=["discovery_source:acme_interview"],
            linked_evidence_ids=["evidence:acme_1"],
            readiness_rationale="Demand evidence is strengthening but still draft-only.",
        )
    )

    assert draft.draft_status == DraftStatus.DRAFT
    assert draft.readiness_status == CapitalReadinessStatus.EMERGING


def test_capital_readiness_review_ready_requires_score_links_and_provenance() -> None:
    try:
        build_capital_readiness_draft(
            CapitalReadinessInput(
                organization_id="org:acme",
                report_period="2026-Q2",
                readiness_status=CapitalReadinessStatus.EMERGING,
                readiness_rationale="Some support exists.",
                draft_status=DraftStatus.REVIEW_READY,
            )
        )
    except ValueError as exc:
        assert "linked domain score draft ids" in str(exc)
        return

    raise AssertionError("Capital-readiness draft accepted review_ready without linked score ids.")


def test_capital_readiness_review_ready_requires_rationale() -> None:
    try:
        build_capital_readiness_draft(
            CapitalReadinessInput(
                organization_id="org:acme",
                report_period="2026-Q2",
                readiness_status=CapitalReadinessStatus.EMERGING,
                linked_domain_score_ids=["domain_score:org_acme:customer_risk"],
                linked_discovery_source_ids=["discovery_source:acme_interview"],
                draft_status=DraftStatus.REVIEW_READY,
            )
        )
    except ValueError as exc:
        assert "readiness rationale" in str(exc)
        return

    raise AssertionError("Capital-readiness draft accepted review_ready without a rationale.")


def test_support_routing_builder_preserves_internal_links() -> None:
    draft = build_support_routing_draft(
        SupportRoutingInput(
            organization_id="org:acme",
            report_period="2026-Q2",
            route_recommendation="Route product onboarding support next.",
            route_category="product_support",
            route_rationale="Onboarding remains the clearest blocker to cleaner activation evidence.",
            priority_domain=DomainKey.PRODUCT_RISK,
            linked_domain_score_ids=["domain_score:org_acme:product_risk"],
            linked_capital_readiness_draft_ids=["capital_readiness:org_acme:internal:2026_q2"],
            linked_discovery_source_ids=["discovery_source:acme_interview"],
            linked_evidence_ids=["evidence:acme_1"],
            draft_status=DraftStatus.REVIEW_READY,
        )
    )

    assert draft.audience == ReportAudience.INTERNAL
    assert draft.draft_status == DraftStatus.REVIEW_READY
    assert draft.priority_domain == DomainKey.PRODUCT_RISK
    assert draft.linked_domain_score_ids == ["domain_score:org_acme:product_risk"]


def test_support_routing_review_ready_rejects_founder_audience() -> None:
    try:
        build_support_routing_draft(
            SupportRoutingInput(
                organization_id="org:acme",
                report_period="2026-Q2",
                route_recommendation="Route onboarding support next.",
                audience=ReportAudience.FOUNDER,
            )
        )
    except ValueError as exc:
        assert "internal operational use" in str(exc)
        return

    raise AssertionError("SupportRoutingDraft accepted a non-internal audience.")


def test_milestone_builder_preserves_internal_links() -> None:
    draft = build_milestone_draft(
        MilestoneInput(
            organization_id="org:acme",
            report_period="2026-Q2",
            milestone_statement="Validate onboarding improvements with the next three pilots.",
            milestone_category="product_activation",
            milestone_rationale="This is the next internal checkpoint before capital readiness can improve.",
            target_window="next_30_days",
            priority_domain=DomainKey.PRODUCT_RISK,
            linked_domain_score_ids=["domain_score:org_acme:product_risk"],
            linked_discovery_source_ids=["discovery_source:acme_interview"],
            linked_evidence_ids=["evidence:acme_1"],
            draft_status=DraftStatus.REVIEW_READY,
        )
    )

    assert draft.audience == ReportAudience.INTERNAL
    assert draft.draft_status == DraftStatus.REVIEW_READY
    assert draft.target_window == "next_30_days"
    assert draft.priority_domain == DomainKey.PRODUCT_RISK


def test_milestone_review_ready_requires_rationale() -> None:
    try:
        build_milestone_draft(
            MilestoneInput(
                organization_id="org:acme",
                report_period="2026-Q2",
                milestone_statement="Validate onboarding improvements with the next three pilots.",
                linked_domain_score_ids=["domain_score:org_acme:product_risk"],
                linked_discovery_source_ids=["discovery_source:acme_interview"],
                draft_status=DraftStatus.REVIEW_READY,
            )
        )
    except ValueError as exc:
        assert "milestone rationale" in str(exc)
        return

    raise AssertionError("MilestoneDraft accepted review_ready without a rationale.")
