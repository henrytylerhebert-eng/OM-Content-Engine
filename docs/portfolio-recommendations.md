# Portfolio Recommendations

## Purpose

Phase one now includes a smallest viable recommendation layer for internal use.

Its job is to summarize the current draft state into a conservative operating view:

- top risks
- strongest signals
- next validation steps
- support recommendations
- likely near-term capital path label
- what should not be pursued yet

## What it is

This layer is:

- rules-based
- internal only
- draft-oriented
- explainable from existing records

It is assembled from the current bundle state after reviewed-truth overrides are applied.

That means it can reflect:

- reviewed evidence promotions
- manual score adjustments
- current capital-readiness drafts
- explicit support-routing drafts
- explicit milestone drafts

## What it is not

- not source truth
- not predictive modeling
- not investor-facing logic
- not automated approval
- not a replacement for operator judgment

## Rule Shape

The current rules are intentionally simple:

- top risks prioritize domains that are still draft, still missing grounded scores, or still waiting on reviewed evidence
- strongest signals prefer reviewed evidence, but can include pending-review signals with that boundary stated explicitly
- next validation steps come from linked score next actions, required evidence, and milestone drafts
- support recommendations come from explicit support-routing drafts first, then internal capital-readiness drafts
- likely near-term capital path comes from the current internal capital-readiness draft and keeps its readiness label attached
- what should not be pursued yet is derived conservatively from unresolved capital-readiness and unreviewed evidence

## Boundary Rule

The recommendation artifact always remains a draft.

It can help OM decide what to look at next, but it should never be treated as:

- final truth
- an approved score interpretation
- an investor-ready capital judgment
