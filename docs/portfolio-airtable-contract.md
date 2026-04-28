# Portfolio Airtable Contract

## Purpose

This contract gives phase-one portfolio records a stable, Airtable-aligned table shape without adding full sync or write-back automation.

For the locked 3 to 5 company pilot schema, use `docs/portfolio-airtable-pilot-contract-lock.md` as the authoritative working spec.

It is a one-way operational handoff:

1. Airtable exports and other discovery material come into the repo as source truth.
2. The repo builds reviewed and draft portfolio structures.
3. The repo can write Airtable-aligned operational table outputs for staff use.

## Phase-One Tables

The contract currently exports these table-shaped outputs:

- `Companies`
- `Evidence Items`
- `Assumptions`
- `Domain Scores`
- `Capital Readiness`
- `Support Routing`
- `Action Items`
- `Milestones`

## Important Boundaries

- Raw discovery input remains separate from reviewed-truth overrides.
- Reviewed-truth overrides remain separate from operational export rows.
- Airtable-aligned operational rows are not source truth.
- Explicit company names should be carried through the input bundle for pilot exports. Inferred company names are a fallback only, not a recommended pilot input.
- `Support Routing` and `Milestones` are exported only from explicit draft records in phase one. The export contract does not invent those rows from capital-readiness or report fallback fields.
- `Action Items` remain draft operational projections in phase one.
- Investor-facing outputs are out of scope.

## Why This Is The Smallest Useful Contract

This shape is enough to connect the repo to the real OM operating model because it gives staff stable table outputs they can inspect, import manually later, or compare against Airtable without needing sync logic yet.

It does not try to decide:

- how Airtable views are configured
- how manual edits should round-trip
- how write-back should work
- how multi-company batching should be orchestrated

## Example Command

```bash
python3 -m src.reporting.portfolio_operational_export
```

That command uses the runnable portfolio example and writes Airtable-aligned JSON tables into:

`data/processed/portfolio_example/airtable_operational_export/`

It also writes `airtable_operational_example_summary.json`, which groups the example export by Airtable table shape and keeps the draft boundary visible.

See `docs/portfolio-airtable-example.md` for the Acme example mapping.

## Smallest Viable Repo <-> Airtable Contract

For phase one, the smallest viable contract is:

- one-way Airtable exports into `data/raw/`
- repo-side reviewed truth in `data/reviewed_truth/`
- repo-side operational export tables in `data/processed/`
- stable row ids and field names
- explicit truth-stage and review-status fields on exported records

That keeps Airtable as the operational system of record while letting the repo hold normalization rules, reviewed-truth logic, and draft operating outputs safely beside it.
