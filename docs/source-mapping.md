# Source Mapping

## Purpose

This is the working field map for the OM pilot exports.

Current priority sources:

- `Active Members`
- `Mentors`
- `Cohorts`

This document is written against the current repo state:

- synthetic pilot fixtures in `tests/fixtures/`
- review flag definitions in `src/transform/review_flags.py`
- first-pass transforms in `src/transform/`

It is meant to help future maintainers answer two questions quickly:

1. what a raw field is supposed to create
2. when the system should stop and send the row to review

## Operating Position

- `Active Members` is organization-first.
- `Mentors` is person-first.
- `Cohorts` is participation-first.
- One raw row can create multiple normalized records.
- Source provenance must be preserved on every normalized record and every review row.
- Content intelligence is derived later from normalized fields. It is not the direct storage target for raw source fields.
- `Interaction` is not created by default from `Active Members` or `Mentors`. It should only be created when a row contains a clear dated engagement trace that can stand on its own.

## Handling Labels

- `direct copy`: copy with light cleanup only
- `derived transform`: normalize, classify, or convert the source value
- `split into multiple records`: one field can create more than one normalized record
- `ignored`: keep in raw provenance only for now
- `review-needed`: preserve raw value and emit review flags instead of trusting automation

## Provenance Rules

- Keep the raw landed row unchanged in the raw source layer.
- Preserve `source_table`, `source_record_id`, import timestamp, file path, and row hash in the raw layer.
- Every normalized record created from a raw row must carry:
  - `source_record_id`
  - `source_system`
- If one raw row creates several normalized records, they all share the same `source_record_id`.
- Review queue rows must also carry `source_table` and `source_record_id`.
- Ignored fields still stay in raw provenance so later transforms can revisit them.

## Target Entity Coverage

| Source file | Primary targets | Secondary targets | Not default from this file |
| --- | --- | --- | --- |
| `Active Members` | `Organization`, `Person`, `Affiliation` | `Program`, `Cohort`, `Participation`, derived `ContentIntelligence` seeds | `Interaction` unless the row includes a clear dated engagement trace |
| `Cohorts` | `Program`, `Cohort`, `Participation` | possible `Organization` or `Person` linkage when identity is already known in normalized records | `Interaction` by default |
| `Mentors` | `Person`, `MentorProfile` | derived `ContentIntelligence` seeds, possible later `Organization` and `Affiliation` | `Interaction` unless the row includes a clear dated engagement trace |

## Review Flag Alignment

These are the main review flags that matter for the two pilot sources today.

| Review flag code | Typical trigger in these sources |
| --- | --- |
| `review_missing_organization_name` | `Active Members` row has people or status data but no usable org name |
| `review_org_type` | org type is missing or too weak to classify confidently |
| `review_sparse_record` | row has too little usable detail to trust downstream |
| `review_internal_record_detected` | row appears to be an internal OM record |
| `review_personnel_parse` | `Personnel` field contains free text that should not be trusted as clean person records |
| `review_member_side_person_multiple_candidates` | one `Personnel` cell appears to contain more than one person candidate |
| `review_member_side_person_name_incomplete` | `Personnel` contains only a first name or otherwise incomplete name text |
| `review_member_side_person_generic_email` | the only available email is generic or role-based |
| `review_member_side_person_context_ambiguous` | the row does not resolve to one safe org or cohort context for semi-structured person creation |
| `review_grouped_record_detected` | grouped team text appears in `Personnel` or a person-like name field |
| `review_placeholder_record` | placeholder text such as `TBD` or `Unknown` appears in a key name field |
| `review_missing_cohort_name` | participation context exists but no usable cohort value is available |
| `review_multi_value_cohort_parse` | one cohort cell contains more than one cohort token |
| `review_participation_link_unresolved` | explicit cohort row could not be matched to an existing organization or person safely |
| `review_person_missing_email` | a mentor or contact person is created without an email |
| `review_mentor_location_type` | mentor location text exists but does not normalize cleanly to `local`, `remote`, or `hybrid` |
| `review_employer_organization` | mentor employer text is not clearly a real organization |

## Active Members

### File Role

Treat `Active Members` as an organization-oriented source.

Do not assume:

- one row equals one founder
- every row should create a person
- every row should create a cohort record

The minimum useful outcome for this file is often just a clean `Organization` record plus review flags.

### Field Inventory

| Source field | Normalized target | Handling | Operational note |
| --- | --- | --- | --- |
| `Record ID` | all created records -> `source_record_id` | direct copy | Shared by every normalized record created from the row |
| `Company Name` | `Organization.name` | direct copy | Main organization name field |
| `Organization Name` | `Organization.name` | direct copy | Alias for org name |
| `Member Company` / `Startup Name` | `Organization.name` | direct copy | Alias for org name |
| `Membership Status` | `Organization.membership_status`, `Organization.active_flag` | derived transform | Normalize to lowercase underscore form; active flag falls out of status |
| `Status` / `Active Status` | `Organization.membership_status`, `Organization.active_flag` | derived transform | Used when `Membership Status` is absent |
| `Member Type` | `Organization.org_type` | derived transform | Primary field for org classification |
| `Organization Type` / `Org Type` / `Category` / `Company Type` | `Organization.org_type` | derived transform | Same classification path as `Member Type` |
| `Confirmed Membership Level` | `Organization.membership_tier` | direct copy | Now supported as an alias in the current transform |
| `Membership Tier` / `Tier` | `Organization.membership_tier` | direct copy | Keep source wording in Phase 1 |
| `Accessible Space` | none | ignored | Keep in raw provenance until OM decides whether this belongs in facilities, benefits, or segmentation |
| `Application Date` | none | ignored | Keep raw for now; no first-pass application timeline model exists yet |
| `Website` / `Company Website` | `Organization.website` | direct copy | Keep raw URL |
| `Description` / `Company Description` | `Organization.description` | direct copy | No rewriting in transform |
| `Industry` / `Sector` | `Organization.industry` | direct copy | Keep source wording until a stable taxonomy exists |
| `Stage` / `Company Stage` | `Organization.stage` | direct copy | Keep source wording |
| `Headquarters` / `Location` / `City` | `Organization.headquarters_location` | direct copy | Used as org location, not person location, in organization normalization |
| `Founder Name` | `Person.full_name`, `Affiliation.role_title`, `Affiliation.founder_flag`, `Person.person_type` | split into multiple records | Creates a founder person and founder affiliation when an org exists |
| `Founder Email` | `Person.email` | direct copy | Used for matching and outreach |
| `Primary Contact Name` | `Person.full_name`, `Affiliation.role_title`, `Affiliation.primary_contact_flag`, `Person.person_type` | split into multiple records | Creates an operator or primary contact person |
| `Primary Contact Email` | `Person.email` | direct copy | Used for matching and outreach |
| `Primary Email (from Link to Application)` / `Your Email (from Participants)` / `Email` | possible `Person.email` for conservative member-side resolution | derived transform | Used only when one clear full-name candidate exists in `Personnel` and the row has one unique non-generic email |
| `Personnel` | possible `Person.full_name` and `Affiliation.role_title` in one narrow case; otherwise review queue only | review-needed | Current transform only creates one extra member-side person when the field contains one clear full name, one unique non-generic email exists elsewhere in the same row, and the row has one resolved org or cohort context |
| `Program Name` | `Program.program_name` | direct copy | Only when participation context is clearly present |
| `Cohort` / `Cohort Name` / `Builder Cohort` | `Cohort.cohort_name`, `Participation.cohort_id`, possible `Participation.participation_status` | split into multiple records or review-needed | One clean cohort label creates one cohort path; one known trailing status token such as `Dropout` can be separated safely; anything broader goes to review |
| `Participation Status` | `Participation.participation_status` | derived transform | Normalize to `active`, `alumni`, `pending`, `withdrawn`, or `unknown` |
| `Start Date` | `Cohort.start_date` | direct copy | Only when cohort context is clear |
| `End Date` | `Cohort.end_date` | direct copy | Only when cohort context is clear |
| `Notes` | `Participation.notes` | direct copy | Only when the row is clearly about cohort participation; otherwise keep raw |
| `Feedback` | `Participation.notes` or none | review-needed | Use only if it is clearly participation context; richer feedback belongs in a dedicated feedback source |
| `Meeting Requests` | possible later `Interaction` or none | review-needed | If this is only a count or summary, keep raw; use `Interaction` only for clear dated traces |
| `LinkedIn` / `Linkedin` | `Person.linkedin` | direct copy | Only when clearly tied to a named person in the row |
| `Bio` | `Person.bio` | direct copy | Only when clearly tied to a named person in the row |
| `Headshot URL` / `Headshot` | `Person.headshot_url` | direct copy | Only when clearly tied to a named person in the row |
| public-facing readiness fields | derived `ContentIntelligence` inputs later | derived transform | Stored on `Person` now; formal content intelligence is built in enrichment |
| unmapped extra columns | none | ignored | Preserve raw until there is a documented use |

### Active Members Entity Rules

#### Organization

- Create `Organization` when any supported org name field is present.
- `Organization` is the anchor record for this source.
- If the org name is missing, do not invent one.

#### Person

- Create people only from structured contact fields first:
  - `Founder Name`
  - `Primary Contact Name`
  - `Contact Name` when present in another export shape
- Allow one extra member-side person from `Personnel` only when all of these are true:
  - there is one clear full-name candidate
  - there is one unique non-generic email in the same row
  - the row resolves to one organization or one cohort context
- Store `Person.person_resolution_basis` so downstream outputs can tell:
  - `structured_field`
  - `semi_structured_member_side`
- Keep `Personnel` review-first for multi-person strings, grouped labels, first-name-only values, email-only rows, generic emails, or ambiguous row context.

#### Affiliation

- Create `Affiliation` only when both of these are true:
  - there is at least one normalized person
  - there is a normalized organization
- Use row-level role hints from the structured person fields.

#### Program, Cohort, Participation

- Only create these when the row clearly contains participation context.
- One clean cohort value can produce:
  - one `Program`
  - one `Cohort`
  - one `Participation`
- Multi-value cohort cells are review-first in the current implementation.
- If the same organization-cohort relationship is later present in the explicit `Cohorts` export, keep one participation record and prefer the explicit cohort provenance.

#### Interaction

- Do not create `Interaction` by default from `Active Members`.
- If the row contains only summary columns like `Meeting Requests` or `Feedback`, keep them raw unless they are clearly dated and attributable.
- Dedicated engagement exports such as `Connections`, `Meeting Requests`, or `Feedback` are still the cleaner source for `Interaction`.

#### ContentIntelligence

- Do not map raw `Active Members` fields directly into `ContentIntelligence`.
- Instead, use normalized fields such as:
  - `Organization.website`
  - `Organization.description`
  - `Person.bio`
  - `Person.headshot_url`
  - `Person.linkedin`
  - cohort history

### Active Members Transform Rules

#### How `org_type` is derived

Current organization typing is conservative and now reflects the real `Active Members` export more directly.

1. trust explicit values from `Member Type`, `Organization Type`, `Org Type`, `Category`, or `Company Type`
2. normalize common labels into:
   - `startup`
   - `partner`
   - `internal`
   - `university`
   - `investor`
   - `mentor_org`
   - `service_provider`
   - `government`
   - `nonprofit`
   - `other`
   - `unknown`
3. if explicit type is weak, use strong real-export signals in this order:
   - internal naming and OM domains
   - `.gov` and government naming patterns
   - `.edu` and university naming patterns
   - `.vc` domains and investor language that reads like an actual investment organization
   - nonprofit naming patterns
   - mentor-network naming patterns
   - strong professional-service naming patterns
   - `Confirmed Membership Level`
   - startup-member operational signals such as `Accessible Space`, `Cohort`, and `Application Date`
4. if still unclear, set `org_type="unknown"` and emit `review_org_type`

See `docs/org-classification-rules.md` for the full rule order and examples.

#### How `person_type` is derived

For `Active Members`, the current transform uses structured columns only:

- `Founder Name` -> `person_type="founder"`
- `Primary Contact Name` -> `person_type="operator"`
- generic fallback contact fields -> `person_type="other"`
- conservative semi-structured member-side path -> `person_type="operator"`

`Personnel` only creates a person in the narrow dual-signal path described above.

#### How conservative member-side people resolution works

The current implementation only applies this rule to `Active Members` rows with no structured person already found.

It may create one extra `Person` from `Personnel` only when:

- the `Personnel` value yields one clear full name
- the row yields exactly one unique email from supported member-side email fields
- that email is not generic or role-based
- the row resolves to one organization or one clean cohort context

The current code does not:

- split multi-person `Personnel`
- create a person from first-name-only text
- create a person from email-only context
- trust generic emails such as `info@...` or `team@...`
- guess across multiple organizations or mixed cohort context

Near-miss cases should emit targeted review flags such as:

- `review_member_side_person_multiple_candidates`
- `review_member_side_person_name_incomplete`
- `review_member_side_person_generic_email`
- `review_member_side_person_context_ambiguous`

#### How multi-value cohort fields are handled

Target shape over time:

- one cohort token should create one `Cohort`
- one participation should be attached to the organization or person that actually took part

Current implementation remains conservative:

- one clean cohort token -> normalize directly
- one clean cohort label plus one known status token such as `Dropout` -> separate into:
  - `Cohort.cohort_name`
  - `Participation.participation_status`
- semicolon-separated, line-break, or clear multi-label cells -> emit `review_multi_value_cohort_parse`
- invalid leftover tokens or mixed status across more than one cohort label -> emit `review_invalid_cohort_parse`

This is deliberate. The code favors a human review queue over accidental cohort history drift.

## Cohorts

### File Role

Treat `Cohorts` as the explicit cohort participation source.

This file is more trusted than free-text cohort cells embedded in `Active Members`.

The current pipeline uses it to:

- create or refine `Program`
- create or refine `Cohort`
- create `Participation`
- reconcile duplicate org-cohort relationships already inferred from `Active Members`

### Field Inventory

| Source field | Normalized target | Handling | Operational note |
| --- | --- | --- | --- |
| `Company Name` | used to resolve `Participation.organization_id` | derived transform | Exact normalized name match only in Phase 1 |
| `Link to Application` | fallback org lookup context | review-needed | Use only as a fallback label when `Company Name` is missing or inconsistent |
| `Cohort` | `Cohort.cohort_name`, `Participation.cohort_id`, possible `Participation.participation_status` | split into multiple records | Explicit cohort rows can safely split clean cohort labels and one known status token when it applies to one cohort label |
| `Program` / `Program Name` | `Program.program_name` | direct copy | Use when present |
| builder workflow fields such as `Miro Link`, `Customer Discovery Link`, `Customer Discovery Tracker`, `Welcome Email` | `Program.program_name="Builder"` when no explicit program exists | derived transform | This is a narrow OM-specific inference for the current cohort export shape |
| `Membership History` | `Participation.notes` | direct copy | Preserve row-level context without turning it into a separate entity |
| `Membership Status (from Application Link)` | none by default | ignored | This is not treated as cohort participation status |
| `Primary Email (from Link to Application)` | possible `Participation.person_id` link | derived transform | Link only when the email matches exactly one existing normalized person |
| `Participants` / `First Name (from Participants)` / `Your Email (from Participants)` | possible person-link context | review-needed | Keep conservative; do not auto-create extra people from participant lists yet |
| `Onboarding Complete Date` | none | ignored | Keep raw for now; not treated as cohort timing |
| `Review Batch (from Link to Application)` | none | ignored | Preserve only in raw provenance |
| extra delivery fields such as `Completion Certificate` or `Send Certificate` | none | ignored | Operational workflow context only in Phase 1 |

### Cohorts Entity Rules

#### Program

- Trust `Program` or `Program Name` if present.
- If those are blank and the row clearly uses the builder workflow fields, set `Program.program_name="Builder"`.
- Do not infer other program names from weak text.

#### Cohort

- Clean explicit cohort labels create `Cohort` records directly.
- The current explicit parser accepts:
  - season-year labels such as `Spring 2025`
  - month-year labels such as `September 2022`
  - `Individual Track`
- Explicit rows may split multiple clean cohort labels from one cell.
- Tokens like `Dropout` are treated as participation status, not extra cohort names, but only when that status can be tied safely to one cohort label.

#### Participation

- Link to `Organization` by exact normalized company name when possible.
- Link to `Person` only when the row email matches exactly one existing normalized person.
- If neither organization nor person can be matched safely, emit `review_participation_link_unresolved` and skip participation creation.
- If the same org-cohort relationship already exists from `Active Members`, keep one record and prefer the explicit `Cohorts` source as the primary participation origin.

### Cohorts Transform Rules

#### How multi-value cohort cells differ from `Active Members`

The same text pattern is treated differently depending on the source:

- `Active Members`: one cohort label plus one known status token can now be separated safely; broader multi-value text is still review-first
- `Cohorts`: multi-value cohort text can be split when every token is either a clean cohort label or one safe status token tied to a single label

This is deliberate. The explicit cohort export is the safer place to split history.

#### How participation status is derived

- `Dropout` becomes `withdrawn` when it appears as a separate known status token
- if one row contains more than one cohort label plus one status token, do not spread that status across all labels; send the row to review instead
- explicit `Participation Status` or `Status` wins if the row provides it
- otherwise, if the cohort timing is clearly in the past, use `alumni`
- otherwise use `active`

#### How timing is derived

- explicit `Start Date` and `End Date` win when present
- if they are missing, the transform can derive a rough time window from labels like `Spring 2025` or `September 2022`
- if the label does not carry clear timing, leave dates blank

#### How provenance is preserved

- every explicit cohort-derived record keeps `source_record_id` or row hash fallback
- participation records also keep a `source_provenance` trail in the normalized bundle
- reconciled participation records can show both:
  - inferred `Active Members` provenance
  - explicit `Cohorts` provenance

#### How comma-separated `Personnel` fields are handled

Current rule:

- preserve the raw field
- if the field contains multiple people or grouped text, emit `review_personnel_parse`
- if grouped team text is obvious, also emit `review_grouped_record_detected`
- if the field contains one clear full-name candidate and the row also has one unique non-generic email plus one resolved context, create one member-side `Person`
- otherwise keep the row review-first and emit the targeted near-miss flag that explains why the conservative rule did not fire

This protects against bad imports from values like:

- `Jamie Wells - CEO; Ava Chen - COO; Builder Intern Team`
- `Ops Team`
- `Summer Intern Group`

#### How grouped or placeholder records are flagged

- Placeholder organization names such as `TBD` or `Unknown` should emit `review_placeholder_record`.
- Grouped team text inside `Personnel` should emit `review_grouped_record_detected`.
- Internal OM records should emit `review_internal_record_detected`.

#### How sparse records are flagged

If the row has an organization name but very little supporting context, emit `review_sparse_record`.

This usually means:

- no useful website
- no description
- no people
- no location
- no cohort context

## Mentors

### File Role

Treat `Mentors` as a person-oriented source.

Do not assume:

- the row should create an employer organization
- the program label should create a standalone program record
- meeting links are interactions by themselves

The minimum useful outcome for this file is a clean `Person` plus `MentorProfile`.

### Field Inventory

| Source field | Normalized target | Handling | Operational note |
| --- | --- | --- | --- |
| `Record ID` | all created records -> `source_record_id` | direct copy | Shared by the normalized person and mentor profile |
| `Name` | `Person.full_name` | direct copy | Now supported as an alias in the current transform |
| `Full Name` / `Mentor Name` | `Person.full_name` | direct copy | Primary mentor naming fields |
| `Email` | `Person.email` | direct copy | Missing email still creates the person but emits review |
| `Area of Expertise` | `Person.expertise_tags`, `MentorProfile.expertise_summary` | derived transform | Now supported as an alias in the current transform |
| `Expertise` / `Expertise Tags` / `Skills` | `Person.expertise_tags`, `MentorProfile.expertise_summary` | derived transform | Normalize separators into a consistent comma-separated tag string |
| `Program` | `MentorProfile.mentor_program_type` | direct copy | Now supported as an alias in the current transform |
| `Mentor Program Type` / `Program Type` | `MentorProfile.mentor_program_type` | direct copy | Keep source wording for now |
| `Bio` | `Person.bio` | direct copy | Also feeds later content intelligence |
| `LinkedIn` / `Linkedin` | `Person.linkedin` | direct copy | Keep raw URL |
| `Headshot URL` / `Headshot` | `Person.headshot_url` | direct copy | Keep raw asset URL |
| `Mailing Address` | `Person.location` | direct copy | Now supported as a location alias in the current transform |
| `Location` / `City` / `State` | `Person.location` | direct copy | Keep plain location text |
| `Mentor Location` | `MentorProfile.mentor_location_type` | derived transform | Now supported as an alias in the current transform |
| `Mentor Location Type` / `Location Type` / `Availability` | `MentorProfile.mentor_location_type` | derived transform | Normalize to `local`, `remote`, or `hybrid` when the text is clean |
| `Time Zone` | `Person.timezone` | direct copy | Now supported as an alias in the current transform |
| `Timezone` | `Person.timezone` | direct copy | Keep source wording |
| `Share Email?` | `MentorProfile.share_email_permission` | derived transform | Now supported as an alias in the current transform |
| `Share Email Permission` / `Share Email` | `MentorProfile.share_email_permission` | derived transform | Normalize to boolean |
| `Meeting Request Link` / `Meeting Request Links` | `MentorProfile.booking_link` | direct copy | Supported as aliases for mentor booking or intake links |
| `Booking Link` / `Calendar Link` | `MentorProfile.booking_link` | direct copy | Keep raw URL |
| `Status` / `Active` | `Person.active_flag`, `MentorProfile.mentor_active_flag` | derived transform | Normalize active state |
| `Employer` / `Organization` | possible later `Organization` and `Affiliation` | review-needed | Current transform does not auto-create employer org records from mentor rows |
| engagement trace fields such as last meeting or request history | possible `Interaction` | review-needed | Only create `Interaction` when the trace is clearly dated and attributable |
| public-facing readiness fields | derived `ContentIntelligence` inputs later | derived transform | Formal content intelligence is built after normalization |
| unmapped extra columns | none | ignored | Preserve raw until there is a documented use |

### Mentors Entity Rules

#### Person

- A mentor row should normally create one `Person`.
- The current transform trusts:
  - `Mentor Name`
  - `Full Name`
  - `Name`

#### MentorProfile

- A mentor row should create a `MentorProfile` when mentor identity is clear.
- Program labels stay on `MentorProfile` for now.
- They do not create standalone `Program` records in Phase 1.

#### Organization and Affiliation

- Do not auto-create employer organizations from mentor rows unless the business rule is settled first.
- Employer text is often too messy or too descriptive to trust without review.

#### Interaction

- A meeting request link is not an `Interaction` by itself.
- A mentor row should only create `Interaction` if it includes a dated trace such as:
  - a request date
  - a meeting date
  - a clear owner
  - a clear subject or participant

#### ContentIntelligence

- Do not write raw mentor fields straight into `ContentIntelligence`.
- Later enrichment should use normalized fields such as:
  - `Person.bio`
  - `Person.headshot_url`
  - `Person.linkedin`
  - `Person.expertise_tags`
  - `MentorProfile.mentor_location_type`
  - `MentorProfile.booking_link`

### Mentors Transform Rules

#### How `person_type` is derived

For `Mentors`, the current transform sets `person_type="mentor"` when:

- the source table is `Mentors`
- or a `Mentor Name` field is present

Fallback name-only rows in the mentors source also become mentor people.

#### How `mentor_location_type` is derived

Current derivation order:

1. look at `Mentor Location Type`, `Mentor Location`, `Location Type`, or `Availability`
2. normalize:
   - values containing `local` or `in-person` -> `local`
   - values containing `remote` or `virtual` -> `remote`
   - values containing `hybrid` -> `hybrid`
3. if explicit classification is absent but a location or mailing address exists, default to `local`
4. if explicit location text exists but cannot be normalized, emit `review_mentor_location_type`

#### How grouped or placeholder mentor records are flagged

- placeholder names such as `TBD Mentor` emit `review_placeholder_record`
- grouped name text such as `Mentor Team` emits `review_grouped_record_detected`

#### How sparse mentor records are flagged

Typical sparse mentor review conditions:

- missing email -> `review_person_missing_email`
- missing bio, headshot, or other story assets -> later content intelligence review flags

## Concrete Raw-To-Normalized Examples

These examples use the safe synthetic pilot fixture patterns already in `tests/fixtures/`.

### Example 1: Clean startup member

Raw row shape:

```text
Source table: Active Members
Record ID: rec_member_001
Company Name: Acme AI
Member Type: Startup
Status: Active
Membership Tier: Core
Founder Name: Jane Founder
Founder Email: jane@acme.ai
Primary Contact Name: Alex Ops
Primary Contact Email: alex@acme.ai
Builder Cohort: Builder Spring 2026
Program Name: Builder
```

Normalized records created:

- `Organization(name="Acme AI", org_type="startup", membership_status="active", membership_tier="Core")`
- `Person(full_name="Jane Founder", person_type="founder", email="jane@acme.ai")`
- `Person(full_name="Alex Ops", person_type="operator", email="alex@acme.ai")`
- `Affiliation(role_title="Founder", founder_flag=True)`
- `Affiliation(role_title="Primary Contact", primary_contact_flag=True)`
- `Program(program_name="Builder")`
- `Cohort(cohort_name="Builder Spring 2026")`
- `Participation(participation_status="active")`

Review flags created:

- none

### Example 2: Partner organization with no founder record

Raw row shape:

```text
Source table: Active Members
Record ID: rec_member_002
Company Name: Gulf Coast Manufacturing Network
Member Type: Partner
Status: Active
Website: https://gcmn.org
Primary Contact Name: Riley Partner
Primary Contact Email: riley@gcmn.org
```

Normalized records created:

- `Organization(name="Gulf Coast Manufacturing Network", org_type="partner")`
- `Person(full_name="Riley Partner", person_type="operator")`
- `Affiliation(role_title="Primary Contact", primary_contact_flag=True)`

Review flags created:

- none

### Example 3: Grouped `Personnel` text in a startup row

Raw row shape:

```text
Source table: Active Members
Record ID: rec_member_003
Company Name: Pelican Robotics
Member Type: Startup
Founder Name: Jamie Wells
Primary Contact Name: Ava Chen
Personnel: Jamie Wells - CEO; Ava Chen - COO; Builder Intern Team
```

Normalized records created:

- `Organization(name="Pelican Robotics", org_type="startup")`
- `Person(full_name="Jamie Wells", person_type="founder")`
- `Person(full_name="Ava Chen", person_type="operator")`
- `Affiliation(role_title="Founder", founder_flag=True)`
- `Affiliation(role_title="Primary Contact", primary_contact_flag=True)`

Review flags created:

- `review_personnel_parse`
- `review_grouped_record_detected`

Operational note:

- The current transform does not create extra `Person` records from the `Personnel` field.

### Example 4: Valid dual-signal member-side person creation

Raw row shape:

```text
Source table: Active Members
Record ID: rec_member_semi_001
Company Name: Signal Works
Personnel: Morgan Rivers - CEO
Primary Email (from Link to Application): morgan@signalworks.example
Cohort: Builder Spring 2026
```

Normalized records created:

- `Organization(name="Signal Works", org_type="startup")`
- `Person(full_name="Morgan Rivers", person_type="operator", person_resolution_basis="semi_structured_member_side")`
- `Affiliation(role_title="Member Contact")`

Review flags created:

- none

Operational note:

- The person is created only because the row has one clean full-name candidate, one unique non-generic email, and one resolved organization context.

### Example 5: Sparse member row with unclear org type

Raw row shape:

```text
Source table: Active Members
Record ID: rec_member_004
Company Name: Bayou Build Collective
Status: Active
```

Normalized records created:

- `Organization(name="Bayou Build Collective", org_type="other", membership_status="active")`

Review flags created:

- `review_org_type`
- `review_sparse_record`

### Example 6: Internal OM record

Raw row shape:

```text
Source table: Active Members
Record ID: rec_member_005
Company Name: Opportunity Machine Internal Ops
Member Type: Internal
Status: Active
Primary Contact Name: Taylor Staff
Primary Contact Email: taylor@opportunitymachine.org
```

Normalized records created:

- `Organization(name="Opportunity Machine Internal Ops", org_type="internal")`
- `Person(full_name="Taylor Staff", person_type="operator")`
- `Affiliation(role_title="Primary Contact", primary_contact_flag=True)`

Review flags created:

- `review_internal_record_detected`

### Example 7: Multi-cohort member row

Raw row shape:

```text
Source table: Active Members
Record ID: rec_member_006
Company Name: Delta Dynamics
Member Type: Startup
Builder Cohort: Builder Spring 2025; Builder Fall 2025
Program Name: Builder
```

Normalized records created:

- `Organization(name="Delta Dynamics", org_type="startup")`

Review flags created:

- `review_multi_value_cohort_parse`

Operational note:

- The target shape is still one participation per cohort.
- The current implementation does not auto-split this row yet.

### Example 8: Clean mentor row

Raw row shape:

```text
Source table: Mentors
Record ID: rec_mentor_001
Full Name: Morgan Guide
Email: morgan@example.com
Expertise: AI, Go-to-market
Mentor Program Type: Builder
Mentor Location Type: Local
Booking Link: https://calendar.example.com/morgan
```

Normalized records created:

- `Person(full_name="Morgan Guide", person_type="mentor", expertise_tags="AI, Go-to-market")`
- `MentorProfile(mentor_program_type="Builder", mentor_location_type="local", share_email_permission=True)`

Review flags created:

- none

### Example 9: Sparse mentor row

Raw row shape:

```text
Source table: Mentors
Record ID: rec_mentor_003
Full Name: Jordan Sparse
Program: Builder
Status: Active
```

Normalized records created:

- `Person(full_name="Jordan Sparse", person_type="mentor")`
- `MentorProfile(mentor_program_type="Builder")`

Review flags created:

- `review_person_missing_email`

## Biggest Ambiguity Cases

These still need human review or a later hardening pass.

- `Personnel` fields that mix names, titles, and team labels
- multi-value cohort cells that bundle several cohorts into one string
- `Meeting Requests` or `Feedback` columns embedded in member or mentor rows without a clean date and subject
- mentor employer values that may be descriptors instead of real organizations
- placeholder or grouped records that look real enough to pass a loose parser

When in doubt, preserve the raw row, create only the records that are clearly justified, and let the review queue carry the rest.
