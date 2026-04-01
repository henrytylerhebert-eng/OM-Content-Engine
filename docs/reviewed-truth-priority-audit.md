# Reviewed-Truth Priority Audit

## Scope

This audit uses the current real-run snapshot in `data/processed/airtable_run/`.

At audit time, `data/processed/local_run/` did not exist and `data/raw/` was empty, so `airtable_run` is the latest real review queue available in the repo.

## Current State

- `organization_count`: 96
- `people_count`: 55
- `mentor_profile_count`: 55
- `participation_count`: 64
- `review_flag_count`: 545
- `content candidate count`: 119
- `reviewed_truth_backed candidates`: 0
- `public_ready candidates`: 0

Important constraints:

- all current person candidates are mentor-derived
- there are no structured or semi-structured member-side people in the real run
- reviewed truth can improve trust and reduce false positives
- reviewed truth cannot create the missing founder/operator people records that do not exist yet

## What Overrides Help Most Right Now

The highest-value reviewed-truth work is:

1. confirm a small set of clean mentor candidates so the planning list is not entirely heuristic
2. suppress a small set of org-only spotlight candidates that currently look stronger than the underlying trust supports

This improves internal candidate quality now without pretending the founder/operator gap is solved.

## First 20 Proposed Overrides

### Batch A: confirm 10 clean mentor candidates for planning use

Use `person_content` overrides with an empty `set` to mark these as reviewed-truth-backed planning candidates.

These are good first confirmations because they already read as strong internal candidates and their remaining burden is mostly missing org-context assets, not identity risk.

| Priority | Record | Match target | Match field | Proposed action | Why this is high value |
| --- | --- | --- | --- | --- | --- |
| 1 | Chris Kimmel | `person_content` | `linked_person_id=person:chris_kimmel_louisiana_edu` | confirm only | cleanest current mentor candidate; no current review flag summary on the candidate row |
| 2 | Aditya Visweswaran | `person_content` | `linked_person_id=person:avbuy42_gmail_com` | confirm only | bio, expertise, headshot present; good internal feature candidate |
| 3 | Aishwarya Parasuram | `person_content` | `linked_person_id=person:aishwarya_parasuram92_gmail_com` | confirm only | strong mentor profile; review burden is asset-oriented, not identity-oriented |
| 4 | Alex Lanclos | `person_content` | `linked_person_id=person:alexlanclos_gmail_com` | confirm only | strong planning candidate for mentor feature work |
| 5 | Ali Chapman | `person_content` | `linked_person_id=person:ali_thoughtfulgm_com` | confirm only | good planning candidate with strong supporting evidence |
| 6 | Amol Desai | `person_content` | `linked_person_id=person:amoldesai_latticeworkinvestments_com` | confirm only | strong mentor record that can anchor internal brief generation |
| 7 | Andrew Tabit | `person_content` | `linked_person_id=person:andrew_leansquad_com` | confirm only | good mentor candidate with strong narrative substance |
| 8 | Axel Strombergsson | `person_content` | `linked_person_id=person:axel_straightline_tech_com` | confirm only | strong mentor candidate; useful to reduce all-heuristic planning exports |
| 9 | Ben Norwood | `person_content` | `linked_person_id=person:ben_norwood821_gmail_com` | confirm only | another clean mentor record that helps seed a reviewed-truth-backed candidate pool |
| 10 | Bill Ellison | `person_content` | `linked_person_id=person:bill_innovationcatalyst_us` | confirm only | strong mentor candidate for internal feature planning |

### Batch B: suppress 10 misleading org-only spotlight candidates until human review catches up

Use `organization_content` overrides with `suppress: true`.

These are high value because they currently appear in the candidate export as `spotlight_ready`, but their unresolved person ambiguity materially weakens trust. Suppressing them now makes the planning list more honest.

| Priority | Record | Match target | Match field | Proposed action | Why this is high value |
| --- | --- | --- | --- | --- | --- |
| 11 | Acadiana Veteran Alliance | `organization_content` | `linked_organization_id=org:acadiana_veteran_alliance` | suppress | sparse plus grouped personnel ambiguity; too weak for spotlight-style planning right now |
| 12 | Chase Robotics LLC | `organization_content` | `linked_organization_id=org:chase_robotics_llc` | suppress | grouped personnel parse and no resolved person make the spotlight signal misleading |
| 13 | Collective Wealth Advisors / Burnette Financial Planning | `organization_content` | `linked_organization_id=org:collective_wealth_advisors_burnette_financial_planning` | suppress | service-provider candidate with grouped personnel ambiguity and no trusted human anchor |
| 14 | DealFlow | `organization_content` | `linked_organization_id=org:dealflow` | suppress | multi-person ambiguity plus no resolved founder/operator makes current candidate quality too weak |
| 15 | Far UVC Innovations | `organization_content` | `linked_organization_id=org:far_uvc_innovations` | suppress | unresolved grouped personnel burden is too high for spotlight planning |
| 16 | Acadian Capital Research | `organization_content` | `linked_organization_id=org:acadian_capital_research` | suppress | sparse investor record with no trusted person linkage |
| 17 | Adjuvant Behavioral Health of Louisiana LLC | `organization_content` | `linked_organization_id=org:adjuvant_behavioral_health_of_louisiana_llc` | suppress | sparse startup record with no founder/operator visibility |
| 18 | Atchafalaya Intelligence | `organization_content` | `linked_organization_id=org:atchafalaya_intelligence` | suppress | sparse candidate with unresolved person context |
| 19 | Exepron | `organization_content` | `linked_organization_id=org:exepron` | suppress | sparse startup candidate with no trusted human anchor |
| 20 | GlowSens (Ammunition) | `organization_content` | `linked_organization_id=org:glowsens_ammunition` | suppress | sparse candidate with unresolved person context and weak current content trust |

## Why These 20 First

This list deliberately does two things:

- it creates a small reviewed-truth-backed person candidate pool immediately
- it removes some of the noisiest org-only spotlight candidates that currently overstate trust

That improves the planning export faster than trying to hand-edit 20 weak organization records that still do not have real founder/operator visibility.

## What This Does Not Fix

These overrides do not solve the main member-side people gap.

The current real run still has:

- `review_no_person_found`: 96
- `review_no_affiliation_people`: 96
- `review_member_side_person_context_ambiguous`: 62
- `review_personnel_parse`: 34
- `review_member_side_person_multiple_candidates`: 34

That means founder/operator visibility is still blocked mostly by missing or ambiguous person creation, not by missing reviewed truth.

## Best Next Step After These 20

After this first override pass, the next highest-leverage move is:

- review a small batch of member-side records with real contact evidence
- decide whether those cases should become source fixes, normalization improvements, or future reviewed-truth-supported person confirmation paths

In short:

- use reviewed truth now to improve trust
- do not expect it to replace the next person-resolution pass
