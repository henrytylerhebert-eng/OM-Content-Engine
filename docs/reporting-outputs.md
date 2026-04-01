# Reporting Outputs

## Purpose

These reports are meant for internal strategy, reporting, and communications planning.

They are intentionally lightweight:

- JSON input
- markdown output for readable summaries
- CSV output for one section at a time
- plain Python functions for script use

Current section outputs include:

- active organizations by type
- active people by type
- active people by source path
- active mentor summary
- readiness trust summary
- structured people
- semi-structured auto-created people
- mentor-derived people
- review-needed people candidates
- organizations by cohort
- organizations by membership tier
- internally usable organizations
- internally usable people
- organizations with content-ready profiles
- people with content-ready profiles
- spotlight-ready organizations
- spotlight-ready people
- externally publishable records
- missing content asset counts
- review burden by flag
- records requiring review

## Expected Input Shape

The command-line report runner expects a JSON file with keys like:

```json
{
  "organizations": [],
  "people": [],
  "mentor_profiles": [],
  "affiliations": [],
  "participations": [],
  "cohorts": [],
  "review_rows": []
}
```

## Example Markdown Output

```md
# Ecosystem Report

## Active Organizations By Type

| org_type | count |
| --- | --- |
| startup | 8 |
| partner | 3 |

## Active Mentor Summary

| metric | count |
| --- | --- |
| active_mentors | 12 |
| local_mentors | 7 |
| non_local_mentors | 5 |

## Active People By Source Path

| person_source_path | count | reviewed_truth_backed_count | source_derived_count |
| --- | --- | --- | --- |
| mentor_structured | 12 | 0 | 12 |
| structured_member_fields | 8 | 2 | 6 |
| semi_structured_member_side | 3 | 1 | 2 |

## Readiness Trust Summary

| record_type | trust_basis | row_count | internally_usable_count | content_ready_count | spotlight_ready_count | externally_publishable_count |
| --- | --- | --- | --- | --- | --- | --- |
| organization | reviewed_truth_backed | 2 | 2 | 2 | 1 | 0 |
| organization | heuristic_only | 7 | 5 | 3 | 1 | 0 |
| person | human_approved | 1 | 1 | 1 | 1 | 1 |
| person | reviewed_truth_backed | 2 | 2 | 2 | 1 | 0 |
| person | heuristic_only | 9 | 8 | 4 | 1 | 0 |

## Semi-Structured Auto-Created People

| full_name | person_type | person_resolution_basis | person_source_path | review_state | reviewed_override_count | active_flag | email | source_record_id | source_system |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Dana Planner | operator | semi_structured_member_side | semi_structured_member_side | source_derived | 0 | True | dana@example.com | rec_person_013 | airtable_export |

## Internally Usable People

| full_name | person_type | person_resolution_basis | person_source_path | trust_basis | reviewed_truth_applied | reviewed_override_count | internally_usable | content_ready | spotlight_ready | externally_publishable | profile_completeness_score | story_type | message_pillar | missing_content_assets |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Dana Planner | operator | semi_structured_member_side | semi_structured_member_side | heuristic_only | False | 0 | True | False | False | False | 0 | profile | newsletter_profile | bio, headshot, linkedin, expertise, location, organization_website, organization_description, cohort_history |

## Content-Ready Organizations

| organization_name | org_type | internally_usable | content_ready | spotlight_ready | externally_publishable | profile_completeness_score | story_type | message_pillar | missing_content_assets |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Acme AI | startup | True | True | True | False | 90 | founder_spotlight | program_recruitment | location, spokesperson |

## Spotlight-Ready People

| full_name | person_type | person_resolution_basis | person_source_path | trust_basis | reviewed_truth_applied | reviewed_override_count | internally_usable | content_ready | spotlight_ready | externally_publishable | profile_completeness_score | story_type | message_pillar | missing_content_assets |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Priya Founder | founder | structured_field | structured_member_fields | reviewed_truth_backed | True | 1 | True | True | True | False | 65 | founder_spotlight | program_recruitment | linkedin, expertise, location |

## Externally Publishable Records

| record_type | label | entity_type | trust_basis | reviewed_override_count | content_ready | spotlight_ready | externally_publishable | profile_completeness_score | story_type | message_pillar | missing_content_assets |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| person | Priya Founder | founder | human_approved | 1 | True | True | True | 65 | founder_spotlight | program_recruitment | linkedin, expertise, location |

## Missing Content Asset Counts

| record_type | trust_basis | readiness_level | asset_name | count |
| --- | --- | --- | --- | --- |
| person | heuristic_only | content_ready | headshot | 9 |
| person | reviewed_truth_backed | spotlight_ready | linkedin | 2 |
| organization | heuristic_only | content_ready | spokesperson | 4 |

## Review Burden By Flag

| flag_code | flag_type | severity | review_scope | count | source_tables |
| --- | --- | --- | --- | --- | --- |
| review_no_person_found | missing_name | medium | people_candidate | 96 | Active Members |
| review_missing_content_assets | sparse_record | low | general | 149 | Mentors, Active Members |

## Records Requiring Review

| source_table | source_record_id | flag_code | flag_type | severity | record_label | source_field | note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Active Members | rec_104 | review_missing_org_type | missing_org_type | medium | Community Network | Member Type |  |
| Mentors | rec_225 | review_content_profile_sparse | sparse_record | medium | Sparse Mentor | internally_usable | bio, headshot, linkedin |

## Review-Needed People Candidates

| source_table | source_record_id | flag_code | severity | record_label | source_field | note |
| --- | --- | --- | --- | --- | --- | --- |
| Active Members | rec_301 | review_member_side_person_generic_email | medium | Signal Works | Email | Generic inbox only; keep review-first |
```

## Example Python Usage

```python
from src.reporting.ecosystem_reports import build_reporting_snapshot, render_markdown_report

snapshot = build_reporting_snapshot(
    organizations=organizations,
    people_payloads=people,
    mentor_profiles=mentor_profiles,
    affiliations=affiliations,
    participations=participations,
    cohorts=cohorts,
    review_rows=review_rows,
)

print(render_markdown_report(snapshot))
```

## Example CSV Usage

```bash
python3 -m src.reporting.ecosystem_reports \
  --input data/processed/reporting_input.json \
  --format csv \
  --section externally_publishable_records
```
