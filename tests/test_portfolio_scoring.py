"""Tests for portfolio score-draft integrity and service rules."""

from pydantic import ValidationError

from src.models.domain_score import DomainScore
from src.models.evidence_item import EvidenceItem
from src.models.review_queue_item import ReviewQueueItem
from src.portfolio.constants import DomainKey, ReviewStatus, ScoreConfidence, ScoreStatus, TruthStage
from src.portfolio.scoring_service import DomainScoreInput, build_domain_score_draft, update_domain_score_draft


def test_domain_score_rejects_invalid_raw_score() -> None:
    try:
        DomainScore(
            id="domain_score:org_1:problem_risk",
            organization_id="org:1",
            domain_key=DomainKey.PROBLEM_RISK,
            raw_score=6,
        )
    except ValidationError:
        return

    raise AssertionError("DomainScore accepted a raw score above the approved range.")


def test_domain_score_defaults_to_draft_state() -> None:
    score = DomainScore(
        id="domain_score:org_1:problem_risk",
        organization_id="org:1",
        domain_key=DomainKey.PROBLEM_RISK,
    )

    assert score.score_status == ScoreStatus.DRAFT
    assert score.truth_stage == TruthStage.INTERPRETED_EVIDENCE
    assert score.review_status == ReviewStatus.PENDING_REVIEW


def test_build_domain_score_draft_uses_only_reviewed_evidence_as_basis() -> None:
    reviewed_item = EvidenceItem(
        id="evidence:reviewed",
        organization_id="org:1",
        discovery_source_id="discovery_source:1",
        primary_domain=DomainKey.CUSTOMER_RISK,
        evidence_statement="Reviewed demand signal",
        evidence_level=4,
        truth_stage=TruthStage.REVIEWED_EVIDENCE,
        review_status=ReviewStatus.REVIEWED,
    )
    extracted_item = EvidenceItem(
        id="evidence:extracted",
        organization_id="org:1",
        discovery_source_id="discovery_source:1",
        primary_domain=DomainKey.CUSTOMER_RISK,
        evidence_statement="Extracted but not reviewed",
        evidence_level=2,
        truth_stage=TruthStage.EXTRACTED_SIGNAL,
        review_status=ReviewStatus.PENDING_REVIEW,
    )
    queue_item = ReviewQueueItem(
        id="review:evidence_item:extracted:review_stage_promotion",
        organization_id="org:1",
        entity_type="evidence_item",
        entity_id="evidence:extracted",
        queue_reason_code="review_stage_promotion",
        linked_evidence_item_id="evidence:extracted",
    )

    score = build_domain_score_draft(
        DomainScoreInput(
            organization_id="org:1",
            domain_key=DomainKey.CUSTOMER_RISK,
            raw_score=3,
            confidence=ScoreConfidence.MODERATE,
            rationale="Reviewed customer calls show repeat demand, but retention proof is still early.",
            key_gap="Need stronger retention proof.",
            next_action="Verify repeat usage in the next founder check-in.",
        ),
        evidence_items=[reviewed_item, extracted_item],
        review_queue_items=[queue_item],
    )

    assert score.raw_score == 3
    assert score.confidence == ScoreConfidence.MODERATE
    assert score.evidence_level == 4
    assert score.score_basis_evidence_ids == ["evidence:reviewed"]
    assert score.pending_evidence_ids == ["evidence:extracted"]
    assert score.linked_review_queue_ids == ["review:evidence_item:extracted:review_stage_promotion"]
    assert score.score_status == ScoreStatus.DRAFT


def test_build_domain_score_draft_rejects_raw_score_without_reviewed_evidence() -> None:
    extracted_item = EvidenceItem(
        id="evidence:extracted",
        organization_id="org:1",
        discovery_source_id="discovery_source:1",
        primary_domain=DomainKey.PROBLEM_RISK,
        evidence_statement="Founder claim only",
        truth_stage=TruthStage.EXTRACTED_SIGNAL,
        review_status=ReviewStatus.PENDING_REVIEW,
    )

    try:
        build_domain_score_draft(
            DomainScoreInput(
                organization_id="org:1",
                domain_key=DomainKey.PROBLEM_RISK,
                raw_score=2,
                confidence=ScoreConfidence.LOW,
            ),
            evidence_items=[extracted_item],
        )
    except ValueError as exc:
        assert "reviewed evidence" in str(exc)
        return

    raise AssertionError("Score draft accepted a raw score without reviewed evidence.")


def test_update_domain_score_draft_refreshes_linkages_without_blurring_stage() -> None:
    reviewed_item = EvidenceItem(
        id="evidence:reviewed",
        organization_id="org:1",
        discovery_source_id="discovery_source:1",
        primary_domain=DomainKey.TEAM_RISK,
        evidence_statement="Leadership team has strong execution history.",
        evidence_level=5,
        truth_stage=TruthStage.REVIEWED_EVIDENCE,
        review_status=ReviewStatus.REVIEWED,
    )
    existing_score = DomainScore(
        id="domain_score:org_1:team_risk",
        organization_id="org:1",
        domain_key=DomainKey.TEAM_RISK,
        review_status=ReviewStatus.IN_REVIEW,
        review_notes="Still discussing confidence level.",
    )

    updated_score = update_domain_score_draft(
        existing_score,
        raw_score=4,
        confidence=ScoreConfidence.HIGH,
        rationale="Reviewed operating history and execution cadence are strong.",
        evidence_items=[reviewed_item],
    )

    assert updated_score.id == existing_score.id
    assert updated_score.raw_score == 4
    assert updated_score.confidence == ScoreConfidence.HIGH
    assert updated_score.score_basis_evidence_ids == ["evidence:reviewed"]
    assert updated_score.review_status == ReviewStatus.IN_REVIEW
    assert updated_score.review_notes == "Still discussing confidence level."
