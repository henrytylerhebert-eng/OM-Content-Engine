# System Map

## What The System Takes In

Primary source files:

- `Active Members`: organization-first source
- `Mentors`: person-first source
- `Cohorts`: participation-first source
- `data/reviewed_truth/overrides.json`: optional human-approved corrections applied after normalization

The raw CSVs land in `data/raw/`. The reviewed-truth file is local repo state, not source data.

## Pipeline In One Pass

1. Land Airtable CSV exports in `data/raw/`.
2. Run the raw pipeline.
3. Normalize raw rows into explicit entities.
4. Emit review flags instead of guessing through ambiguous cases.
5. Apply reviewed truth from `data/reviewed_truth/overrides.json` if it exists.
6. Build content intelligence and reporting outputs from the reviewed layer.

## Main Entities

- `Organization`: startup, partner, internal, university, government, and similar org records
- `Person`: founders, operators, mentors, and other named people
- `Affiliation`: joins people to organizations with role context
- `Program`: high-level program identity such as `Builder`
- `Cohort`: specific cohort instance such as `Spring 2026`
- `Participation`: a person or organization linked to a cohort with a status
- `MentorProfile`: mentor-specific availability and expertise fields layered on a person
- `ContentIntelligence`: derived content and readiness state for people and organizations

## Reviewed Truth

The system keeps three truth layers separate:

- source truth: raw Airtable exports
- derived truth: normalized and enriched outputs from repo rules
- reviewed truth: local human-approved overrides applied after normalization

Reviewed truth is where OM can:

- correct `org_type`
- suppress placeholder or grouped records
- confirm or deny content use
- confirm spotlight suitability
- mark `externally_publishable`
- resolve cohort identity or participation status when a human has better context

## Readiness Ladder

- `internally_usable`: safe for planning, segmentation, and internal reporting
- `content_ready`: enough profile substance for lightweight drafting or mention
- `spotlight_ready`: strong candidate for a real feature or highlighted story
- `externally_publishable`: public-ready only through reviewed truth

Heuristics may set the first three. Only reviewed truth may set `externally_publishable`.

## Main Outputs

The raw pipeline writes these into `data/processed/<run_name>/`:

- `normalized_bundle.json`: normalized entities before reviewed truth changes
- `reviewed_truth.json`: reviewed copies plus applied override log
- `review_flags.json`: unresolved ambiguity and cleanup queue
- `content_intelligence.json`: readiness and content-use signals
- `reporting_snapshot.json`: machine-friendly reporting sections
- `ecosystem_summary.json`: compact run summary
- `ecosystem_report.md`: readable markdown summary

## Golden Paths

These examples use the current fixture rows in `tests/fixtures/`.

### 1. Clean Startup Member With Founder And Cohort

Raw source shape:

- `Active Members`
- `Record ID=rec_member_001`
- `Company Name=Acme AI`
- `Founder Name=Jane Founder`
- `Founder Email=jane@acme.ai`
- `Primary Contact Name=Alex Ops`
- `Primary Contact Email=alex@acme.ai`
- `Builder Cohort=Builder Spring 2026`
- `Program Name=Builder`

Normalized records created:

- `Organization`: `Acme AI`, `org_type=startup`
- `Person`: `Jane Founder`, `person_type=founder`, `person_source_path=structured_member_fields`
- `Person`: `Alex Ops`, `person_type=operator`, `person_source_path=structured_member_fields`
- `Affiliation`: founder affiliation for Jane
- `Affiliation`: primary contact affiliation for Alex
- `Program`: `Builder`
- `Cohort`: `Builder Spring 2026`
- `Participation`: `Acme AI -> Builder Spring 2026`, `status=active`

Review flags:

- none

Content intelligence outcome:

- organization: `internally_usable`, `content_ready`, `spotlight_ready`
- Jane Founder: `internally_usable`, `content_ready`, `spotlight_ready`
- Alex Ops: `internally_usable`, `content_ready`, `spotlight_ready`
- `externally_publishable` remains `false` until reviewed truth says otherwise

Reporting significance:

- shows up in active startups
- shows up in organizations by cohort
- shows up in content-ready and spotlight-ready people and organizations
- strengthens founder-story and recruitment reporting

### 2. Partner Organization With One Structured Contact

Raw source shape:

- `Active Members`
- `Record ID=rec_member_002`
- `Company Name=Gulf Coast Manufacturing Network`
- `Member Type=Partner`
- `Primary Contact Name=Riley Partner`
- `Primary Contact Email=riley@gcmn.org`

Normalized records created:

- `Organization`: `Gulf Coast Manufacturing Network`, `org_type=partner`
- `Person`: `Riley Partner`, `person_type=operator`, `person_source_path=structured_member_fields`
- `Affiliation`: primary contact affiliation

Review flags:

- `review_content_profile_sparse`
- `review_missing_content_assets`

Content intelligence outcome:

- organization: `internally_usable`, `content_ready`, `spotlight_ready`
- Riley Partner: `internally_usable` only
- no external publication approval by default

Reporting significance:

- shows up in partner counts
- helps ecosystem-proof and partner reporting
- person record stays visible but clearly not ready for polished feature work

### 3. Startup With Grouped Personnel Text

Raw source shape:

- `Active Members`
- `Record ID=rec_member_003`
- `Company Name=Pelican Robotics`
- `Founder Name=Jamie Wells`
- `Primary Contact Name=Ava Chen`
- `Personnel=Jamie Wells - CEO; Ava Chen - COO; Builder Intern Team`
- `Builder Cohort=Builder Spring 2026`

Normalized records created:

- `Organization`: `Pelican Robotics`, `org_type=startup`
- `Person`: `Jamie Wells`, structured founder path
- `Person`: `Ava Chen`, structured primary contact path
- `Affiliation`: founder and primary-contact links
- `Participation`: `Pelican Robotics -> Builder Spring 2026`, `status=active`

Review flags:

- `review_personnel_parse`
- `review_grouped_record_detected`
- person-level content sparsity flags

Content intelligence outcome:

- organization: `internally_usable`, `content_ready`, `spotlight_ready`
- Jamie Wells and Ava Chen: `internally_usable` but not `content_ready`

Reporting significance:

- still counts cleanly for startup and cohort reporting
- stays visible as a people record source, but the grouped `Personnel` cell remains in the review queue instead of creating extra risky people

### 4. Internal Record That Should Stay Segmented

Raw source shape:

- `Active Members`
- `Record ID=rec_member_005`
- `Company Name=Opportunity Machine Internal Ops`
- `Member Type=Internal`
- `Primary Contact Name=Taylor Staff`

Normalized records created:

- `Organization`: `Opportunity Machine Internal Ops`, `org_type=internal`
- `Person`: `Taylor Staff`, `person_type=operator`, `person_source_path=structured_member_fields`
- `Affiliation`: primary contact affiliation

Review flags:

- `review_internal_record_detected`
- grouped-name/content sparsity flags as applicable

Content intelligence outcome:

- organization: below `internally_usable` for content work
- person: `internally_usable` but not `content_ready`
- no external publication approval

Reporting significance:

- internal record stays in the system for operational traceability
- should be filtered or segmented separately from external ecosystem reporting

### 5. Clean Mentor Record

Raw source shape:

- `Mentors`
- `Record ID=rec_mentor_001`
- `Full Name=Morgan Guide`
- `Email=morgan@example.com`
- `Expertise=AI, Go-to-market`
- `Mentor Location Type=Local`

Normalized records created:

- `Person`: `Morgan Guide`, `person_type=mentor`, `person_source_path=mentor_structured`
- `MentorProfile`: `mentor_location_type=local`, `mentor_program_type=Builder`

Review flags:

- `review_missing_content_assets` for missing org-context assets only

Content intelligence outcome:

- `internally_usable`, `content_ready`, `spotlight_ready`
- strong `mentor_story_candidate`
- not externally publishable unless reviewed truth approves it

Reporting significance:

- shows up in active mentors
- shows up in local mentor reporting
- shows up in content-ready and spotlight-ready people
- useful for mentor features and event speaker shortlists

## What This Map Helps With

This doc is the fast orientation layer:

- what comes in
- what gets created
- what stays in review
- what the readiness ladder means
- which outputs to inspect after a run
