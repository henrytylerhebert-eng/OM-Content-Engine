# Portfolio Batching

## Purpose

Phase one now includes a smallest viable multi-company batch runner.

Its job is simple:

- reuse the existing one-company portfolio flow
- process multiple local company input files in one run
- keep each company in its own artifact folder
- write a top-level batch manifest and company index

## Input Contract

The batch runner looks for local company JSON files in one directory.

Optional reviewed-truth overrides are resolved by companion filename:

- input file: `acme_phase_one.json`
- override file: `acme_phase_one_overrides.json`

If the companion override file is missing, the company still runs.
That keeps the batch runner file-backed and phase-one friendly.

## Output Shape

The batch run writes:

- one subdirectory per company input file
- the normal one-company snapshot artifact pack inside each subdirectory
- `portfolio_batch_manifest.json`
- `portfolio_batch_index.json`

The batch manifest contains:

- input file
- optional override file
- output directory
- organization id
- report period
- snapshot id
- reviewed-truth applied flag
- draft-status summary

The batch index is a lighter lookup file for quick scanning.

## Boundary Rules

- this reuses the one-company flow exactly
- it does not merge company truth together
- it does not add sync, UI, or investor-facing outputs
- each company keeps its own review-state and provenance boundaries

## Example Command

```bash
python3 -m src.reporting.portfolio_batch
```

By default that command processes all JSON files in `data/raw/portfolio_example/` and writes output to `data/processed/portfolio_batch_example/`.
