# Portfolio Airtable Pilot Contract Lock

## A. Pilot contract summary

This document freezes the phase-one Airtable contract for a limited 3 to 5 company pilot.

It is stable enough for a one-way operational pilot.
It is not a full production contract.

The pilot uses these 8 tables:

- `Companies`
- `Evidence Items`
- `Assumptions`
- `Domain Scores`
- `Capital Readiness`
- `Support Routing`
- `Action Items`
- `Milestones`

Use these tables in two groups:

- Core working tables:
  - `Companies`
  - `Evidence Items`
  - `Assumptions`
  - `Domain Scores`
  - `Capital Readiness`
- Derived read-only tables:
  - `Support Routing`
  - `Action Items`
  - `Milestones`

Contract position for the pilot:

- Airtable is an operational working surface, not the only truth layer.
- Raw discovery material remains outside Airtable.
- Reviewed-truth overrides remain outside Airtable.
- Exported Airtable rows are derived operating records.
- Founder-facing and internal-facing rows remain draft-oriented.
- No investor-facing rows are included.

## B. Table-by-table contract

### `Companies`

Purpose:
- one row per company per report period
- portfolio summary entry point for operators

Required fields:
- `id`
- `organization_id`
- `report_period`
- `company_name`
- `reviewed_evidence_count`
- `pending_evidence_count`
- `review_ready_domain_score_count`
- `capital_readiness_draft_count`

Optional fields:
- `watchlist_status`
- `recommended_support_route`
- `milestone_status`

Rules:
- `company_name` must be explicit in pilot input. Do not rely on inferred names.
- `id` is system-managed and not operator-editable.
- there should be exactly one `Companies` row per `organization_id` plus `report_period`

### `Evidence Items`

Purpose:
- truth-pressure table for evidence and provenance

Required fields:
- `id`
- `organization_id`
- `discovery_source_id`
- `primary_domain`
- `evidence_statement`
- `evidence_level`
- `truth_stage`
- `review_status`

Optional fields:
- `evidence_type`
- `observed_at`
- `excerpt`
- `reviewed_by`
- `reviewed_at`
- `linked_assumption_ids`
- `source_system`
- `source_url`
- `source_path`

Rules:
- every row must remain traceable to a source via `discovery_source_id`
- `truth_stage` must make it clear whether the row is still extracted or already reviewed
- `evidence_level` must stay in the approved `0-7` range
- operators should treat this as the closest Airtable table to source truth

### `Assumptions`

Purpose:
- explicit hypotheses, gaps, or unresolved beliefs

Required fields:
- `id`
- `organization_id`
- `domain_key`
- `title`
- `statement`
- `status`

Optional fields:
- `owner`
- `linked_evidence_ids`

Rules:
- assumption rows should stay linked to evidence where possible
- this table should surface uncertainty, not hide it

### `Domain Scores`

Purpose:
- draft score view by domain

Required fields:
- `id`
- `organization_id`
- `domain_key`
- `evidence_level`
- `rationale`
- `key_gap`
- `next_action`
- `score_status`

Optional fields:
- `raw_score`
- `confidence`
- `linked_assumption_ids`
- `score_basis_evidence_ids`

Rules:
- `raw_score` may be blank
- if present, `raw_score` must stay in the approved `1-5` range
- `confidence` may be blank
- if present, `confidence` must be `low`, `moderate`, or `high`
- no row should appear more final than its linked evidence supports
- `score_status` is the primary Airtable-facing maturity signal for this table

### `Capital Readiness`

Purpose:
- cautious capital-path draft for internal or founder use

Required fields:
- `id`
- `organization_id`
- `report_period`
- `audience`
- `draft_status`
- `review_status`
- `truth_stage`
- `readiness_status`
- `primary_capital_path`
- `readiness_rationale`
- `blocking_gaps`
- `required_evidence`

Optional fields:
- `linked_domain_score_ids`
- `linked_evidence_ids`

Rules:
- `audience` is limited to `internal` or `founder` in phase one
- capital-readiness rows remain draft outputs, not final truth
- this table should stay sparse and conservative
- do not use this table to imply investor readiness

### `Support Routing`

Purpose:
- derived draft view of what support OM should route next

Required fields:
- `id`
- `organization_id`
- `report_period`
- `audience`
- `route_recommendation`
- `route_category`
- `route_rationale`

Optional fields:
- `priority_domain`

Rules:
- phase-one rows should be `internal` only
- rows are exported only from explicit support-routing drafts
- if no explicit support-routing draft exists, export no row
- this table is read-only for the pilot

### `Action Items`

Purpose:
- derived draft view of concrete next actions

Required fields:
- `id`
- `organization_id`
- `report_period`
- `audience`
- `action_text`
- `action_type`

Optional fields:
- none in the pilot-facing field set

Rules:
- rows are draft operating outputs
- this table is read-only for the pilot
- operators should use it as a task signal, not as source truth

### `Milestones`

Purpose:
- derived draft view of the next proof point or operating checkpoint

Required fields:
- `id`
- `organization_id`
- `report_period`
- `audience`
- `milestone_text`
- `milestone_type`
- `milestone_rationale`

Optional fields:
- `target_window`
- `priority_domain`

Rules:
- phase-one rows should be `internal` only
- rows are exported only from explicit milestone drafts
- if no explicit milestone draft exists, export no row
- this table is read-only for the pilot

## C. Operator rules

What operators should edit:

- Airtable views, filters, and groupings
- comments, discussion, and manual follow-up outside the locked contract fields
- optional Airtable-only helper columns that are clearly outside the repo contract
  - examples: `Pilot Notes`, `Owner Notes`, `Manual Follow-up`

What operators should not edit:

- `id`
- `organization_id`
- `report_period`
- exported review-state fields
- exported truth-stage fields
- exported counts
- exported score fields
- exported capital-readiness fields
- derived draft tables as if they were source truth

Important operator rule:

- if staff make a real review decision, score adjustment, or draft approval, that decision belongs in the repo reviewed-truth layer, not only in Airtable

Pilot interpretation rules:

- `Evidence Items` is the closest table to truth inside Airtable
- `Domain Scores` and `Capital Readiness` are draft interpretation layers
- `Support Routing`, `Action Items`, and `Milestones` are draft operational outputs
- founder/internal audience rows must not be confused with approved external outputs

## D. Repo-to-Airtable boundary

What stays in the repo for phase one:

- raw discovery material in `data/raw/`
- reviewed-truth overrides in `data/reviewed_truth/`
- full snapshot artifacts in `data/processed/`
- review queue items
- founder report draft artifacts
- internal report draft artifacts
- recommendation draft artifacts
- detailed override and provenance metadata not needed in pilot views

What moves into Airtable for the pilot:

- only the 8 operational tables listed in this document
- only the field set frozen in this document for operator-facing use

Boundary rules:

- Airtable rows are one-way exports from the repo for this pilot
- Airtable edits do not write back into the repo
- repo reruns may overwrite exported contract fields
- any Airtable-only helper fields must be treated as local pilot conveniences, not repo truth

## E. Deferred decisions

These decisions are intentionally deferred until after pilot validation:

- whether Airtable should become a true linked-record system or stay id-based longer
- whether `Support Routing`, `Action Items`, and `Milestones` should remain separate tables
- whether `Capital Readiness` needs a narrower or broader field set
- whether `Companies` should gain more operator-facing company metadata
- whether score scale wording or confidence wording needs refinement for operators
- whether founder-facing Airtable views are useful enough to keep
- how write-back or sync should work
- how approval workflow should work beyond the current one-way pilot

## F. Pilot success criteria

The pilot is successful if:

- 3 to 5 real companies can be exported into Airtable without contract changes
- operators can understand one company from `Companies` and then drill into `Evidence Items`, `Domain Scores`, and `Capital Readiness`
- operators can tell the difference between reviewed evidence and draft interpretation
- explicit company names remain stable across reruns
- missing explicit support-routing or milestone drafts result in empty tables, not invented rows
- staff do not need sync, write-back, or UI expansion to learn from the pilot
- the pilot produces clear feedback on which fields should be hidden, renamed, or collapsed before phase two
