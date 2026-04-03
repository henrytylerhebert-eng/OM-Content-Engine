# Portfolio Reviewed Truth

## Purpose

The phase-one portfolio reviewed-truth layer gives Opportunity Machine one narrow place to store durable human decisions for portfolio records.

It exists so a company's reviewed evidence, manual score adjustments, and internal draft approvals can survive reruns without editing the raw example input.

## Smallest Viable Model

For phase one, the override model is intentionally narrow:

- one local JSON file
- patch-only rules
- no suppression engine
- internal operational use only
- no investor-facing output logic

This is the smallest useful shape because it preserves raw input separately while still allowing a few durable decisions to survive reruns.

## Where It Lives

- default local path: `data/reviewed_truth/portfolio_overrides.json`
- example tracked file: `data/reviewed_truth/portfolio_example_overrides.json`
- starter template: `data/reviewed_truth/portfolio_overrides.example.json`
- operator helper usage: `docs/portfolio-override-authoring.md`

## Supported Targets

Phase one supports overrides only for:

- `evidence_items`
- `domain_scores`
- `capital_readiness_drafts`
- `founder_report_draft`
- `internal_report_draft`
- `review_queue_items`

It does not support overrides on discovery sources or raw input files.

## Conservative Rules

- Overrides are patch-only. They cannot suppress records in phase one.
- External approval states are not allowed.
- Evidence overrides may only promote evidence to `reviewed_evidence`.
- Capital-readiness and report draft overrides are limited to internal/founder operational states.
- Review queue overrides are for resolving or annotating queue items, not hiding them.
- The operator helper creates only one validated rule at a time so staff do not need to hand-edit the whole file.

## Why This Is The Right Scope

This keeps the override layer useful without turning it into a workflow engine.

The raw input file still tells you what discovery material and draft inputs were supplied.
The override file tells you what human decisions were later applied.

That separation keeps provenance readable and prevents manual decisions from being confused with source truth.

For the runnable Acme example, the tracked override file demonstrates reviewed evidence and score adjustment only.
Founder and internal report outputs remain draft-only in that example flow.
