# Portfolio Airtable Pilot Validation Pack

## A. Objective

Prepare a limited Airtable pilot for 3 to 5 real OM companies using the current one-way export contract.

This pack is meant to answer one practical question:

Can OM operators use the current export contract to manage real portfolio workflow without confusing source truth, reviewed truth, and draft operating output?

This pack assumes:

- Airtable is the phase-one operational system of record
- the repo remains the normalization, reviewed-truth, and export layer
- the pilot is one-way only
- no sync, write-back, UI, or investor-facing outputs are in scope

## B. Current Airtable contract summary

The current export contract supports these 8 tables:

- `Companies`
- `Evidence Items`
- `Assumptions`
- `Domain Scores`
- `Capital Readiness`
- `Support Routing`
- `Action Items`
- `Milestones`

The exact table shapes are implemented in `src/portfolio/airtable_contract.py`.

Current contract position:

- raw discovery input stays outside Airtable
- reviewed-truth overrides stay outside Airtable
- Airtable rows are derived operating records
- explicit company names are expected for real pilot companies
- `Support Routing` and `Milestones` export only from explicit drafts
- `Action Items` remains a derived draft table

## C. Stable fields for pilot

These fields are stable enough now for real pilot use.

### `Companies`

- `id`
- `organization_id`
- `report_period`
- `company_name`
- `reviewed_evidence_count`
- `pending_evidence_count`
- `review_ready_domain_score_count`
- `capital_readiness_draft_count`
- `watchlist_status`
- `recommended_support_route`
- `milestone_status`

### `Evidence Items`

- `id`
- `organization_id`
- `discovery_source_id`
- `primary_domain`
- `evidence_statement`
- `evidence_level`
- `truth_stage`
- `review_status`
- `reviewed_by`
- `reviewed_at`
- `source_system`
- `source_url`
- `source_path`

### `Assumptions`

- `id`
- `organization_id`
- `domain_key`
- `title`
- `statement`
- `status`
- `owner`
- `linked_evidence_ids`

### `Domain Scores`

- `id`
- `organization_id`
- `domain_key`
- `raw_score`
- `confidence`
- `evidence_level`
- `rationale`
- `key_gap`
- `next_action`
- `score_status`

### `Capital Readiness`

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

### `Support Routing`

- `id`
- `organization_id`
- `report_period`
- `audience`
- `route_recommendation`
- `route_category`
- `route_rationale`
- `priority_domain`

### `Action Items`

- `id`
- `organization_id`
- `report_period`
- `audience`
- `action_text`
- `action_type`

### `Milestones`

- `id`
- `organization_id`
- `report_period`
- `audience`
- `milestone_text`
- `milestone_type`
- `milestone_rationale`
- `target_window`
- `priority_domain`

## D. Unstable or risky fields

These fields are still too repo-centric, awkward, or ambiguous for normal operator views.

### `Companies`

- `company_name_inferred`
- `portfolio_snapshot_id`
- `source_truth_statement`
- `draft_boundary_statement`
- `domain_score_count`
- `founder_report_draft_id`
- `founder_report_draft_status`
- `founder_report_review_status`
- `internal_report_draft_id`
- `internal_report_draft_status`
- `internal_report_review_status`

### `Evidence Items`

- `secondary_domains`
- `confidence_note`
- `interpretation_note`
- `review_notes`
- `reviewed_truth_applied`
- `reviewed_override_ids`
- `source_table`
- `source_record_id`
- `source_document_id`
- `row_hash`

### `Assumptions`

- `assumption_type`
- `validation_plan`
- `next_check_date`
- `truth_stage`
- `review_status`
- `review_notes`
- `contradicting_evidence_ids`
- `source_system`
- `source_table`
- `source_record_id`
- `source_url`
- `source_path`

### `Domain Scores`

- `truth_stage`
- `review_status`
- `review_notes`
- `reviewed_by`
- `reviewed_at`
- `pending_evidence_ids`
- `linked_review_queue_ids`
- `generated_by`
- `reviewed_truth_applied`
- `reviewed_override_ids`

### `Capital Readiness`

- `secondary_capital_paths`
- `support_routing_recommendation`
- `next_milestone`
- all long-form linked id sets beyond what operators need immediately
- `generated_by`
- `reviewed_truth_applied`
- `reviewed_override_ids`

### `Support Routing`

- `route_source_type`
- `route_source_id`
- `source_draft_status`
- `source_truth_stage`
- `source_review_status`
- all linkage fields
- `operational_status`

### `Action Items`

- `source_record_type`
- `source_record_id`
- `source_domain_key`
- `source_draft_status`
- `source_truth_stage`
- `source_review_status`
- all linkage fields
- `operational_status`

### `Milestones`

- `source_record_type`
- `source_record_id`
- `source_draft_status`
- `source_truth_stage`
- `source_review_status`
- all linkage fields
- `operational_status`

## E. Minimum viable pilot schema

Use these 8 tables, but in two operating modes.

### Core working tables

- `Companies`
- `Evidence Items`
- `Assumptions`
- `Domain Scores`
- `Capital Readiness`

These are the tables operators should work from first.

### Derived read-only tables

- `Support Routing`
- `Action Items`
- `Milestones`

These should be visible, but clearly marked as derived draft outputs.

### Minimum pilot-facing schema by table

#### `Companies`

- `id`
- `organization_id`
- `report_period`
- `company_name`
- `reviewed_evidence_count`
- `pending_evidence_count`
- `review_ready_domain_score_count`
- `capital_readiness_draft_count`
- `watchlist_status`
- `recommended_support_route`
- `milestone_status`

#### `Evidence Items`

- `id`
- `organization_id`
- `discovery_source_id`
- `primary_domain`
- `evidence_statement`
- `evidence_level`
- `truth_stage`
- `review_status`
- `reviewed_by`
- `reviewed_at`
- `source_system`
- `source_url`
- `source_path`

#### `Assumptions`

- `id`
- `organization_id`
- `domain_key`
- `title`
- `statement`
- `status`
- `owner`
- `linked_evidence_ids`

#### `Domain Scores`

- `id`
- `organization_id`
- `domain_key`
- `raw_score`
- `confidence`
- `evidence_level`
- `rationale`
- `key_gap`
- `next_action`
- `score_status`

#### `Capital Readiness`

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

#### `Support Routing`

- `id`
- `organization_id`
- `report_period`
- `audience`
- `route_recommendation`
- `route_category`
- `route_rationale`
- `priority_domain`

#### `Action Items`

- `id`
- `organization_id`
- `report_period`
- `audience`
- `action_text`
- `action_type`

#### `Milestones`

- `id`
- `organization_id`
- `report_period`
- `audience`
- `milestone_text`
- `milestone_type`
- `milestone_rationale`
- `target_window`
- `priority_domain`

## F. Operator workflow assumptions

This pilot only works if these assumptions hold:

- operators start from `Companies`
- they drill into `Evidence Items` before trusting draft interpretations
- `Domain Scores` and `Capital Readiness` are treated as draft operating views
- `Support Routing`, `Action Items`, and `Milestones` are treated as read-only outputs
- founder-facing rows are separated into filtered views, not mixed into default internal workflows
- Airtable helper columns may exist, but they are local operating aids, not repo truth
- real review decisions still belong in repo-side reviewed-truth files

## G. Risks

Top risks for the pilot:

- score semantics may still be too soft if OM has not locked what `1-5` means in plain English
- readiness semantics may still feel too final unless operators are pre-briefed
- `Companies` may still feel half summary and half metadata
- provenance is technically strong but may overwhelm operators if too many columns are exposed
- `Capital Readiness`, `Support Routing`, and `Milestones` still overlap conceptually
- `Action Items` may feel like duplicate output rather than a useful working table
- staff may read draft outputs as approved decisions if the boundary language is not reinforced

## H. Next best move

Use this validation pack plus the locked pilot contract to run the manual Airtable pilot.

Before the pilot:

1. expose only the minimum pilot-facing fields in Airtable views
2. require explicit company names for all pilot companies
3. mark `Support Routing`, `Action Items`, and `Milestones` as derived draft tables
4. brief operators on the boundary:
   - evidence is closest to truth
   - reviewed-truth decisions live outside Airtable
   - scores and readiness are drafts
   - support routing, action items, and milestones are derived draft outputs

During the pilot, observe:

- which tables operators actually use first
- which fields they ignore
- which fields they mentally rename
- where they duplicate work
- whether support routing, milestones, and action items feel useful or redundant

After the pilot, use `docs/portfolio-post-pilot-review-framework.md` to decide what to change and what to leave alone.
