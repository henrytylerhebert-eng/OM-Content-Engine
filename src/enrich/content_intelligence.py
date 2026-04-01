"""Rule-based content intelligence for storytelling and promotion workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Mapping, Optional, Sequence

from src.transform.review_flags import ReviewFlag, build_review_flag, build_review_queue_rows


PERSON_COMPLETENESS_WEIGHTS = {
    "bio": 25,
    "headshot": 20,
    "linkedin": 10,
    "expertise": 15,
    "location": 10,
    "organization_website": 10,
    "organization_description": 5,
    "cohort_history": 5,
}

ORGANIZATION_COMPLETENESS_WEIGHTS = {
    "description": 30,
    "website": 25,
    "industry": 10,
    "stage": 10,
    "location": 10,
    "spokesperson": 10,
    "cohort_history": 5,
}


@dataclass
class ContentIntelligenceResult:
    """Derived content-intelligence payload plus review flags."""

    intelligence: dict[str, object]
    review_flags: list[ReviewFlag] = field(default_factory=list)


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "active"}


def _split_tags(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.replace(";", ",").split(",") if part.strip()]


def _join_unique(values: Sequence[str]) -> Optional[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.strip()
        if not normalized:
            continue
        lowered = normalized.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        cleaned.append(normalized)
    return ", ".join(cleaned) if cleaned else None


def _record_key(record: Mapping[str, object]) -> Optional[object]:
    return record.get("id") if record.get("id") is not None else record.get("source_record_id")


def _weighted_score(weights: Dict[str, int], present: Dict[str, bool]) -> tuple[int, list[str]]:
    score = 0
    missing: list[str] = []
    for field_name, weight in weights.items():
        if present.get(field_name, False):
            score += weight
        else:
            missing.append(field_name)
    return score, missing


def _any_present(*values: object) -> bool:
    return any(bool(value) for value in values)


def _find_associated_organizations(
    person_payload: Mapping[str, object],
    affiliations: Sequence[dict[str, object]],
    organizations: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    person_key = _record_key(person_payload)
    if person_key is None:
        return []
    organizations_by_key = {
        _record_key(organization): organization
        for organization in organizations
        if _record_key(organization) is not None
    }

    associated: list[dict[str, object]] = []
    for affiliation in affiliations:
        if affiliation.get("person_id") != person_key:
            continue
        organization = organizations_by_key.get(affiliation.get("organization_id"))
        if organization is not None:
            associated.append(organization)
    return associated


def _cohort_history_for_person(
    person_payload: Mapping[str, object],
    affiliations: Sequence[dict[str, object]],
    participations: Sequence[dict[str, object]],
    cohorts: Sequence[dict[str, object]],
) -> tuple[bool, bool]:
    person_key = _record_key(person_payload)
    cohort_map = {
        _record_key(cohort): cohort
        for cohort in cohorts
        if _record_key(cohort) is not None
    }

    current = False
    alumni = False
    if person_key is not None:
        for participation in participations:
            if participation.get("person_id") == person_key:
                status = str(participation.get("participation_status") or "").strip().lower()
                if status == "active":
                    current = True
                if status == "alumni":
                    alumni = True

    organization_ids = {
        affiliation.get("organization_id")
        for affiliation in affiliations
        if affiliation.get("person_id") == person_key
    }
    organization_ids.discard(None)

    for participation in participations:
        if participation.get("organization_id") not in organization_ids:
            continue
        status = str(participation.get("participation_status") or "").strip().lower()
        cohort = cohort_map.get(participation.get("cohort_id"))
        if status == "active" and (cohort is None or _truthy(cohort.get("active_flag"))):
            current = True
        if status == "alumni" or (cohort is not None and not _truthy(cohort.get("active_flag"))):
            alumni = True

    return current, alumni


def _cohort_history_for_organization(
    organization_payload: Mapping[str, object],
    participations: Sequence[dict[str, object]],
    cohorts: Sequence[dict[str, object]],
) -> tuple[bool, bool]:
    organization_key = _record_key(organization_payload)
    cohort_map = {
        _record_key(cohort): cohort
        for cohort in cohorts
        if _record_key(cohort) is not None
    }
    current = False
    alumni = False

    for participation in participations:
        if participation.get("organization_id") != organization_key:
            continue
        status = str(participation.get("participation_status") or "").strip().lower()
        cohort = cohort_map.get(participation.get("cohort_id"))
        if status == "active" and (cohort is None or _truthy(cohort.get("active_flag"))):
            current = True
        if status == "alumni" or (cohort is not None and not _truthy(cohort.get("active_flag"))):
            alumni = True

    return current, alumni


def build_person_content_intelligence(
    person_payload: dict[str, object],
    *,
    affiliations: Sequence[dict[str, object]] = (),
    organizations: Sequence[dict[str, object]] = (),
    participations: Sequence[dict[str, object]] = (),
    cohorts: Sequence[dict[str, object]] = (),
    source_system: str = "derived",
) -> ContentIntelligenceResult:
    """Build a content-intelligence record for a normalized person."""

    person_type = str(person_payload.get("person_type") or "").strip().lower()
    active_flag = _truthy(person_payload.get("active_flag"))
    associated_organizations = _find_associated_organizations(person_payload, affiliations, organizations)
    has_org_website = any(bool(org.get("website")) for org in associated_organizations)
    has_org_description = any(bool(org.get("description")) for org in associated_organizations)
    current_cohort, alumni_cohort = _cohort_history_for_person(
        person_payload,
        affiliations,
        participations,
        cohorts,
    )

    content_eligible = active_flag and person_type in {"founder", "mentor", "operator", "partner_contact"}
    spokesperson_candidate = content_eligible and (
        _truthy(person_payload.get("public_facing_ready"))
        or _truthy(person_payload.get("speaker_ready"))
        or any(
            _truthy(affiliation.get("spokesperson_flag")) or _truthy(affiliation.get("primary_contact_flag"))
            for affiliation in affiliations
            if affiliation.get("person_id") == _record_key(person_payload)
        )
        or person_type == "mentor"
    )
    founder_story_candidate = (
        person_type == "founder"
        and active_flag
        and (
            bool(person_payload.get("bio"))
            or bool(person_payload.get("headshot_url"))
            or current_cohort
            or alumni_cohort
            or has_org_website
            or has_org_description
        )
    )
    mentor_story_candidate = (
        person_type == "mentor"
        and active_flag
        and (bool(person_payload.get("bio")) or bool(person_payload.get("expertise_tags")))
    )
    ecosystem_proof_candidate = content_eligible and active_flag and (
        current_cohort
        or alumni_cohort
        or bool(person_payload.get("expertise_tags"))
        or spokesperson_candidate
    )
    identity_anchor = _any_present(
        person_payload.get("email"),
        person_payload.get("linkedin"),
        person_payload.get("headshot_url"),
        person_payload.get("bio"),
        person_payload.get("expertise_tags"),
    )
    planning_context = _any_present(
        current_cohort,
        alumni_cohort,
        has_org_website,
        has_org_description,
        person_payload.get("location"),
        spokesperson_candidate,
    )

    present_assets = {
        "bio": bool(person_payload.get("bio")),
        "headshot": bool(person_payload.get("headshot_url")),
        "linkedin": bool(person_payload.get("linkedin")),
        "expertise": bool(person_payload.get("expertise_tags")),
        "location": bool(person_payload.get("location")),
        "organization_website": has_org_website,
        "organization_description": has_org_description,
        "cohort_history": current_cohort or alumni_cohort,
    }
    completeness_score, missing_assets = _weighted_score(PERSON_COMPLETENESS_WEIGHTS, present_assets)
    internally_usable = content_eligible and (identity_anchor or planning_context)
    content_ready = internally_usable and completeness_score >= 35 and _any_present(
        person_payload.get("bio"),
        person_payload.get("expertise_tags"),
        person_payload.get("headshot_url"),
        person_payload.get("linkedin"),
        current_cohort,
        alumni_cohort,
        has_org_website,
        has_org_description,
    )

    audience_tags: list[str] = []
    proof_tags: list[str] = []
    industry_tags = _split_tags(person_payload.get("expertise_tags"))  # type: ignore[arg-type]
    if person_type == "founder":
        audience_tags.extend(["founders", "newsletter"])
    if person_type == "mentor":
        audience_tags.extend(["mentors", "newsletter"])
    if spokesperson_candidate:
        audience_tags.append("events")
    if current_cohort:
        audience_tags.append("recruitment")
        proof_tags.append("current_cohort")
    if alumni_cohort:
        proof_tags.append("alumni_cohort")
    if spokesperson_candidate:
        proof_tags.append("spokesperson")
    if founder_story_candidate:
        proof_tags.append("founder_story")
    if mentor_story_candidate:
        proof_tags.append("mentor_story")
    if ecosystem_proof_candidate:
        proof_tags.append("ecosystem_proof")

    narrative_theme = None
    message_pillar = None
    story_type = "profile"
    if founder_story_candidate:
        narrative_theme = "founder_journey"
        story_type = "founder_spotlight"
    elif mentor_story_candidate:
        narrative_theme = "mentor_expertise"
        story_type = "mentor_feature"
    elif spokesperson_candidate:
        narrative_theme = "ecosystem_voice"
        story_type = "speaker_profile"

    if current_cohort:
        message_pillar = "program_recruitment"
    elif ecosystem_proof_candidate:
        message_pillar = "ecosystem_proof"
    elif internally_usable:
        message_pillar = "newsletter_profile"

    spotlight_ready = content_ready and completeness_score >= 60 and (
        founder_story_candidate
        or mentor_story_candidate
        or spokesperson_candidate
        or ecosystem_proof_candidate
    )

    review_flags: list[ReviewFlag] = []
    source_table = str(person_payload.get("source_table") or "content_intelligence")
    if content_eligible and not internally_usable:
        review_flags.append(
            build_review_flag(
                "review_content_profile_sparse",
                source_table=source_table,
                source_record_id=person_payload.get("source_record_id"),  # type: ignore[arg-type]
                source_system=str(person_payload.get("source_system") or source_system),
                record_label=str(person_payload.get("full_name") or ""),
                source_field="internally_usable",
                raw_value=internally_usable,
                note="Identity or planning context is too weak for internal content use.",
            )
        )
    elif content_eligible and completeness_score < 35:
        review_flags.append(
            build_review_flag(
                "review_content_profile_sparse",
                source_table=source_table,
                source_record_id=person_payload.get("source_record_id"),  # type: ignore[arg-type]
                source_system=str(person_payload.get("source_system") or source_system),
                record_label=str(person_payload.get("full_name") or ""),
                source_field="profile_completeness_score",
                raw_value=completeness_score,
                note=_join_unique(missing_assets) or "profile completeness below threshold",
            )
        )
    if content_eligible and len(missing_assets) >= 3:
        review_flags.append(
            build_review_flag(
                "review_missing_content_assets",
                source_table=source_table,
                source_record_id=person_payload.get("source_record_id"),  # type: ignore[arg-type]
                source_system=str(person_payload.get("source_system") or source_system),
                record_label=str(person_payload.get("full_name") or ""),
                source_field="missing_content_assets",
                raw_value=_join_unique(missing_assets),
                note="Missing several assets needed for polished content packaging.",
            )
        )

    intelligence = {
        "linked_person_id": person_payload.get("id"),
        "linked_organization_id": None,
        "audience_tags": _join_unique(audience_tags),
        "industry_tags": _join_unique(industry_tags),
        "proof_tags": _join_unique(proof_tags),
        "content_eligible": content_eligible,
        "internally_usable": internally_usable,
        "content_ready": content_ready,
        "narrative_theme": narrative_theme,
        "message_pillar": message_pillar,
        "story_type": story_type,
        "spotlight_ready": spotlight_ready,
        "externally_publishable": False,
        "spokesperson_candidate": spokesperson_candidate,
        "founder_story_candidate": founder_story_candidate,
        "mentor_story_candidate": mentor_story_candidate,
        "ecosystem_proof_candidate": ecosystem_proof_candidate,
        "missing_content_assets": _join_unique(missing_assets),
        "profile_completeness_score": completeness_score,
        "last_featured_date": None,
        "priority_score": completeness_score,
        "source_record_id": person_payload.get("source_record_id"),
        "source_system": person_payload.get("source_system") or source_system,
    }
    return ContentIntelligenceResult(intelligence=intelligence, review_flags=review_flags)


def build_organization_content_intelligence(
    organization_payload: dict[str, object],
    *,
    affiliated_people: Sequence[dict[str, object]] = (),
    participations: Sequence[dict[str, object]] = (),
    cohorts: Sequence[dict[str, object]] = (),
    source_system: str = "derived",
) -> ContentIntelligenceResult:
    """Build a content-intelligence record for a normalized organization."""

    org_type = str(organization_payload.get("org_type") or "").strip().lower()
    active_flag = _truthy(organization_payload.get("active_flag"))
    content_eligible = active_flag and org_type in {
        "startup",
        "partner",
        "investor",
        "university",
        "mentor_org",
        "service_provider",
        "government",
        "nonprofit",
    }
    current_cohort, alumni_cohort = _cohort_history_for_organization(
        organization_payload,
        participations,
        cohorts,
    )
    spokesperson_candidate = any(
        _truthy(person.get("public_facing_ready")) or _truthy(person.get("speaker_ready"))
        for person in affiliated_people
    )
    founder_story_candidate = org_type == "startup" and any(
        str(person.get("person_type") or "").strip().lower() == "founder"
        for person in affiliated_people
    )
    mentor_story_candidate = False
    ecosystem_proof_candidate = content_eligible and (
        current_cohort
        or alumni_cohort
        or bool(organization_payload.get("website"))
        or bool(organization_payload.get("description"))
        or org_type == "partner"
    )
    planning_context = _any_present(
        organization_payload.get("website"),
        organization_payload.get("description"),
        organization_payload.get("industry"),
        organization_payload.get("stage"),
        organization_payload.get("headquarters_location"),
        current_cohort,
        alumni_cohort,
        spokesperson_candidate,
    )

    present_assets = {
        "description": bool(organization_payload.get("description")),
        "website": bool(organization_payload.get("website")),
        "industry": bool(organization_payload.get("industry")),
        "stage": bool(organization_payload.get("stage")),
        "location": bool(organization_payload.get("headquarters_location")),
        "spokesperson": spokesperson_candidate,
        "cohort_history": current_cohort or alumni_cohort,
    }
    completeness_score, missing_assets = _weighted_score(ORGANIZATION_COMPLETENESS_WEIGHTS, present_assets)
    internally_usable = content_eligible and planning_context
    content_ready = internally_usable and completeness_score >= 35 and _any_present(
        organization_payload.get("website"),
        organization_payload.get("description"),
        current_cohort,
        alumni_cohort,
        spokesperson_candidate,
        founder_story_candidate,
        ecosystem_proof_candidate,
    )

    audience_tags: list[str] = ["newsletter"] if content_eligible else []
    proof_tags: list[str] = []
    if org_type == "startup":
        audience_tags.append("founders")
    if org_type == "partner":
        audience_tags.append("partners")
    if current_cohort:
        audience_tags.append("recruitment")
        proof_tags.append("current_cohort")
    if alumni_cohort:
        proof_tags.append("alumni_cohort")
    if founder_story_candidate:
        proof_tags.append("founder_story")
    if ecosystem_proof_candidate:
        proof_tags.append("ecosystem_proof")
    if spokesperson_candidate:
        proof_tags.append("spokesperson")

    narrative_theme = None
    message_pillar = None
    story_type = "organization_profile"
    if org_type == "startup":
        narrative_theme = "startup_progress"
        story_type = "founder_spotlight"
    elif org_type in {"partner", "government", "nonprofit", "university", "mentor_org"}:
        narrative_theme = "ecosystem_partner"
        story_type = "ecosystem_proof"

    if current_cohort:
        message_pillar = "program_recruitment"
    elif ecosystem_proof_candidate:
        message_pillar = "ecosystem_proof"
    elif internally_usable:
        message_pillar = "newsletter_profile"

    spotlight_ready = content_ready and completeness_score >= 55 and (
        ecosystem_proof_candidate or founder_story_candidate or spokesperson_candidate
    )

    review_flags: list[ReviewFlag] = []
    source_table = str(organization_payload.get("source_table") or "content_intelligence")
    if content_eligible and not internally_usable:
        review_flags.append(
            build_review_flag(
                "review_content_profile_sparse",
                source_table=source_table,
                source_record_id=organization_payload.get("source_record_id"),  # type: ignore[arg-type]
                source_system=str(organization_payload.get("source_system") or source_system),
                record_label=str(organization_payload.get("name") or ""),
                source_field="internally_usable",
                raw_value=internally_usable,
                note="Identity or planning context is too weak for internal content use.",
            )
        )
    elif content_eligible and completeness_score < 35:
        review_flags.append(
            build_review_flag(
                "review_content_profile_sparse",
                source_table=source_table,
                source_record_id=organization_payload.get("source_record_id"),  # type: ignore[arg-type]
                source_system=str(organization_payload.get("source_system") or source_system),
                record_label=str(organization_payload.get("name") or ""),
                source_field="profile_completeness_score",
                raw_value=completeness_score,
                note=_join_unique(missing_assets) or "profile completeness below threshold",
            )
        )
    if content_eligible and len(missing_assets) >= 3:
        review_flags.append(
            build_review_flag(
                "review_missing_content_assets",
                source_table=source_table,
                source_record_id=organization_payload.get("source_record_id"),  # type: ignore[arg-type]
                source_system=str(organization_payload.get("source_system") or source_system),
                record_label=str(organization_payload.get("name") or ""),
                source_field="missing_content_assets",
                raw_value=_join_unique(missing_assets),
                note="Missing several organization assets needed for polished content packaging.",
            )
        )

    intelligence = {
        "linked_person_id": None,
        "linked_organization_id": organization_payload.get("id"),
        "audience_tags": _join_unique(audience_tags),
        "industry_tags": _join_unique(_split_tags(organization_payload.get("industry"))),  # type: ignore[arg-type]
        "proof_tags": _join_unique(proof_tags),
        "content_eligible": content_eligible,
        "internally_usable": internally_usable,
        "content_ready": content_ready,
        "narrative_theme": narrative_theme,
        "message_pillar": message_pillar,
        "story_type": story_type,
        "spotlight_ready": spotlight_ready,
        "externally_publishable": False,
        "spokesperson_candidate": spokesperson_candidate,
        "founder_story_candidate": founder_story_candidate,
        "mentor_story_candidate": mentor_story_candidate,
        "ecosystem_proof_candidate": ecosystem_proof_candidate,
        "missing_content_assets": _join_unique(missing_assets),
        "profile_completeness_score": completeness_score,
        "last_featured_date": None,
        "priority_score": completeness_score,
        "source_record_id": organization_payload.get("source_record_id"),
        "source_system": organization_payload.get("source_system") or source_system,
    }
    return ContentIntelligenceResult(intelligence=intelligence, review_flags=review_flags)


def build_content_intelligence_bundle(
    *,
    organizations: Sequence[dict[str, object]],
    people_payloads: Sequence[dict[str, object]],
    affiliations: Sequence[dict[str, object]] = (),
    participations: Sequence[dict[str, object]] = (),
    cohorts: Sequence[dict[str, object]] = (),
    source_system: str = "derived",
) -> dict[str, object]:
    """Build reporting-friendly content intelligence outputs plus review rows."""

    organization_keys = {
        _record_key(organization): organization
        for organization in organizations
        if _record_key(organization) is not None
    }
    people_by_org: Dict[object, list[dict[str, object]]] = {}
    for affiliation in affiliations:
        organization = organization_keys.get(affiliation.get("organization_id"))
        if organization is None:
            continue
        person = next(
            (
                payload
                for payload in people_payloads
                if _record_key(payload) == affiliation.get("person_id")
            ),
            None,
        )
        if person is not None:
            people_by_org.setdefault(_record_key(organization), []).append(person)

    people_results = [
        build_person_content_intelligence(
            person,
            affiliations=affiliations,
            organizations=organizations,
            participations=participations,
            cohorts=cohorts,
            source_system=source_system,
        )
        for person in people_payloads
    ]
    organization_results = [
        build_organization_content_intelligence(
            organization,
            affiliated_people=people_by_org.get(_record_key(organization), []),
            participations=participations,
            cohorts=cohorts,
            source_system=source_system,
        )
        for organization in organizations
    ]

    review_rows: list[dict[str, Optional[str]]] = []
    for person, result in zip(people_payloads, people_results):
        review_rows.extend(
            build_review_queue_rows(
                source_table=str(person.get("source_table") or "content_intelligence"),
                source_record_id=person.get("source_record_id"),  # type: ignore[arg-type]
                flag_codes=result.review_flags,
                record_label=str(person.get("full_name") or ""),
            )
        )
    for organization, result in zip(organizations, organization_results):
        review_rows.extend(
            build_review_queue_rows(
                source_table=str(organization.get("source_table") or "content_intelligence"),
                source_record_id=organization.get("source_record_id"),  # type: ignore[arg-type]
                flag_codes=result.review_flags,
                record_label=str(organization.get("name") or ""),
            )
        )

    return {
        "people": [result.intelligence for result in people_results],
        "organizations": [result.intelligence for result in organization_results],
        "review_rows": review_rows,
    }
