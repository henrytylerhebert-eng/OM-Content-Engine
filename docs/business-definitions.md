# Business Definitions

This doc locks the working meaning of core internal terms used across normalization, reviewed truth, content intelligence, and reporting.

## Truth Layers

### Source truth

The raw operational truth coming from Airtable exports and synced CSVs.

- lives in `data/raw/`
- should not be rewritten by this repo
- remains the reference point for staff workflow

### Derived truth

The repo's normalized and enriched output created from source truth plus documented rules.

- lives in `data/processed/`
- includes normalization, classification, readiness, and reporting output
- should stay traceable back to source records

### Reviewed truth

Human-approved corrections applied after normalization.

- lives in `data/reviewed_truth/overrides.json`
- can patch, confirm, or suppress derived records
- is the only place that can approve `externally_publishable`

## Readiness Ladder

### Internally usable

Safe for internal planning, reporting, segmentation, and candidate review.

- good enough for staff decision-making
- not a claim that the record is ready for outward-facing use

### Content ready

Strong enough for lightweight drafting or a short mention.

- enough profile substance to avoid guesswork
- still not public approval

### Spotlight ready

Strong enough for a real feature candidate or highlighted story.

- higher bar than `content_ready`
- should imply a stronger story angle and stronger profile completeness

### Externally publishable

Approved for public-facing use.

- never set by heuristics alone
- can only be set through reviewed truth

## People Provenance

### Structured person

A person created from clear named source fields such as:

- `Founder Name`
- `Primary Contact Name`
- clean mentor fields like `Full Name`

This is the most trusted person-creation path.

### Semi-structured auto-created person

A person created from the narrow member-side dual-signal rule.

Required evidence:

- one clear full-name candidate
- one unique non-generic email
- one resolved org or cohort context

This is allowed but intentionally narrow.

### Mentor-derived person

A person created from the `Mentors` export.

- treated as a structured person path
- reported separately because it comes from a different source shape and usually carries mentor-specific fields

### Review-needed candidate

A possible person or organization signal the system did not trust enough to create or finalize automatically.

Examples:

- grouped `Personnel` text
- first-name-only values
- generic emails
- ambiguous cohort linkage
- sparse placeholder-like records

These belong in the review queue, not in silent automation.

## Organization Types

These are working reporting and segmentation labels, not a promise of perfect taxonomy.

- `startup`: a member company or startup venture
- `partner`: a partner organization or network supporting the ecosystem
- `internal`: an Opportunity Machine internal record
- `university`: a college, university, or academic unit
- `government`: a public-sector or government body
- `investor`: an investment organization
- `mentor_org`: an organization that primarily represents mentor supply or a mentor network
- `service_provider`: a professional-services or support organization
- `nonprofit`: a nonprofit organization
- `other`: a real organization that does not fit the working buckets cleanly
- `unknown`: not enough evidence to classify safely

`unknown` means the system is holding uncertainty on purpose.
`other` means the system believes the record is real but the current taxonomy is not a clean fit.

## Participation Status

These are the normalized participation states used in reporting.

- `active`: currently in the cohort or program context
- `alumni`: completed or past participant
- `pending`: expected or not yet fully active
- `withdrawn`: dropped or left before completion
- `unknown`: source text did not support a safer status

Status should stay separate from cohort identity.
Mixed source labels such as `Fall 2025,Dropout` should be split when that can be done safely. If not, they should go to review.

## Working Interpretation Rule

When there is tension between completeness and trust, trust wins.

In practice that means:

- review flags are better than risky guesses
- reviewed truth outranks heuristics
- public-facing approval requires explicit human confirmation
