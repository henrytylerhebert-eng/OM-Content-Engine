# Organization Classification Rules

## Purpose

These rules exist to classify organizations from messy operational exports into a more useful `org_type` field without pretending the source is cleaner than it is.

The goal is not perfect taxonomy.

The goal is to reduce the number of obviously classifiable organizations falling into `other` or `unknown`, while keeping weak cases in review.

## Current Target Types

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

## Rule Order

The current classifier works in a strict order.

### 1. Explicit source type wins

If the source row includes one of these fields and the value is usable:

- `Organization Type`
- `Org Type`
- `Member Type`
- `Category`
- `Company Type`

Then the transform maps it directly into a normalized `org_type`.

### 2. Internal patterns override membership assumptions

Classify as `internal` when the row clearly points to Opportunity Machine itself, such as:

- company name contains `Opportunity Machine`
- website domain contains `opportunitymachine`
- source table is `Personnel`

### 3. Strong institutional and sector patterns come next

These should only trigger on strong signals.

#### `government`

Use when one of these is clearly present:

- website domain ends with `.gov`
- name contains phrases like `Louisiana Economic Development`, `Department of`, `Office of`, `City of`, or `Parish`

#### `university`

Use when one of these is clearly present:

- website domain ends with `.edu`
- name contains `University`, `College`, `Community College`, `School of`, or `UL Lafayette`

#### `investor`

Use when one of these is clearly present:

- website domain ends with `.vc`
- description explicitly uses investor language like `investor`, `investment firm`, `investment fund`, `investment research`, `venture capital`, `angel investor`, `deal sourcing`, or `private equity`
- name contains standalone investor words like `Capital`, `Ventures`, `Angel`, or `Fund` and the description also reads like an investment organization

Do not trigger this rule on partial word matches like `Adventure` or `Archangel` alone.

#### `nonprofit`

Use when one of these is clearly present:

- name contains `Foundation`, `Association`, `Alliance`, `Coalition`, or `Chamber`
- website is `.org` and the description explicitly reads like a mission-based service organization

#### `mentor_org`

Use only for clear mentor-network language such as:

- `mentor network`
- `mentorship network`
- `mentor matching`

#### `service_provider`

Use only for strong professional-service signals, especially:

- `consulting`
- `legal`
- `financial planning`
- `advisors`
- `advisory`
- `insurance`
- `marketing`
- `creative`
- `notary`
- `billing`

These should be strong and specific. The classifier should not treat generic words like `solutions` or `services` alone as enough.

### 4. Membership tier is the next strong signal

When the source is `Active Members`, `Confirmed Membership Level` is useful operational context.

#### Partner

If membership level is `Partner`, classify as `partner` unless a stronger rule above already identified something more specific like `government`, `university`, `investor`, `nonprofit`, or `service_provider`.

#### Startup

If membership level is one of:

- `Standard`
- `Build`
- `Momentum`

classify as `startup` unless a stronger rule above already identified something more specific.

### 5. Startup membership signals can still classify a row

If membership level is missing but the row still has strong program-member context, classify as `startup` when at least one of these is present:

- `Accessible Space`
- `Cohort`
- `Builder Cohort`
- `2.0 Cohort`
- `Application Date`
- `Link to Application`

These are operational signals that the row belongs to the startup-member workflow rather than a generic ecosystem org list.

### 6. Fallback

If none of the strong rules apply:

- return `unknown`
- emit `review_org_type`

Use `other` only when the source explicitly labels the row that way or another future business rule intentionally assigns it.

## What The Rules Should Not Do

The classifier should not:

- use broad buzzwords in descriptions to infer service-provider status
- treat every `.org` website as a nonprofit
- treat every partner-tier record as the same institutional type
- silently turn weak or missing signals into a confident org type

## Why This Works Better For The Real Export

The real `Active Members` export does not include a clean org-type field, but it does include operational context that is still useful:

- `Confirmed Membership Level`
- `Accessible Space`
- `Cohort`
- `Application Date`
- `Company Name`
- `Company Website`
- company description

Those signals are strong enough to distinguish many startups and partner-tier organizations from truly unknown rows without pretending the taxonomy is perfect.
