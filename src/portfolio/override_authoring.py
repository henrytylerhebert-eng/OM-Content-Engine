"""Operator-safe helpers for creating and updating portfolio override rules."""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Optional

from src.portfolio.constants import (
    DraftStatus,
    QueueStatus,
    ReviewStatus,
    ScoreConfidence,
    ScoreStatus,
    TruthStage,
)
from src.portfolio.reviewed_truth import PortfolioOverrideRule, create_portfolio_override_rule


APPROVAL_OVERRIDE_TARGETS = {
    "capital_readiness_drafts",
    "founder_report_draft",
    "internal_report_draft",
}


def _required_text(value: object, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError("%s is required." % label)
    return text


def _optional_text(value: object) -> Optional[str]:
    text = str(value or "").strip()
    return text or None


def _slug(value: object) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower())
    return text.strip("-") or "record"


def _iso_timestamp(value: Optional[str]) -> str:
    if value is None:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()


def build_evidence_review_override(
    *,
    evidence_id: str,
    reviewed_by: str,
    review_notes: str,
    reviewed_at: Optional[str] = None,
    rule_id: Optional[str] = None,
    reason: Optional[str] = None,
    note: Optional[str] = None,
) -> PortfolioOverrideRule:
    """Build a patch-only override that promotes one evidence item to reviewed_evidence."""

    evidence_id_value = _required_text(evidence_id, "evidence_id")
    reviewed_by_value = _required_text(reviewed_by, "reviewed_by")
    review_notes_value = _required_text(review_notes, "review_notes")
    reviewed_at_value = _iso_timestamp(reviewed_at)
    return create_portfolio_override_rule(
        {
            "id": _optional_text(rule_id) or "review-%s" % _slug(evidence_id_value),
            "target": "evidence_items",
            "match": {"id": evidence_id_value},
            "set": {
                "truth_stage": TruthStage.REVIEWED_EVIDENCE.value,
                "review_status": ReviewStatus.REVIEWED.value,
                "review_notes": review_notes_value,
                "reviewed_by": reviewed_by_value,
                "reviewed_at": reviewed_at_value,
            },
            "reason": _optional_text(reason),
            "reviewed_by": reviewed_by_value,
            "reviewed_at": reviewed_at_value,
            "note": _optional_text(note),
        }
    )


def build_domain_score_adjustment_override(
    *,
    score_id: str,
    reviewed_by: str,
    reviewed_at: Optional[str] = None,
    rule_id: Optional[str] = None,
    raw_score: Optional[int] = None,
    confidence: Optional[ScoreConfidence | str] = None,
    evidence_level: Optional[int] = None,
    rationale: Optional[str] = None,
    key_gap: Optional[str] = None,
    next_action: Optional[str] = None,
    score_status: Optional[ScoreStatus | str] = None,
    review_notes: Optional[str] = None,
    reason: Optional[str] = None,
    note: Optional[str] = None,
) -> PortfolioOverrideRule:
    """Build a validated override for a domain score draft adjustment."""

    score_id_value = _required_text(score_id, "score_id")
    reviewed_by_value = _required_text(reviewed_by, "reviewed_by")
    reviewed_at_value = _iso_timestamp(reviewed_at)

    set_values: dict[str, object] = {}
    if raw_score is not None:
        set_values["raw_score"] = int(raw_score)
    if confidence is not None:
        set_values["confidence"] = ScoreConfidence(str(confidence)).value
    if evidence_level is not None:
        set_values["evidence_level"] = int(evidence_level)
    if _optional_text(rationale) is not None:
        set_values["rationale"] = _optional_text(rationale)
    if _optional_text(key_gap) is not None:
        set_values["key_gap"] = _optional_text(key_gap)
    if _optional_text(next_action) is not None:
        set_values["next_action"] = _optional_text(next_action)
    if score_status is not None:
        set_values["score_status"] = ScoreStatus(str(score_status)).value
    if _optional_text(review_notes) is not None:
        set_values["review_notes"] = _optional_text(review_notes)

    if not set_values:
        raise ValueError(
            "Domain score adjustment overrides require at least one score field or review note to update."
        )

    set_values["review_status"] = ReviewStatus.REVIEWED.value
    set_values["reviewed_by"] = reviewed_by_value
    set_values["reviewed_at"] = reviewed_at_value

    return create_portfolio_override_rule(
        {
            "id": _optional_text(rule_id) or "adjust-%s" % _slug(score_id_value),
            "target": "domain_scores",
            "match": {"id": score_id_value},
            "set": set_values,
            "reason": _optional_text(reason),
            "reviewed_by": reviewed_by_value,
            "reviewed_at": reviewed_at_value,
            "note": _optional_text(note),
        }
    )


def build_review_queue_resolution_override(
    *,
    reviewed_by: str,
    resolution_note: str,
    reviewed_at: Optional[str] = None,
    rule_id: Optional[str] = None,
    queue_item_id: Optional[str] = None,
    linked_evidence_item_id: Optional[str] = None,
    queue_reason_code: Optional[str] = "review_stage_promotion",
    owner: Optional[str] = None,
    note: Optional[str] = None,
    reason: Optional[str] = None,
) -> PortfolioOverrideRule:
    """Build a queue-resolution override for a known queue item or linked evidence item."""

    reviewed_by_value = _required_text(reviewed_by, "reviewed_by")
    resolution_note_value = _required_text(resolution_note, "resolution_note")
    reviewed_at_value = _iso_timestamp(reviewed_at)

    match: dict[str, object]
    queue_item_id_value = _optional_text(queue_item_id)
    linked_evidence_item_id_value = _optional_text(linked_evidence_item_id)
    if queue_item_id_value is not None:
        match = {"id": queue_item_id_value}
        rule_id_value = _optional_text(rule_id) or "resolve-%s" % _slug(queue_item_id_value)
    elif linked_evidence_item_id_value is not None:
        match = {"linked_evidence_item_id": linked_evidence_item_id_value}
        queue_reason_code_value = _optional_text(queue_reason_code)
        if queue_reason_code_value is not None:
            match["queue_reason_code"] = queue_reason_code_value
        rule_id_value = _optional_text(rule_id) or "resolve-%s-queue" % _slug(linked_evidence_item_id_value)
    else:
        raise ValueError("Queue resolution overrides require queue_item_id or linked_evidence_item_id.")

    set_values: dict[str, object] = {
        "queue_status": QueueStatus.RESOLVED.value,
        "resolution_note": resolution_note_value,
        "resolved_at": reviewed_at_value,
    }
    if _optional_text(owner) is not None:
        set_values["owner"] = _optional_text(owner)
    if _optional_text(note) is not None:
        set_values["note"] = _optional_text(note)

    return create_portfolio_override_rule(
        {
            "id": rule_id_value,
            "target": "review_queue_items",
            "match": match,
            "set": set_values,
            "reason": _optional_text(reason),
            "reviewed_by": reviewed_by_value,
            "reviewed_at": reviewed_at_value,
            "note": _optional_text(note),
        }
    )


def build_internal_draft_approval_override(
    *,
    target: str,
    record_id: str,
    reviewed_by: str,
    review_notes: str,
    reviewed_at: Optional[str] = None,
    rule_id: Optional[str] = None,
    draft_status: DraftStatus | str = DraftStatus.REVIEWED,
    internal_approved_by: Optional[str] = None,
    internal_approved_at: Optional[str] = None,
    reason: Optional[str] = None,
    note: Optional[str] = None,
) -> PortfolioOverrideRule:
    """Build an internal-only approval override for a founder/internal draft record."""

    if target not in APPROVAL_OVERRIDE_TARGETS:
        raise ValueError(
            "Draft approval overrides must target one of %s." % ", ".join(sorted(APPROVAL_OVERRIDE_TARGETS))
        )

    record_id_value = _required_text(record_id, "record_id")
    reviewed_by_value = _required_text(reviewed_by, "reviewed_by")
    review_notes_value = _required_text(review_notes, "review_notes")
    reviewed_at_value = _iso_timestamp(reviewed_at)
    internal_approved_by_value = _optional_text(internal_approved_by) or reviewed_by_value
    internal_approved_at_value = _iso_timestamp(internal_approved_at) if internal_approved_at else reviewed_at_value
    draft_status_value = DraftStatus(str(draft_status)).value

    return create_portfolio_override_rule(
        {
            "id": _optional_text(rule_id) or "approve-%s" % _slug(record_id_value),
            "target": target,
            "match": {"id": record_id_value},
            "set": {
                "draft_status": draft_status_value,
                "review_status": ReviewStatus.INTERNALLY_APPROVED.value,
                "truth_stage": TruthStage.INTERNALLY_APPROVED_OUTPUT.value,
                "review_notes": review_notes_value,
                "reviewed_by": reviewed_by_value,
                "reviewed_at": reviewed_at_value,
                "internal_approved_by": internal_approved_by_value,
                "internal_approved_at": internal_approved_at_value,
            },
            "reason": _optional_text(reason),
            "reviewed_by": reviewed_by_value,
            "reviewed_at": reviewed_at_value,
            "note": _optional_text(note),
        }
    )
