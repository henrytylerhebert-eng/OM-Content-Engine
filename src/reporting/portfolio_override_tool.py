"""Operator-safe CLI for creating and updating portfolio reviewed-truth rules."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional, Sequence

from src.portfolio.constants import DraftStatus, ScoreConfidence, ScoreStatus
from src.portfolio.override_authoring import (
    APPROVAL_OVERRIDE_TARGETS,
    build_domain_score_adjustment_override,
    build_evidence_review_override,
    build_internal_draft_approval_override,
    build_review_queue_resolution_override,
)
from src.portfolio.reviewed_truth import (
    DEFAULT_PORTFOLIO_OVERRIDES_PATH,
    portfolio_override_rule_to_payload,
    upsert_portfolio_override_rule,
)


def _add_shared_metadata_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--overrides-file", default=str(DEFAULT_PORTFOLIO_OVERRIDES_PATH))
    parser.add_argument("--description", help="Optional description to store on the override document.")
    parser.add_argument("--rule-id", help="Optional stable rule id. If omitted, a deterministic id is generated.")
    parser.add_argument("--reviewed-by", required=True, help="Operator identifier for this durable decision.")
    parser.add_argument("--reviewed-at", help="ISO timestamp. Defaults to the current UTC time.")
    parser.add_argument("--reason", help="Why this override should survive reruns.")
    parser.add_argument("--note", help="Optional operator note stored with the rule.")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Create or update one portfolio reviewed-truth override rule."""

    parser = argparse.ArgumentParser(
        description="Create or update one file-backed portfolio reviewed-truth override rule."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    evidence_parser = subparsers.add_parser(
        "evidence-review",
        help="Promote one evidence item to reviewed_evidence without editing the raw input file.",
    )
    _add_shared_metadata_arguments(evidence_parser)
    evidence_parser.add_argument("--evidence-id", required=True)
    evidence_parser.add_argument("--review-notes", required=True)

    score_parser = subparsers.add_parser(
        "domain-score-adjustment",
        help="Create or update a domain-score adjustment override.",
    )
    _add_shared_metadata_arguments(score_parser)
    score_parser.add_argument("--score-id", required=True)
    score_parser.add_argument("--raw-score", type=int)
    score_parser.add_argument("--confidence", choices=[member.value for member in ScoreConfidence])
    score_parser.add_argument("--evidence-level", type=int)
    score_parser.add_argument("--rationale")
    score_parser.add_argument("--key-gap")
    score_parser.add_argument("--next-action")
    score_parser.add_argument("--score-status", choices=[member.value for member in ScoreStatus])
    score_parser.add_argument("--review-notes")

    queue_parser = subparsers.add_parser(
        "queue-resolution",
        help="Resolve one review queue item without hiding the underlying record.",
    )
    _add_shared_metadata_arguments(queue_parser)
    queue_parser.add_argument("--resolution-note", required=True)
    queue_parser.add_argument("--queue-item-id")
    queue_parser.add_argument("--linked-evidence-item-id")
    queue_parser.add_argument("--queue-reason-code", default="review_stage_promotion")
    queue_parser.add_argument("--owner")

    approval_parser = subparsers.add_parser(
        "internal-draft-approval",
        help="Create or update an internal-only approval override for a founder/internal draft record.",
    )
    _add_shared_metadata_arguments(approval_parser)
    approval_parser.add_argument("--target", required=True, choices=sorted(APPROVAL_OVERRIDE_TARGETS))
    approval_parser.add_argument("--record-id", required=True)
    approval_parser.add_argument("--review-notes", required=True)
    approval_parser.add_argument("--draft-status", default=DraftStatus.REVIEWED.value, choices=[member.value for member in DraftStatus])
    approval_parser.add_argument("--internal-approved-by")
    approval_parser.add_argument("--internal-approved-at")

    args = parser.parse_args(argv)
    if args.command == "evidence-review":
        rule = build_evidence_review_override(
            evidence_id=args.evidence_id,
            reviewed_by=args.reviewed_by,
            review_notes=args.review_notes,
            reviewed_at=args.reviewed_at,
            rule_id=args.rule_id,
            reason=args.reason,
            note=args.note,
        )
    elif args.command == "domain-score-adjustment":
        rule = build_domain_score_adjustment_override(
            score_id=args.score_id,
            reviewed_by=args.reviewed_by,
            reviewed_at=args.reviewed_at,
            rule_id=args.rule_id,
            raw_score=args.raw_score,
            confidence=args.confidence,
            evidence_level=args.evidence_level,
            rationale=args.rationale,
            key_gap=args.key_gap,
            next_action=args.next_action,
            score_status=args.score_status,
            review_notes=args.review_notes,
            reason=args.reason,
            note=args.note,
        )
    elif args.command == "queue-resolution":
        rule = build_review_queue_resolution_override(
            reviewed_by=args.reviewed_by,
            resolution_note=args.resolution_note,
            reviewed_at=args.reviewed_at,
            rule_id=args.rule_id,
            queue_item_id=args.queue_item_id,
            linked_evidence_item_id=args.linked_evidence_item_id,
            queue_reason_code=args.queue_reason_code,
            owner=args.owner,
            reason=args.reason,
            note=args.note,
        )
    else:
        rule = build_internal_draft_approval_override(
            target=args.target,
            record_id=args.record_id,
            reviewed_by=args.reviewed_by,
            review_notes=args.review_notes,
            reviewed_at=args.reviewed_at,
            rule_id=args.rule_id,
            draft_status=args.draft_status,
            internal_approved_by=args.internal_approved_by,
            internal_approved_at=args.internal_approved_at,
            reason=args.reason,
            note=args.note,
        )

    result = upsert_portfolio_override_rule(
        Path(args.overrides_file),
        rule,
        description=args.description,
    )

    print("%s override rule %s in %s" % (result.action.capitalize(), result.rule.rule_id, result.file_path))
    print("")
    print(json.dumps(portfolio_override_rule_to_payload(result.rule), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
