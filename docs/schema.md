# Schema

## Notes

- This is a first-pass schema for a read-optimized intelligence layer.
- Source data is messy, so some fields stay optional by design.
- Tag fields are plain strings in Phase 1. That keeps the model readable and easy to change while the taxonomy is still settling.
- Operational source identifiers are preserved wherever possible.

## Organizations

Represents a company, partner, university, investor, service organization, or internal entity.

| Field | Type | Notes |
| --- | --- | --- |
| id | int | Local primary key |
| name | str | Required normalized display name |
| org_type | str | `startup`, `partner`, `internal`, `university`, `investor`, `mentor_org`, `service_provider`, `government`, `nonprofit`, `other`, `unknown` |
| membership_status | str | Example: `active`, `alumni`, `inactive` |
| membership_tier | str | Optional operational tier or level |
| website | str | Optional |
| description | str | Short normalized description |
| industry | str | Optional |
| stage | str | Optional startup stage |
| headquarters_location | str | Optional location string |
| active_flag | bool | Normalized active flag |
| source_record_id | str | Original source record id when available |
| source_system | str | Example: `airtable_export`, `csv_sync` |
| content_eligible | bool | Whether the organization is reasonable to consider for stories |
| spotlight_priority | int | Simple first-pass priority score |

## People

Represents founders, mentors, staff, partner contacts, or other known individuals.

| Field | Type | Notes |
| --- | --- | --- |
| id | int | Local primary key |
| full_name | str | Required normalized display name |
| email | str | Optional but important for matching |
| linkedin | str | Optional |
| bio | str | Optional |
| headshot_url | str | Optional |
| location | str | Optional |
| timezone | str | Optional |
| person_type | str | `founder`, `mentor`, `staff`, `operator`, `partner_contact`, `other` |
| expertise_tags | str | Comma-separated tags in Phase 1 |
| public_facing_ready | bool | Enough profile material exists for external use |
| speaker_ready | bool | Reasonable candidate for events or panels |
| content_ready | bool | Reasonable candidate for storytelling |
| active_flag | bool | Normalized active flag |
| person_resolution_basis | str | `structured_field` or `semi_structured_member_side` in the current implementation |
| source_record_id | str | Original source record id when available |
| source_system | str | Example: `airtable_export`, `csv_sync` |

## Affiliations

Join table between people and organizations.

| Field | Type | Notes |
| --- | --- | --- |
| id | int | Local primary key |
| person_id | int | Nullable until persistence stage resolves foreign keys |
| organization_id | int | Nullable until persistence stage resolves foreign keys |
| role_title | str | Example: `Founder`, `CEO`, `Primary Contact` |
| role_category | str | `founder`, `executive`, `staff`, `mentor`, `sponsor`, `advisor`, `other` |
| founder_flag | bool | Startup founder indicator |
| primary_contact_flag | bool | Useful for outreach |
| spokesperson_flag | bool | Candidate public-facing representative |
| active_flag | bool | Normalized active flag |
| start_date | date | Optional |
| end_date | date | Optional |
| source_record_id | str | Source traceability |
| source_system | str | Source traceability |

## Programs

Represents an OM program, not a specific cohort run.

| Field | Type | Notes |
| --- | --- | --- |
| id | int | Local primary key |
| program_name | str | Required |
| program_type | str | Example: `builder`, `accelerator`, `mentor`, `community` |
| active_flag | bool | Normalized active flag |
| source_record_id | str | Optional source traceability |
| source_system | str | Optional source traceability |

## Cohorts

Represents a dated cohort instance within a program.

| Field | Type | Notes |
| --- | --- | --- |
| id | int | Local primary key |
| cohort_name | str | Required |
| program_id | int | Nullable until persistence stage resolves foreign keys |
| start_date | date | Optional |
| end_date | date | Optional |
| active_flag | bool | Derived from dates or source status |
| source_record_id | str | Optional source traceability |
| source_system | str | Optional source traceability |

## Participation

Represents a person or organization participating in a cohort.

| Field | Type | Notes |
| --- | --- | --- |
| id | int | Local primary key |
| person_id | int | Nullable |
| organization_id | int | Nullable |
| cohort_id | int | Nullable until persistence stage resolves foreign keys |
| participation_status | str | `active`, `alumni`, `pending`, `withdrawn`, `unknown` |
| notes | str | Optional notes from source |
| source_record_id | str | Source traceability |
| source_system | str | Source traceability |

## Mentor Profiles

Mentor-specific attributes layered on top of people.

| Field | Type | Notes |
| --- | --- | --- |
| id | int | Local primary key |
| person_id | int | Nullable until persistence stage resolves foreign keys |
| mentor_program_type | str | Example: `builder`, `office_hours`, `general` |
| mentor_location_type | str | Example: `local`, `remote`, `hybrid` |
| expertise_summary | str | Short human-readable summary |
| share_email_permission | bool | Whether contact sharing is allowed |
| booking_link | str | Optional scheduling link |
| mentor_active_flag | bool | Normalized active flag |
| source_record_id | str | Source traceability |
| source_system | str | Source traceability |

## Interactions

Represents connections, meeting requests, notes, or engagement events.

| Field | Type | Notes |
| --- | --- | --- |
| id | int | Local primary key |
| person_id | int | Nullable |
| organization_id | int | Nullable |
| interaction_type | str | Example: `connection`, `meeting_request`, `feedback` |
| date | date | Interaction date if known |
| owner | str | Internal owner if present |
| notes | str | Optional |
| follow_up_date | date | Optional |
| source_record_id | str | Source traceability |
| source_system | str | Source traceability |

## Content Intelligence

Derived storytelling and communications fields.

| Field | Type | Notes |
| --- | --- | --- |
| id | int | Local primary key |
| linked_person_id | int | Nullable |
| linked_organization_id | int | Nullable |
| audience_tags | str | Comma-separated in Phase 1 |
| industry_tags | str | Comma-separated in Phase 1 |
| proof_tags | str | Comma-separated in Phase 1 |
| content_eligible | bool | Whether the profile should be considered for content use at all |
| internally_usable | bool | Trusted enough for internal planning and candidate review |
| content_ready | bool | Broadly usable for internal content planning or lightweight drafting |
| narrative_theme | str | Optional |
| message_pillar | str | Optional |
| story_type | str | Optional |
| spotlight_ready | bool | Derived output flag |
| externally_publishable | bool | Reviewed-truth-only flag for records approved for public use |
| spokesperson_candidate | bool | Whether the linked person or organization has a reasonable public-facing representative |
| founder_story_candidate | bool | Founder profile looks usable for a spotlight or story package |
| mentor_story_candidate | bool | Mentor profile looks usable for a feature or event-related story |
| ecosystem_proof_candidate | bool | Record supports proof-of-ecosystem content |
| missing_content_assets | str | Comma-separated missing assets such as bio, headshot, website, or description |
| profile_completeness_score | int | Simple rule-based completeness score from 0 to 100 |
| last_featured_date | date | Optional |
| priority_score | int | Simple first-pass score |
| source_record_id | str | Source traceability |
| source_system | str | Source traceability |

## Matching Notes

- `source_record_id` is not a substitute for a stable internal key. It is there for traceability.
- Some joins will stay unresolved during early transforms if the source row does not include clean foreign keys.
- That is acceptable in Phase 1 as long as the ambiguity is visible and recoverable.
