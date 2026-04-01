# Segmentation Rules

## Purpose

This repo uses explicit rule-based segmentation.

The goal is to make reporting, outreach, and future automation easier without hiding the logic in scoring or opaque filters.

These segments are first-pass only. If the source data is incomplete, the record may be left out of a segment rather than guessed into one.

## Segment Output Shape

The segment layer returns a bundle where each segment contains:

- `name`
- `label`
- `record_type`
- `rule`
- `description`
- `count`
- `records`

That shape is intended to be useful for:

- reporting scripts
- export views
- future Codex-driven content tasks
- future Canva or Loomly preparation

## Rules

### Active startup members

- include organizations where `org_type == "startup"`
- include only when `active_flag` is truthy

### Partner organizations

- include organizations where `org_type == "partner"`
- also include organizations where `membership_tier == "Partner"`
- this lets partner-tier universities, government groups, or nonprofits stay in the partner segment without flattening their sector classification to `partner`

### Active mentors

- include people where `person_type == "mentor"`
- include only when both `Person.active_flag` and `MentorProfile.mentor_active_flag` are truthy
- require a matching mentor profile

### Local mentors

- include active mentors where `MentorProfile.mentor_location_type == "local"`

### Non-local mentors

- include active mentors where `MentorProfile.mentor_location_type` is `remote` or `hybrid`
- do not guess that a missing location means non-local

### Current cohort founders

- include people linked to organizations through founder affiliations
- include only when the linked organization has participation with `participation_status == "active"`
- if the linked cohort record is present, require `Cohort.active_flag` to be truthy
- unresolved joins are excluded rather than guessed

### Alumni founders

- include people linked to organizations through founder affiliations
- include when linked participation has `participation_status == "alumni"`
- also include when linked cohort exists and `Cohort.active_flag` is not truthy

### Internal records

- include organizations where `org_type == "internal"`
- include people where `person_type == "staff"`
- output is mixed because it can contain both organization and person records

### Content-ready organizations

- include only active organizations
- require `content_eligible` to be truthy
- require `spotlight_priority > 0`

### Content-ready people

- include only active people
- require `content_ready` to be truthy

### Review-needed records

- include rows already routed into the review queue
- do not hide review rows just because the underlying normalized record is still usable elsewhere

## Practical Notes

- This is not a scoring system.
- The rules are intentionally narrow.
- When joins are unresolved, the segment layer leaves records out instead of inventing connections.
- Segments should be updated only when the rule change can be explained in one sentence.
