# Review Workflow

## Purpose

The transform layer is supposed to be conservative. That only works if ambiguous records have a predictable review path.

This repo now treats review flags as a lightweight queue mechanism:

- transforms emit structured review flags with source context
- each flag has a severity
- each flag has a recommended action
- reporting helpers can turn flagged rows into review queue entries

## How To Use It

1. Run a raw import and normalization pass.
2. Collect all review flags produced during normalization.
3. Convert those flags into queue rows using `src/transform/review_flags.py`.
4. Review high-severity rows first, then medium, then low.

## Current Flag Priorities

### High

- `review_missing_organization_name`
- `review_missing_cohort_name`
- `review_missing_interaction_subject`

These block useful downstream records.

### Medium

- `review_org_type`
- `review_affiliation_missing_organization`
- `review_no_person_found`
- `review_missing_interaction_date`
- `review_content_profile_sparse`

These records can still land, but they need cleanup before they are reliable for segmentation or reporting.

### Low

- `review_person_missing_email`
- `review_no_affiliation_people`
- `review_missing_content_assets`

These are still useful records, but they weaken matching and outreach quality.

## Suggested Queue Row Shape

Each review row should include:

- `source_table`
- `source_record_id`
- `source_field` when the problem is tied to one raw field
- `raw_value` when the transform can safely preserve the triggering value
- `flag_code`
- `flag_type`
- `severity`
- `description`
- `recommended_action`
- `record_label` if one is available

That shape is intentionally simple so it can later feed a spreadsheet, Airtable view, or reporting export without needing more infrastructure.

## What Gets Flagged

The current transforms should flag records like these:

- unclear organization type
- grouped or free-text `Personnel` values
- member-side `Personnel` rows that almost created a person but failed the trust-first rule
- sparse rows with too little context
- placeholder names like `TBD`
- duplicate-looking people in the same row
- multi-value or invalid cohort cells
- internal OM records
- interaction rows missing a date or subject

## What A Human Resolves Later

The human review step is expected to:

- confirm the right org type when the source is weak
- split `Personnel` text into real people only when it is safe
- confirm whether a single member-side `Personnel` value plus one email is enough to create a real person
- split multi-cohort cells into separate cohort history
- decide whether a row is internal, grouped, placeholder, or usable
- add missing names or emails when the source clearly supports it elsewhere

## What The System Should Never Silently Guess

The transform layer should never silently guess:

- that a grouped team label is a real person
- that a first-name-only `Personnel` value is a real person
- that a generic email such as `info@...` belongs to one specific person
- that one semi-structured person can be tied across multiple organizations or mixed row context
- that a multi-value cohort cell can be split safely without review
- that a weak employer string should become an organization
- that a summary field like `Meeting Requests` is a real dated interaction
- that a placeholder record is safe for reporting or outreach

## Where Resolved Decisions Live

When a human wants a decision to survive future runs, it should move into reviewed truth:

- local file: `data/reviewed_truth/overrides.json`
- model doc: `docs/reviewed-truth.md`

That layer is for durable approved corrections such as:

- confirmed org type
- internal classification
- spokesperson designation
- record suppression
- resolved review-flag suppression

The transform layer should stay conservative. Reviewed truth is where deliberate human exceptions belong.
