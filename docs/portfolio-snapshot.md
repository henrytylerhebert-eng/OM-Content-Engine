# Portfolio Snapshot Bundle

## What this is

The phase-one portfolio snapshot is a minimal, inspectable bundle for one company.

The repo now includes a runnable example input at `data/raw/portfolio_example/acme_phase_one.json` and a local command:

```bash
python3 -m src.reporting.portfolio_pipeline
```

By default that command writes inspectable JSON artifacts to `data/processed/portfolio_example/`.
By default it also applies `data/reviewed_truth/portfolio_example_overrides.json` after the source-derived snapshot is built.

It is meant to show the current state of:

- discovery sources
- evidence items
- assumptions
- domain score drafts
- capital-readiness drafts
- rules-based internal recommendation draft
- founder report draft
- internal report draft
- linked review queue items

## What it is not

- It is not source truth on its own.
- It is not an investor-facing output.
- It is not an approval engine.
- It is not a scoring or capital decision system.

Real discovery inputs remain the source of truth. The bundled drafts are interpreted operating artifacts that still require review and approval.
Reviewed-truth overrides are a separate patch layer applied after the source-derived snapshot is built.

## Phase-one boundary rules

- Every bundled record must belong to the same company.
- Report-period-bearing drafts must match the snapshot report period.
- Capital-readiness drafts remain limited to `internal` and `founder` audiences in phase one.
- Founder and internal drafts may be marked `review_ready` only when they include:
  - linked domain score draft ids
  - linked discovery source ids or linked evidence ids
- Capital-readiness drafts may be marked `review_ready` only when they include:
  - linked domain score draft ids
  - linked discovery source ids or linked evidence ids
  - a readiness rationale
- If a founder/internal draft is `review_ready`, the linked score ids and provenance ids must also exist inside the bundled snapshot.
- If a capital-readiness draft is `review_ready`, the linked score ids and provenance ids must also exist inside the bundled snapshot.
- If a capital-readiness draft is `review_ready`, its linked domain scores must not still be `draft`.

## Why this matters

This keeps the phase-one portfolio output honest.

The snapshot can be inspected end to end, but it still preserves the separation between:

- raw input
- extracted signal
- interpreted evidence
- reviewed evidence
- draft operating output

That separation matters because Opportunity Machine is using this system to support decisions, not to generate polished but ungrounded summaries.
