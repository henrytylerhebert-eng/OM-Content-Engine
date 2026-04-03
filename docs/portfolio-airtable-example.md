# Portfolio Airtable Example

## Purpose

This doc shows how the runnable Acme example moves through the phase-one operating flow:

1. raw input
2. reviewed-truth overrides
3. portfolio snapshot
4. Airtable-aligned operational export tables

The goal is not to show live sync.
The goal is to prove that one company can move through the full internal workflow shape cleanly.

## Example Inputs

- raw company input: `data/raw/portfolio_example/acme_phase_one.json`
- reviewed-truth overrides: `data/reviewed_truth/portfolio_example_overrides.json`

The override example keeps founder and internal report outputs draft-only.
It only demonstrates:

- reviewed evidence promotion
- review queue resolution
- domain score adjustment
- no support-routing or milestone approval override is applied in the example

## Commands

Build the snapshot bundle:

```bash
python3 -m src.reporting.portfolio_pipeline
```

Build the Airtable-aligned operational export bundle:

```bash
python3 -m src.reporting.portfolio_operational_export
```

## Example Table Grouping

For the current Acme example, the operational export groups into:

- `Companies`: 1
- `Evidence Items`: 2
- `Assumptions`: 2
- `Domain Scores`: 2
- `Capital Readiness`: 2
- `Support Routing`: 1
- `Action Items`: 4
- `Milestones`: 1

## What Each Table Represents

### `Companies`

One summary row for the company in the selected report period.
This is not the raw source record.
It is the portfolio operating summary row that points back to the snapshot.

### `Evidence Items`

Normalized evidence rows with:

- domain assignment
- evidence level
- provenance fields
- truth stage
- review status
- reviewed-truth markers when overrides were applied

### `Assumptions`

Tracked hypotheses and gaps linked to evidence.

### `Domain Scores`

Draft score rows that preserve:

- raw score when available
- confidence
- evidence level
- rationale
- key gap
- next action
- linked evidence and assumption ids

### `Capital Readiness`

Audience-specific draft rows for founder/internal use only.

### `Support Routing`

Draft operational routing rows taken from explicit internal support-routing drafts when present.
These are phase-one projections, not source truth.
They remain internal operational artifacts only.

### `Action Items`

Draft operational next-action rows derived from:

- domain score `next_action`
- founder report `recommended_next_actions`

### `Milestones`

Draft operational milestone rows taken from explicit internal milestone drafts when present.
If explicit drafts do not exist yet, the export layer can still derive draft milestone rows from other draft artifacts.

## Boundary Check

The Acme example preserves these boundaries:

- raw input remains in `data/raw/`
- reviewed truth remains in `data/reviewed_truth/`
- snapshot artifacts remain in `data/processed/portfolio_example/`
- Airtable-aligned operational export rows remain derived operational views

The founder and internal report outputs remain draft-only in this example.
The support-routing and milestone rows also remain internal draft projections in this example.
That keeps the example aligned with phase-one operating honesty.
