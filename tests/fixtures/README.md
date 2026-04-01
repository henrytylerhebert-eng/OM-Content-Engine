# Synthetic Fixture Exports

These fixture files are safe synthetic exports for local development and tests.

- They mirror the rough shape of the OM pilot Airtable or CSV exports.
- They do not contain live member, mentor, or staff data.
- They intentionally include messy cases so the normalization layer stays conservative.

Current sample exports:

- `active_members.csv`
- `mentors.csv`
- `cohorts.csv`

The rows cover:

- startup organization
- partner organization
- grouped personnel field
- sparse record
- internal record
- multi-cohort record
- explicit cohort export row
- unresolved cohort linkage row
- rich mentor record
- sparse mentor record
