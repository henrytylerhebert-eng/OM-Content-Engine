# Phase 1 Execution Contract

Source context:
- OM Marketing OS Strategy
- OM Marketing OS Airtable Schema
- Builder 1.0 Asset Pack
- Agent Prompt Library

Status: INTERNAL ONLY
Scope: Planning-only and operator-facing

## 1. Purpose Of Phase 1

Phase 1 exists to turn known campaign facts, known source material, and reviewed operator inputs into a usable weekly planning pack.

Phase 1 is meant to help an OM operator:

- choose people or organizations to contact
- send outreach the same day
- identify one post that can be drafted next
- identify one missing proof item that blocks stronger content

Phase 1 does not execute outreach, publish content, or change Airtable automatically.

## 2. Allowed Outputs

Phase 1 may produce only internal planning artifacts such as:

- weekly growth plans
- growth target lists
- partnership target lists
- outreach angle drafts
- content hook lists
- proof-gap lists
- internal content brief drafts
- weekly execution task lists
- signal review notes

All Phase 1 outputs must stay internal and must remain clear about what is known, unknown, and unverified.

## 3. Disallowed Outputs

Phase 1 must not produce:

- runtime code
- UI work
- chat features
- agent behavior
- scraping systems
- automation pipelines
- Airtable sync or write-back behavior
- auto-generated outbound messages sent without human review
- public-facing posts presented as approved
- claims, quotes, metrics, or outcomes without source proof

If a requested artifact crosses into one of these areas, stop and restate the boundary before continuing.

## 4. Required Source Inputs

Before Phase 1 planning work begins, the operator should gather the current available source inputs:

- OM Marketing OS Strategy
- OM Marketing OS Airtable Schema
- Builder 1.0 Asset Pack
- Agent Prompt Library
- confirmed campaign facts such as dates, CTA, and audience
- reviewed operator notes or approved planning inputs

Before a content brief is drafted, the operator must also confirm the specific proof needed for that brief. Typical proof inputs include:

- confirmed interest form link
- curriculum or weekly structure description
- selection criteria that can be shared
- mentor role description
- approved staff author or spokesperson
- any reviewed signal that supports the claim

If a needed source input is missing, the missing item stays visible as `[Unknown]`.

## 5. Rules For Handling `[Unknown]`

`[Unknown]` is the default marker when a fact, owner, metric, quote, source, or contact is not confirmed.

Rules:

- do not replace `[Unknown]` with guesses
- do not convert `[Unknown]` into polished language
- do not hide `[Unknown]` inside vague wording
- keep `[Unknown]` visible until a human confirms the fact from a source
- if a detail is plausible but still not confirmed, it remains `[Unknown]`

If a planning file already contains an unverified placeholder, keep the uncertainty explicit and do not upgrade it into a claim.

## 6. How Planning Docs Become Content Briefs

A planning item can become a content brief only when all of the following are true:

- the hook or angle is still relevant to the active campaign
- the audience is clear
- the CTA is clear
- the underlying claim has source proof
- any named author or approver is identified

Each content brief should capture:

- source planning item
- audience
- campaign
- claim boundary
- proof sources
- CTA
- missing proof items
- approval owner

If the claim boundary is not clear, the item stays in the planning docs and does not move to brief status.

## 7. How Content Briefs Become Weekly Execution Tasks

A content brief becomes a weekly execution task only after a human decides it is ready for work in the current cycle.

Weekly execution tasks should be narrow and operator-usable. Examples:

- draft Hook 04 deadline post
- confirm interest form link with owner
- send outreach to two named founder candidates
- prepare partner one-pager for one named referral partner

Each weekly task should include:

- one owner
- one immediate action
- one due date or current-cycle timing
- any blocking proof item
- the source brief or planning document it came from

If a task cannot be acted on the same week, it should stay as a brief or planning item instead of being promoted into the weekly task list.

## 8. Human Approval Requirements

Human approval is required before:

- any outward-facing content is drafted for publication
- any outreach copy is treated as final
- any selection criteria are presented publicly
- any mentor-role description is sent externally
- any staff-expertise or founder-story content is treated as publishable
- any metric, quote, or outcome claim is included in a brief

Human approval should confirm:

- the claim is supported
- the audience is correct
- the CTA is correct
- the source is acceptable to cite
- the content is safe to use outside internal planning

No artifact becomes public-ready just because it exists in the repo.

## 9. Signal Tracking Rules

A usable content signal is a concrete input that can support planning or briefing work without stretching beyond the source.

A usable signal should be:

- tied to a known source
- relevant to the active campaign
- specific enough to support an action or claim boundary
- recent enough to matter for the current cycle
- reviewable by a human

Signal tracking rules:

- track the source of the signal
- separate source truth from interpretation
- do not treat planning heuristics as proof
- do not treat repo artifacts as a replacement for Airtable
- keep manual review in the loop for anything that could become a public claim

If the signal cannot be traced back to a source, it may inform operator curiosity but it does not qualify as proof.

## 10. Phase 1 Exit Criteria

Phase 1 is complete for a cycle only when the operator has:

- one weekly growth plan for the active campaign
- named targets or clearly marked `[Unknown]` placeholders
- at least one content item that is either ready now or clearly blocked by proof
- at least one missing proof item assigned or escalated
- a short weekly task list tied back to the planning docs
- human review points identified for any item that could move outward

Phase 1 is not complete if it produces only ideas without operators knowing:

- who to contact
- what to ask
- what content can be drafted next
- what proof is still missing

## Operating Rule

Keep Phase 1 boring.

Plain planning is the goal. Clear source boundaries are the goal. The contract succeeds when an operator can act the same day without pretending that execution, proof, or approval already happened.
