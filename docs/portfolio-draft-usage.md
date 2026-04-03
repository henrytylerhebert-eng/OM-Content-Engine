# Portfolio Draft Usage

## Purpose

These draft objects exist so Opportunity Machine can prepare internal working views without pretending they are final truth.

Phase one includes:

- `CapitalReadinessDraft`
- `FounderReportDraft`
- `InternalReportDraft`
- `PortfolioRecommendationDraft`

## What these drafts are for

### `CapitalReadinessDraft`

Use this to prepare a cautious, audience-specific draft of likely capital path and blocking gaps.

- internal audience drafts can support OM routing and discussion
- founder audience drafts can support future founder-facing summaries
- these are not investor-facing outputs
- `review_ready` should be used sparingly and only when linked score and provenance support is present

### `FounderReportDraft`

Use this to assemble founder-safe summary inputs from linked evidence, score, and capital-readiness drafts.

- helpful for operator review and future founder communication
- not automatically approved for sharing

### `InternalReportDraft`

Use this to assemble OM operating summaries for support routing, watchlist review, stuck reasons, and milestone discussion.

- this is the main operational draft output in phase one
- it can include internal-only notes

### `PortfolioRecommendationDraft`

Use this to generate a conservative internal recommendation summary from the current bundle state.

- this is rules-based and explainable
- it helps operators decide what to inspect next
- it is not a final decision or approved judgment

## What these drafts are not

- not source truth
- not reviewed evidence
- not final approved output
- not investor-facing materials

## Provenance rule

Each draft should link back to the records that support it:

- discovery sources
- evidence items
- domain scores
- review queue items
- assumptions
- capital-readiness drafts when a report draft depends on them

Drafts should summarize linked records, not replace them.

## Review-state rule

All draft records start as:

- `truth_stage=interpreted_evidence`
- `review_status=pending_review`
- `draft_status=draft` or `review_ready`

That means:

- a draft can be useful operationally
- a draft is still not final truth
- approval is a separate step

For founder and internal report drafts specifically:

- `review_ready` is allowed only when the draft links to domain score drafts
- `review_ready` is allowed only when the draft also links to discovery sources or evidence items
- those links are there to preserve provenance, not just to decorate the summary

In the phase-one portfolio snapshot bundle:

- a `review_ready` founder/internal draft must point to score ids that are actually present in the bundle
- a `review_ready` founder/internal draft must point to discovery/evidence ids that are actually present in the bundle

For capital-readiness drafts specifically:

- `review_ready` is allowed only when the draft links to domain score drafts
- `review_ready` is allowed only when the draft links to discovery sources or evidence items
- `review_ready` is allowed only when the draft includes a readiness rationale
- inside a portfolio snapshot, a `review_ready` capital-readiness draft must be supported by linked domain scores that are not still `draft`

## Phase-one operating guidance

In phase one, draft outputs should be used for:

1. internal review
2. preparation for operator meetings
3. identifying missing inputs
4. preparing future founder-facing communication

They should not be used for:

1. investor distribution
2. automated capital decisions
3. replacing reviewed evidence
4. claiming readiness beyond what the linked evidence supports
