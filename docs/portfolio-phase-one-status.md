# Portfolio Phase-One Status

## What is real in this checkpoint

- new portfolio schemas for discovery sources, evidence items, assumptions, review queue items, and founder/internal report drafts
- new portfolio score-draft schema with validated OM domain, score, confidence, and evidence-level fields
- new audience-specific capital-readiness draft schema
- new internal-only support-routing draft schema
- new internal-only milestone draft schema
- new rules-based internal recommendation draft assembled from existing portfolio drafts
- new single-company portfolio snapshot bundle structure for inspectable portfolio outputs
- new minimal JSON artifact writer for one-company portfolio snapshots
- new runnable local portfolio pipeline entrypoint for one-company JSON inputs
- new minimal multi-company batch runner that reuses the one-company flow
- new tracked example company input for an end-to-end artifact flow
- new patch-only reviewed-truth override layer for portfolio records
- new operator-safe helper for creating and updating file-backed portfolio override rules
- new Airtable-aligned operational export contract for phase-one portfolio tables
- new example mapping from the Acme portfolio snapshot into Airtable-aligned operational export tables
- shared provenance and review-state fields on the new portfolio records
- internal service interfaces for:
  - discovery-source intake
  - evidence normalization targets
  - domain score draft creation and refresh
  - capital-readiness draft assembly
  - support-routing draft assembly
  - milestone draft assembly
  - rules-based recommendation draft assembly
  - review queue creation
  - founder/internal draft input assembly
  - portfolio snapshot bundle assembly
  - portfolio snapshot artifact writing
  - local portfolio snapshot pipeline execution from a JSON input file
  - local multi-company batch execution from a directory of JSON input files
  - local portfolio reviewed-truth override loading and application
- focused test coverage for the new schema and service behavior

## What is still scaffolded only

- real Google Suite ingestion
- evidence extraction heuristics from raw discovery material
- domain scoring logic
- automated score derivation
- weighted capital-readiness logic
- support-routing recommendation logic
- milestone recommendation logic
- predictive recommendation logic
- founder/internal report prose generation
- any shared operator approval workflow beyond file-backed override authoring
- full Airtable sync or write-back automation
- any UI, dashboard, or investor-facing workflow
- cross-company portfolio aggregation beyond batch manifests and indexes

## What this checkpoint does not claim

- it does not claim the portfolio workflow is end-to-end complete
- it does not claim evidence is auto-reviewed
- it does not claim draft reports are approved for internal or founder use
- it does not claim capital-readiness drafts are investor-ready
- it does not claim simulation output is usable as reviewed evidence

## Review-state position

- `DiscoverySource` lands as `raw_input`
- `EvidenceItem` lands as `extracted_signal`
- `Assumption` lands as `interpreted_evidence`
- `DomainScore` lands as `interpreted_evidence`
- `CapitalReadinessDraft` lands as `interpreted_evidence`
- report drafts land as `interpreted_evidence`
- explicit queue items are created when a company link, source anchor, statement, or domain is missing
- extracted evidence can be queued for manual promotion to `reviewed_evidence`, but it is never promoted automatically
- draft outputs may link to reviewed inputs, but the draft itself is still not final truth until separately reviewed or approved
- founder/internal drafts cannot move to `review_ready` unless they include linked domain score ids and linked discovery/evidence provenance
- capital-readiness drafts cannot move to `review_ready` unless they include linked domain score ids, linked provenance, and a readiness rationale
- review-ready capital-readiness drafts must be supported by non-draft linked domain scores when bundled into a snapshot
- support-routing and milestone drafts remain internal-only operating drafts in phase one
- support-routing and milestone drafts cannot move to `review_ready` unless they include linked domain score ids, linked provenance, and rationale fields
- review-ready support-routing and milestone drafts must be supported by non-draft linked domain scores and reviewed evidence when bundled into a snapshot
- the new recommendation layer is rules-based only and remains an internal draft artifact
- recommendations summarize current signals and gaps, but they do not replace score review or operator judgment
- the snapshot bundle can include review-ready drafts only when those links are also present in the bundled records
- portfolio reviewed-truth overrides are applied after the source-derived snapshot bundle is built and are logged separately from the raw input
- Airtable-aligned operational exports are written after snapshot assembly and remain derived operating views, not source truth
- the runnable Acme example now proves one-company flow from raw input to reviewed truth to snapshot to Airtable-aligned export bundle
- the new batch runner simply repeats that one-company flow across multiple local inputs and writes a batch manifest plus company index

## Why this is the right scope

This checkpoint establishes the structural path:

1. intake discovery material
2. point at candidate evidence
3. assemble conservative score drafts from reviewed evidence only
4. assemble audience-specific capital-readiness drafts from linked score and evidence inputs
5. assemble internal-only support-routing and milestone drafts from linked records
6. assemble a rules-based internal recommendation draft from the current bundle state
7. create review work where needed
8. assemble founder/internal draft inputs from linked records
9. bundle one company into an inspectable phase-one portfolio snapshot
10. write the snapshot as JSON artifacts for inspection or handoff
11. run the whole flow from a local example input file without external services
12. preserve reviewed evidence and internal draft decisions through a separate reviewed-truth file
13. process multiple local company inputs in one run without changing the one-company architecture

That is enough to support the next batch without overbuilding.
