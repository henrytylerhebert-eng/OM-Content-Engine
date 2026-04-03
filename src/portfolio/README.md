# Portfolio Workflow Scaffold

This package holds the phase-one Opportunity Machine portfolio workflow layer.

## Implemented in this checkpoint

- discovery-source intake interfaces
- evidence extraction target structures
- domain score draft structures and conservative score assembly inputs
- capital-readiness draft structures
- portfolio review queue object wiring
- founder and internal report draft input assembly
- single-company portfolio snapshot bundle assembly
- minimal JSON artifact writer for one-company portfolio snapshots
- runnable local portfolio pipeline entrypoint for one-company JSON inputs
- minimal multi-company batch runner that reuses the one-company flow
- tracked example company input for an end-to-end artifact flow
- patch-only reviewed-truth override layer for portfolio records
- operator-safe helper for creating and updating file-backed portfolio override rules
- Airtable-aligned operational export structures and table writers
- review-ready validation for founder and internal draft transitions
- stronger review-ready validation for capital-readiness drafts
- internal-only support-routing and milestone draft structures
- rules-based internal recommendation draft assembly
- review-ready validation for support-routing and milestone drafts
- shared provenance and review-state schema fields for the new portfolio records

## Scaffolded only in this checkpoint

- automatic discovery extraction rules
- automated score generation
- capital-readiness logic
- support-routing recommendation logic
- milestone recommendation logic
- predictive or black-box recommendation logic
- investor-facing outputs
- report narrative generation
- any UI or dashboard layer
- cross-company portfolio aggregation logic beyond batch manifests

## Important rules

- real discovery inputs remain the source of truth
- extracted evidence starts as `extracted_signal` and `pending_review`
- nothing here auto-promotes evidence to reviewed or approved output
- founder/internal drafts cannot be marked `review_ready` unless they link back to score drafts and discovery/evidence provenance
- capital-readiness drafts cannot be marked `review_ready` unless they include linked score support, linked provenance, and a readiness rationale
- support-routing and milestone drafts are internal-only, draft-oriented operational records
- support-routing and milestone drafts cannot be marked `review_ready` unless they link back to non-draft score support and reviewed evidence when bundled into a snapshot
- rules-based recommendations remain internal draft guidance assembled from current score, evidence, assumption, and capital-readiness records
- reviewed-truth overrides are patch-only and are kept separate from raw example inputs
- current content and editorial flows remain separate
- the batch runner only orchestrates multiple one-company runs; it does not merge truth across companies
