"""Rules-based internal recommendation assembly for phase-one portfolio workflow."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import re
from typing import Optional

from src.models.portfolio_recommendation_draft import PortfolioRecommendationDraft
from src.portfolio.constants import (
    CapitalReadinessStatus,
    DraftStatus,
    ReportAudience,
    ScoreStatus,
    TruthStage,
)


def _slug(value: object) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower())
    return text.strip("_") or "record"


def _optional_text(value: object) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _string_list(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return [text for value in values if (text := _optional_text(value)) is not None]


def _unique_strings(values: Sequence[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.strip()
        if not normalized:
            continue
        lowered = normalized.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        cleaned.append(normalized)
    return cleaned


def _model_list(bundle: Mapping[str, object], key: str) -> list[Mapping[str, object]]:
    raw_value = bundle.get(key, [])
    if not isinstance(raw_value, list):
        return []
    return [item for item in raw_value if isinstance(item, Mapping)]


def _single_model(bundle: Mapping[str, object], key: str) -> Optional[Mapping[str, object]]:
    raw_value = bundle.get(key)
    if isinstance(raw_value, Mapping):
        return raw_value
    return None


def _domain_label(value: object) -> str:
    text = str(value or "unmapped_domain").replace("_", " ").strip()
    return text.title()


def _readiness_label(value: object) -> str:
    return str(value or "").replace("_", " ").strip()


def _is_reviewed_truth_stage(value: object) -> bool:
    return str(value) in {
        TruthStage.REVIEWED_EVIDENCE.value,
        TruthStage.INTERNALLY_APPROVED_OUTPUT.value,
        TruthStage.EXTERNALLY_APPROVED_OUTPUT.value,
    }


def _score_priority(score: Mapping[str, object]) -> tuple[int, int, int, int]:
    raw_score = score.get("raw_score")
    evidence_level = int(score.get("evidence_level", 0) or 0)
    return (
        1 if score.get("score_status") == ScoreStatus.DRAFT.value else 0,
        1 if raw_score is None else 0,
        1 if _string_list(score.get("pending_evidence_ids")) else 0,
        (1 if _optional_text(score.get("key_gap")) else 0) + (1 if evidence_level <= 2 else 0),
    )


def _describe_risk(score: Mapping[str, object]) -> str:
    domain_label = _domain_label(score.get("domain_key"))
    raw_score = score.get("raw_score")
    score_status = str(score.get("score_status") or ScoreStatus.DRAFT.value)
    key_gap = _optional_text(score.get("key_gap"))

    if score_status == ScoreStatus.DRAFT.value:
        status_text = "score draft still needs reviewed support"
    elif raw_score is None:
        status_text = "score draft still needs a grounded raw score"
    else:
        status_text = "score draft is %s/5" % raw_score

    if key_gap:
        return "%s: %s. Key gap: %s" % (domain_label, status_text, key_gap)
    return "%s: %s." % (domain_label, status_text)


def _strongest_signal_text(evidence_item: Mapping[str, object]) -> str:
    stage_label = "Reviewed signal" if _is_reviewed_truth_stage(evidence_item.get("truth_stage")) else "Pending review signal"
    domain_label = _domain_label(evidence_item.get("primary_domain"))
    evidence_level = int(evidence_item.get("evidence_level", 0) or 0)
    statement = _optional_text(evidence_item.get("evidence_statement")) or "No evidence statement recorded."
    return "%s: %s (%s, evidence level %s)." % (
        stage_label,
        statement,
        domain_label,
        evidence_level,
    )


def _evidence_priority(evidence_item: Mapping[str, object]) -> tuple[int, int]:
    return (
        1 if _is_reviewed_truth_stage(evidence_item.get("truth_stage")) else 0,
        int(evidence_item.get("evidence_level", 0) or 0),
    )


def _select_internal_capital_readiness(
    capital_readiness_drafts: Sequence[Mapping[str, object]],
) -> Optional[Mapping[str, object]]:
    internal_drafts = [
        draft
        for draft in capital_readiness_drafts
        if draft.get("audience") == ReportAudience.INTERNAL.value
    ]
    if not internal_drafts:
        return None

    readiness_rank = {
        CapitalReadinessStatus.NOT_YET_ASSESSED.value: 0,
        CapitalReadinessStatus.NEEDS_REVIEW.value: 1,
        CapitalReadinessStatus.EMERGING.value: 2,
        CapitalReadinessStatus.READY_TO_DISCUSS.value: 3,
    }
    status_rank = {
        DraftStatus.DRAFT.value: 0,
        DraftStatus.REVIEW_READY.value: 1,
        DraftStatus.REVIEWED.value: 2,
    }
    return max(
        internal_drafts,
        key=lambda draft: (
            readiness_rank.get(str(draft.get("readiness_status")), -1),
            status_rank.get(str(draft.get("draft_status")), -1),
        ),
    )


def build_portfolio_recommendation_draft_from_bundle(
    bundle: Mapping[str, object],
    *,
    generated_by: Optional[str] = None,
) -> PortfolioRecommendationDraft:
    """Build a conservative internal recommendation draft from the current bundle state."""

    snapshot = _single_model(bundle, "portfolio_snapshot") or {}
    organization_id = _optional_text(snapshot.get("organization_id"))
    report_period = _optional_text(snapshot.get("report_period"))
    if organization_id is None or report_period is None:
        raise ValueError("Portfolio recommendation draft requires snapshot organization_id and report_period.")

    domain_scores = _model_list(bundle, "domain_scores")
    evidence_items = _model_list(bundle, "evidence_items")
    assumptions = _model_list(bundle, "assumptions")
    capital_readiness_drafts = _model_list(bundle, "capital_readiness_drafts")
    support_routing_drafts = _model_list(bundle, "support_routing_drafts")
    milestone_drafts = _model_list(bundle, "milestone_drafts")
    review_queue_items = _model_list(bundle, "review_queue_items")
    discovery_sources = _model_list(bundle, "discovery_sources")

    prioritized_scores = sorted(domain_scores, key=_score_priority, reverse=True)
    top_risks = [_describe_risk(score) for score in prioritized_scores[:3]]

    prioritized_evidence = sorted(evidence_items, key=_evidence_priority, reverse=True)
    strongest_signals = [_strongest_signal_text(item) for item in prioritized_evidence[:3]]

    next_validation_steps = _unique_strings(
        [
            *[
                step
                for score in prioritized_scores
                if (step := _optional_text(score.get("next_action"))) is not None
            ],
            *[
                step
                for draft in capital_readiness_drafts
                if draft.get("audience") == ReportAudience.INTERNAL.value
                for step in _string_list(draft.get("required_evidence"))
            ],
            *[
                step
                for draft in milestone_drafts
                if (step := _optional_text(draft.get("milestone_statement"))) is not None
            ],
        ]
    )[:3]

    support_recommendations = _unique_strings(
        [
            *[
                recommendation
                for draft in support_routing_drafts
                if (recommendation := _optional_text(draft.get("route_recommendation"))) is not None
            ],
            *[
                recommendation
                for draft in capital_readiness_drafts
                if draft.get("audience") == ReportAudience.INTERNAL.value
                and (recommendation := _optional_text(draft.get("support_routing_recommendation"))) is not None
            ],
        ]
    )[:3]

    internal_capital_readiness = _select_internal_capital_readiness(capital_readiness_drafts)
    likely_near_term_capital_path_label = None
    if internal_capital_readiness is not None:
        primary_path = _optional_text(internal_capital_readiness.get("primary_capital_path"))
        readiness_status = _optional_text(internal_capital_readiness.get("readiness_status"))
        if primary_path and readiness_status:
            likely_near_term_capital_path_label = "%s (%s draft)" % (
                primary_path,
                _readiness_label(readiness_status),
            )

    what_not_to_pursue_yet: list[str] = []
    if internal_capital_readiness is not None:
        primary_path = _optional_text(internal_capital_readiness.get("primary_capital_path"))
        readiness_status = _optional_text(internal_capital_readiness.get("readiness_status"))
        if (
            primary_path
            and readiness_status
            and readiness_status != CapitalReadinessStatus.READY_TO_DISCUSS.value
        ):
            what_not_to_pursue_yet.append("Do not start a %s process yet." % primary_path)

    draft_risk_domains = [
        _domain_label(score.get("domain_key"))
        for score in prioritized_scores
        if score.get("score_status") == ScoreStatus.DRAFT.value
    ]
    if draft_risk_domains:
        what_not_to_pursue_yet.append("Do not treat %s as resolved yet." % draft_risk_domains[0])

    if any(not _is_reviewed_truth_stage(item.get("truth_stage")) for item in evidence_items):
        what_not_to_pursue_yet.append("Do not present unreviewed evidence as capital-ready proof yet.")

    linked_review_queue_ids = _unique_strings(
        [
            *[
                queue_id
                for score in domain_scores
                for queue_id in _string_list(score.get("linked_review_queue_ids"))
            ],
            *[
                queue_id
                for draft in support_routing_drafts
                for queue_id in _string_list(draft.get("linked_review_queue_ids"))
            ],
            *[
                queue_id
                for draft in milestone_drafts
                for queue_id in _string_list(draft.get("linked_review_queue_ids"))
            ],
            *[
                queue_id
                for draft in capital_readiness_drafts
                for queue_id in _string_list(draft.get("linked_review_queue_ids"))
            ],
            *[
                queue_id
                for item in review_queue_items
                if (queue_id := _optional_text(item.get("id"))) is not None
            ],
        ]
    )

    return PortfolioRecommendationDraft(
        id="portfolio_recommendation:%s:%s" % (_slug(organization_id), _slug(report_period)),
        organization_id=organization_id,
        report_period=report_period,
        top_risks=top_risks,
        strongest_signals=strongest_signals,
        next_validation_steps=next_validation_steps,
        support_recommendations=support_recommendations,
        likely_near_term_capital_path_label=likely_near_term_capital_path_label,
        what_not_to_pursue_yet=_unique_strings(what_not_to_pursue_yet)[:3],
        linked_domain_score_ids=_unique_strings(
            [_optional_text(score.get("id")) or "" for score in domain_scores]
        ),
        linked_capital_readiness_draft_ids=_unique_strings(
            [_optional_text(draft.get("id")) or "" for draft in capital_readiness_drafts]
        ),
        linked_support_routing_draft_ids=_unique_strings(
            [_optional_text(draft.get("id")) or "" for draft in support_routing_drafts]
        ),
        linked_milestone_draft_ids=_unique_strings(
            [_optional_text(draft.get("id")) or "" for draft in milestone_drafts]
        ),
        linked_discovery_source_ids=_unique_strings(
            [_optional_text(source.get("id")) or "" for source in discovery_sources]
        ),
        linked_evidence_ids=_unique_strings(
            [_optional_text(item.get("id")) or "" for item in evidence_items]
        ),
        linked_review_queue_ids=linked_review_queue_ids,
        linked_assumption_ids=_unique_strings(
            [_optional_text(assumption.get("id")) or "" for assumption in assumptions]
        ),
        generated_by=generated_by,
    )


def attach_portfolio_recommendation_draft(
    bundle: Mapping[str, object],
    *,
    generated_by: Optional[str] = None,
) -> dict[str, object]:
    """Attach a rules-based internal recommendation draft to a portfolio bundle."""

    recommendation_draft = build_portfolio_recommendation_draft_from_bundle(
        bundle,
        generated_by=generated_by,
    )
    recommendation_payload = recommendation_draft.model_dump(mode="json")
    updated_bundle = dict(bundle)
    updated_bundle["portfolio_recommendation_draft"] = recommendation_payload

    snapshot = dict(_single_model(updated_bundle, "portfolio_snapshot") or {})
    snapshot["portfolio_recommendation_draft_id"] = recommendation_payload["id"]
    snapshot["portfolio_recommendation_draft_status"] = recommendation_payload["draft_status"]
    updated_bundle["portfolio_snapshot"] = snapshot
    return updated_bundle
