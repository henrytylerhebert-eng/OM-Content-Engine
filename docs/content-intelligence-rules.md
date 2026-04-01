# Content Intelligence Rules

## Purpose

This layer helps identify which founders, mentors, partners, and organizations are usable for:

- founder spotlights
- mentor features
- event promotion
- ecosystem proof posts
- newsletter inclusion
- program recruitment messaging

The logic is rule-based on purpose. It should be easy to explain why a record was included, why it was excluded, and what is missing.

## Output Shape

Each content-intelligence record can include:

- `content_eligible`
- `internally_usable`
- `content_ready`
- `spotlight_ready`
- `externally_publishable`
- `spokesperson_candidate`
- `founder_story_candidate`
- `mentor_story_candidate`
- `ecosystem_proof_candidate`
- `missing_content_assets`
- `profile_completeness_score`
- supporting tags such as `audience_tags`, `proof_tags`, `narrative_theme`, `message_pillar`, and `story_type`

The bundle output also includes `review_rows` for sparse profiles.

## Readiness Ladder

The current content layer uses a practical four-step ladder:

- `internally_usable`: trusted enough for internal planning and candidate review
- `content_ready`: strong enough for lightweight drafting or a short mention
- `spotlight_ready`: strong enough for a real feature or highlighted story package
- `externally_publishable`: approved for public use through reviewed truth only

`content_eligible` is still a gate. It answers a different question:

- should this kind of record even be considered for content use?

The ladder answers:

- how far can staff safely use this record right now?

## Minimum Expectations By Level

| Level | Minimum expectation |
| --- | --- |
| `internally_usable` | Trusted enough for internal planning. Requires content eligibility plus at least one identity or planning anchor. |
| `content_ready` | Draftable for lightweight use. Requires `internally_usable`, enough profile substance to avoid guesswork, and `profile_completeness_score >= 35`. |
| `spotlight_ready` | Suitable for a real feature candidate. Requires `content_ready`, a stronger story signal, and a higher completeness threshold. |
| `externally_publishable` | Explicitly approved for public use. Never set by heuristics. Must come from reviewed truth. |

## Person Rules

### Content eligible

A person is content-eligible when:

- `active_flag` is truthy
- `person_type` is one of:
  - `founder`
  - `mentor`
  - `operator`
  - `partner_contact`

Internal staff are not treated as content-eligible by default.

### Internally usable

A person is internally usable when:

- `content_eligible` is true
- and the record has at least one identity or planning anchor such as:
  - email
  - linkedin
  - headshot
  - bio
  - expertise
  - cohort history
  - linked organization website or description
  - location
  - spokesperson signal

This is the lowest useful rung for internal content planning.

### Spokesperson candidate

A person is a spokesperson candidate when the person is content-eligible and at least one of these is true:

- `public_facing_ready`
- `speaker_ready`
- an affiliation marks `spokesperson_flag`
- an affiliation marks `primary_contact_flag`
- the person is a mentor

### Founder story candidate

A founder is a story candidate when:

- `person_type == "founder"`
- the person is active
- and at least one of these is true:
  - has a bio
  - has a headshot
  - has cohort history
  - is tied to an organization with a website
  - is tied to an organization with a description

### Mentor story candidate

A mentor is a story candidate when:

- `person_type == "mentor"`
- the person is active
- and the record has a bio or expertise tags

### Ecosystem proof candidate

A person is an ecosystem proof candidate when the person is content-eligible and at least one of these is true:

- current cohort history
- alumni cohort history
- expertise tags
- spokesperson candidate

### Content ready

A person is content-ready when:

- `internally_usable` is true
- `profile_completeness_score >= 35`
- and at least one drafting asset exists, such as:
  - bio
  - expertise
  - headshot
  - linkedin
  - cohort history
  - linked organization website or description

## Organization Rules

### Content eligible

An organization is content-eligible when:

- `active_flag` is truthy
- `org_type` is one of:
  - `startup`
  - `partner`
  - `investor`
  - `university`
  - `mentor_org`
  - `service_provider`
  - `government`
  - `nonprofit`

Internal organizations and `other` do not qualify by default.

### Internally usable

An organization is internally usable when:

- `content_eligible` is true
- and the record has at least one planning anchor such as:
  - website
  - description
  - industry
  - stage
  - location
  - cohort history
  - spokesperson signal

### Spokesperson candidate

An organization has a spokesperson candidate when one or more affiliated people are public-facing or speaker-ready.

### Founder story candidate

A startup organization is a founder story candidate when it has at least one affiliated founder.

### Ecosystem proof candidate

An organization is an ecosystem proof candidate when it is content-eligible and at least one of these is true:

- current cohort history
- alumni cohort history
- has a website
- has a description
- is a partner organization

### Content ready

An organization is content-ready when:

- `internally_usable` is true
- `profile_completeness_score >= 35`
- and at least one outward-facing content asset or proof signal exists, such as:
  - website
  - description
  - cohort history
  - spokesperson signal
  - founder-story linkage

## Completeness Scores

The completeness score is not a black-box score. It is a simple sum of present assets.

### Person completeness

| Asset | Weight |
| --- | --- |
| bio | 25 |
| headshot | 20 |
| linkedin | 10 |
| expertise | 15 |
| location | 10 |
| organization_website | 10 |
| organization_description | 5 |
| cohort_history | 5 |

### Organization completeness

| Asset | Weight |
| --- | --- |
| description | 30 |
| website | 25 |
| industry | 10 |
| stage | 10 |
| location | 10 |
| spokesperson | 10 |
| cohort_history | 5 |

## Spotlight Rules

### Person spotlight-ready

A person is spotlight-ready when:

- `content_ready` is true
- `profile_completeness_score >= 60`
- and at least one of these is true:
  - `founder_story_candidate`
  - `mentor_story_candidate`
  - `spokesperson_candidate`
  - `ecosystem_proof_candidate`

### Organization spotlight-ready

An organization is spotlight-ready when:

- `content_ready` is true
- `profile_completeness_score >= 55`
- and at least one of these is true:
  - `ecosystem_proof_candidate`
  - `founder_story_candidate`
  - `spokesperson_candidate`

## External Publishability

`externally_publishable` should not be inferred by the content rules.

The current operating position is:

- the content-intelligence layer may infer `content_eligible`
- the content-intelligence layer may infer `internally_usable`
- the content-intelligence layer may infer `content_ready`
- the content-intelligence layer may infer `spotlight_ready`
- only reviewed truth may set `externally_publishable=True`

That keeps public-facing approval separate from heuristic completeness.

## Missing Content Assets

`missing_content_assets` is a comma-separated list of assets that are still missing from the record.

Examples:

- person: `bio, headshot, linkedin`
- organization: `description, website, spokesperson`

This is meant to make content prep work obvious for later Codex, Canva, or Loomly workflows.

## Review Flags

The content layer emits review flags only when the profile is too sparse to trust.

### `review_content_profile_sparse`

Use when a content-eligible record has a very low completeness score.

This also covers content-eligible records that never reach `internally_usable`.

### `review_missing_content_assets`

Use when a content-eligible record is missing several important assets even if it is still usable in a basic way.

## Practical Notes

- This layer should help package content, not replace judgment.
- Missing data should create review rows instead of fake certainty.
- The rules are intentionally narrow so they can be tuned later with real pilot records.
- External publishability is a reviewed-truth decision, not a derived content score.
- Completeness alone should not move a record to public-ready status.
