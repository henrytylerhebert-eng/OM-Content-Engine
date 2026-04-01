# Content Candidates

This export is the small internal-only candidate list for content planning and brief generation.

It is not a publishing feed.

## Where It Is Written

Each pipeline run now writes:

- `content_candidates.json`
- `content_candidates.csv`

into the run directory, such as `data/processed/local_run/`.

## What It Includes

The export pulls from the existing reviewed output layer and only includes records that are useful enough to consider now.

Current inclusion rule:

- `spotlight_ready`
- or reviewed-truth-backed

Current guardrails:

- exclude internal records from content planning
- exclude unreviewed semi-structured member-side people
- exclude records with material unresolved trust problems
- keep `public_ready` stricter than `planning_safe`

## Core Fields

- `entity_id`: stable entity identifier from the reviewed collections
- `org_name`: organization context when available
- `primary_person_name`: best human anchor for the candidate
- `person_provenance`: structured member-side, semi-structured member-side, or mentor-derived
- `readiness_level`: highest current readiness rung
- `trust_basis`: `heuristic_only`, `reviewed_truth_backed`, or `human_approved`
- `why_it_matters`: short internal hook for planning
- `suggested_use`: lightweight internal recommendation such as `linkedin_post`, `carousel`, `mini_feature`, or `hold_for_review`
- `supporting_evidence_summary`: short evidence summary
- `review_flag_summary`: compact unresolved review burden summary
- `planning_safe`: safe for internal planning use
- `public_ready`: safe for public-facing use under current rules

## How To Use It

- Start with `content_candidates.json` for internal planning and brief drafting.
- Use `content_candidates.csv` when a flat export is easier to scan or sort.
- Treat `planning_safe=true` as internal-use permission only.
- Treat `public_ready=true` as the only public-facing green light.

`spotlight_ready` helps a record enter the candidate list.
It does not make the record public-ready on its own.
