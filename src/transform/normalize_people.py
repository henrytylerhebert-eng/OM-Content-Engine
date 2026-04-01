"""Starter people and mentor normalization for messy operational source rows."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Mapping, Optional, Tuple

from src.transform.review_flags import ReviewFlag, add_review_flag


@dataclass
class PersonDraft:
    """Normalized person payload plus affiliation hints from the same row."""

    payload: dict[str, object]
    role_title: Optional[str] = None
    role_category: str = "other"
    founder_flag: bool = False
    primary_contact_flag: bool = False
    spokesperson_flag: bool = False


@dataclass
class PeopleNormalizationResult:
    """People payloads, optional mentor payload, and review flags."""

    people: list[PersonDraft] = field(default_factory=list)
    mentor_profile: Optional[dict[str, object]] = None
    review_flags: list[ReviewFlag] = field(default_factory=list)


def _value(row: Mapping[str, object], *keys: str) -> Optional[str]:
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        cleaned = str(value).strip()
        if cleaned:
            return cleaned
    return None


def _truthy(value: object) -> bool:
    if value is None:
        return False
    normalized = " ".join(str(value).strip().lower().split())
    return normalized in {
        "1",
        "true",
        "yes",
        "y",
        "active",
        "always share my email",
        "share my email",
    }


def _normalize_source_system(row: Mapping[str, object], fallback: str) -> str:
    return _value(row, "Source System") or fallback


def _looks_like_placeholder(value: Optional[str]) -> bool:
    if not value:
        return False
    lowered = " ".join(value.strip().lower().split())
    return lowered in {"tbd", "unknown", "n/a", "na", "placeholder", "test"} or lowered.startswith("tbd ")


def _looks_grouped(value: Optional[str]) -> bool:
    if not value:
        return False
    lowered = " ".join(value.strip().lower().split())
    keywords = ("team", "group", "committee", "staff", "intern", "cohort")
    return any(keyword in lowered for keyword in keywords)


GENERIC_EMAIL_LOCAL_PARTS = {
    "admin",
    "contact",
    "events",
    "founder",
    "founders",
    "hello",
    "info",
    "membership",
    "office",
    "ops",
    "operations",
    "partnerships",
    "support",
    "team",
}

MEMBER_SIDE_EMAIL_KEYS = (
    "Primary Email (from Link to Application)",
    "Primary Contact Email",
    "Founder Email",
    "Contact Email",
    "Your Email (from Participants)",
    "Email",
)

MEMBER_SIDE_ORG_KEYS = ("Company Name", "Organization Name", "Member Company", "Startup Name")


def _normalize_email(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    cleaned = value.strip().lower()
    if "@" not in cleaned:
        return None
    return cleaned


def _is_generic_email(value: Optional[str]) -> bool:
    email = _normalize_email(value)
    if not email:
        return True
    local_part = email.split("@", 1)[0]
    return local_part in GENERIC_EMAIL_LOCAL_PARTS


def _looks_like_full_name(value: Optional[str]) -> bool:
    if not value:
        return False
    cleaned = " ".join(value.strip().split())
    if _looks_grouped(cleaned) or _looks_like_placeholder(cleaned):
        return False
    tokens = cleaned.split()
    if len(tokens) < 2 or len(tokens) > 4:
        return False
    return all(re.match(r"^[A-Za-z][A-Za-z'.-]*$", token) for token in tokens)


def _extract_member_side_name_candidate(value: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Return one safe full-name candidate from Personnel or a rejection reason."""

    if not value:
        return None, None

    cleaned = " ".join(value.strip().split())
    if not cleaned:
        return None, None
    if _looks_grouped(cleaned):
        return None, "grouped"
    if any(delimiter in cleaned for delimiter in (";", "\n", " & ", " and ", " / ")):
        return None, "multiple_candidates"
    if "," in cleaned:
        return None, "multiple_candidates"

    candidate = cleaned
    for delimiter in (" - ", " | ", " ("):
        if delimiter in candidate:
            candidate = candidate.split(delimiter, 1)[0].strip()
            break

    if not _looks_like_full_name(candidate):
        if len(candidate.split()) <= 1:
            return None, "incomplete_name"
        return None, "multiple_candidates"
    return candidate, None


def _collect_unique_emails(row: Mapping[str, object], *keys: str) -> list[str]:
    seen: set[str] = set()
    emails: list[str] = []
    for key in keys:
        email = _normalize_email(_value(row, key))
        if not email or email in seen:
            continue
        seen.add(email)
        emails.append(email)
    return emails


def _collect_unique_values(row: Mapping[str, object], *keys: str) -> list[str]:
    seen: set[str] = set()
    values: list[str] = []
    for key in keys:
        value = _value(row, key)
        if not value:
            continue
        normalized = value.strip().lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        values.append(value.strip())
    return values


def _resolve_member_side_context(row: Mapping[str, object]) -> Tuple[Optional[str], Optional[str]]:
    """Return one safe org or cohort context label, or a reason to review."""

    org_values = _collect_unique_values(row, *MEMBER_SIDE_ORG_KEYS)
    if len(org_values) > 1:
        return None, "multiple_org_context"
    if len(org_values) == 1:
        return org_values[0], None

    cohort_value = _value(row, "Cohort", "Cohort Name", "Builder Cohort")
    if not cohort_value:
        return None, "missing_context"
    if any(delimiter in cohort_value for delimiter in (";", "\n")) or "," in cohort_value:
        return None, "multiple_cohort_context"
    return cohort_value.strip(), None


def _split_tags(*values: object) -> Optional[str]:
    tags: list[str] = []
    for value in values:
        if not value:
            continue
        text = str(value).replace(";", ",")
        for part in text.split(","):
            cleaned = part.strip()
            if cleaned and cleaned.lower() not in {tag.lower() for tag in tags}:
                tags.append(cleaned)
    return ", ".join(tags) if tags else None


def _active_flag(row: Mapping[str, object]) -> bool:
    status = _value(row, "Status", "Active Status")
    if status:
        return status.strip().lower() not in {"inactive", "former", "withdrawn"}
    active_value = _value(row, "Active")
    if active_value is not None:
        return _truthy(active_value)
    return True


def _person_ready_flags(
    row: Mapping[str, object],
    person_type: str,
) -> Tuple[bool, bool, bool]:
    explicit_public = _value(row, "Public Facing Ready")
    explicit_speaker = _value(row, "Speaker Ready")
    explicit_content = _value(row, "Content Ready")

    bio = _value(row, "Bio")
    linkedin = _value(row, "LinkedIn", "Linkedin")
    headshot = _value(row, "Headshot URL", "Headshot")
    public_ready = _truthy(explicit_public) if explicit_public is not None else bool(bio or linkedin or headshot)
    speaker_ready = _truthy(explicit_speaker) if explicit_speaker is not None else person_type == "mentor"
    content_ready = _truthy(explicit_content) if explicit_content is not None else public_ready
    return public_ready, speaker_ready, content_ready


def _person_payload(
    row: Mapping[str, object],
    *,
    full_name: str,
    email: Optional[str],
    person_type: str,
    source_system: str,
    person_resolution_basis: str = "structured_field",
) -> dict[str, object]:
    public_ready, speaker_ready, content_ready = _person_ready_flags(row, person_type)
    expertise_tags = _split_tags(
        _value(row, "Expertise", "Area of Expertise", "Expertise Tags", "Skills"),
        "AI" if _truthy(_value(row, "AI Expertise")) else None,
    )

    return {
        "full_name": full_name,
        "email": email,
        "linkedin": _value(row, "LinkedIn Profile", "LinkedIn", "Linkedin"),
        "bio": _value(row, "Bio"),
        "headshot_url": _value(row, "Headshot URL", "Headshot"),
        "location": _value(row, "Location", "Mailing Address", "City", "Headquarters"),
        "timezone": _value(row, "Timezone", "Time Zone"),
        "person_type": person_type,
        "expertise_tags": expertise_tags,
        "public_facing_ready": public_ready,
        "speaker_ready": speaker_ready,
        "content_ready": content_ready,
        "active_flag": _active_flag(row),
        "person_resolution_basis": person_resolution_basis,
        "source_record_id": _value(row, "Record ID", "Airtable Record ID", "id"),
        "source_system": _normalize_source_system(row, source_system),
    }


def _append_candidate(
    drafts: list[PersonDraft],
    row: Mapping[str, object],
    *,
    name_key: str,
    email_key: Optional[str],
    role_title: Optional[str],
    role_category: str,
    person_type: str,
    founder_flag: bool = False,
    primary_contact_flag: bool = False,
    spokesperson_flag: bool = False,
    source_system: str,
    person_resolution_basis: str = "structured_field",
) -> None:
    full_name = _value(row, name_key)
    if not full_name:
        return
    email = _value(row, email_key) if email_key else None
    drafts.append(
        PersonDraft(
            payload=_person_payload(
                row,
                full_name=full_name,
                email=email,
                person_type=person_type,
                source_system=source_system,
                person_resolution_basis=person_resolution_basis,
            ),
            role_title=role_title,
            role_category=role_category,
            founder_flag=founder_flag,
            primary_contact_flag=primary_contact_flag,
            spokesperson_flag=spokesperson_flag,
        )
    )


def _try_append_member_side_person_from_personnel(
    drafts: list[PersonDraft],
    flags: list[ReviewFlag],
    row: Mapping[str, object],
    *,
    source_table: str,
    source_system: str,
) -> bool:
    """Create one member-side person from Personnel only when exact dual-signal evidence exists."""

    personnel_value = _value(row, "Personnel")
    if not personnel_value:
        return False

    candidate_name, rejection_reason = _extract_member_side_name_candidate(personnel_value)
    if candidate_name is None:
        if rejection_reason in {"grouped", "multiple_candidates"}:
            add_review_flag(
                flags,
                "review_personnel_parse",
                source_table=source_table,
                row=row,
                source_system=source_system,
                source_field="Personnel",
                raw_value=personnel_value,
            )
        if rejection_reason == "grouped":
            add_review_flag(
                flags,
                "review_grouped_record_detected",
                source_table=source_table,
                row=row,
                source_system=source_system,
                source_field="Personnel",
                raw_value=personnel_value,
            )
        elif rejection_reason == "multiple_candidates":
            add_review_flag(
                flags,
                "review_member_side_person_multiple_candidates",
                source_table=source_table,
                row=row,
                source_system=source_system,
                source_field="Personnel",
                raw_value=personnel_value,
            )
        elif rejection_reason == "incomplete_name":
            add_review_flag(
                flags,
                "review_member_side_person_name_incomplete",
                source_table=source_table,
                row=row,
                source_system=source_system,
                source_field="Personnel",
                raw_value=personnel_value,
            )
        return False

    unique_emails = _collect_unique_emails(row, *MEMBER_SIDE_EMAIL_KEYS)
    if len(unique_emails) != 1:
        add_review_flag(
            flags,
            "review_member_side_person_context_ambiguous",
            source_table=source_table,
            row=row,
            source_system=source_system,
            source_field="Email",
            raw_value=" | ".join(unique_emails) if unique_emails else "",
            note="Semi-structured member-side path needs exactly one unique email.",
        )
        return False
    if _is_generic_email(unique_emails[0]):
        add_review_flag(
            flags,
            "review_member_side_person_generic_email",
            source_table=source_table,
            row=row,
            source_system=source_system,
            source_field="Email",
            raw_value=unique_emails[0],
        )
        return False

    context_label, context_reason = _resolve_member_side_context(row)
    if context_label is None:
        org_values = _collect_unique_values(row, *MEMBER_SIDE_ORG_KEYS)
        cohort_values = _collect_unique_values(row, "Cohort", "Cohort Name", "Builder Cohort")
        raw_context = " | ".join(
            org_values + cohort_values
        )
        add_review_flag(
            flags,
            "review_member_side_person_context_ambiguous",
            source_table=source_table,
            row=row,
            source_system=source_system,
            source_field="Company Name" if context_reason == "multiple_org_context" else "Cohort",
            raw_value=raw_context,
            note="Semi-structured member-side path needs one resolved organization or cohort context.",
        )
        return False

    drafts.append(
        PersonDraft(
            payload=_person_payload(
                row,
                full_name=candidate_name,
                email=unique_emails[0],
                person_type="operator",
                source_system=source_system,
                person_resolution_basis="semi_structured_member_side",
            ),
            role_title="Member Contact",
            role_category="other",
        )
    )
    return True


def _dedupe_people(drafts: list[PersonDraft]) -> list[PersonDraft]:
    seen: set[str] = set()
    unique: list[PersonDraft] = []
    for draft in drafts:
        payload = draft.payload
        dedupe_key = (
            str(payload.get("email") or "").strip().lower()
            or str(payload.get("full_name") or "").strip().lower()
        )
        if not dedupe_key or dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        unique.append(draft)
    return unique


def _infer_mentor_location_type(row: Mapping[str, object]) -> Optional[str]:
    explicit = _value(row, "Mentor Location Type", "Mentor Location", "Location Type", "Availability")
    if explicit:
        lowered = explicit.lower()
        if "hybrid" in lowered:
            return "hybrid"
        if "remote" in lowered or "virtual" in lowered:
            return "remote"
        if "local" in lowered or "in-person" in lowered:
            return "local"
    if _value(row, "Location", "Mailing Address", "City", "State"):
        return "local"
    return None


def normalize_people_from_row(
    row: Mapping[str, object],
    source_table: str,
    source_system: str = "airtable_export",
) -> PeopleNormalizationResult:
    """Create first-pass people payloads from a raw source row.

    Structured founder, primary-contact, and mentor fields are trusted first.
    Active-member Personnel text only creates a person when there is exactly one
    clear full-name candidate, one unique non-generic email, and one resolved
    organization or cohort context in the same row.
    """

    drafts: list[PersonDraft] = []
    flags: list[ReviewFlag] = []

    _append_candidate(
        drafts,
        row,
        name_key="Founder Name",
        email_key="Founder Email",
        role_title="Founder",
        role_category="founder",
        person_type="founder",
        founder_flag=True,
        spokesperson_flag=True,
        source_system=source_system,
    )
    _append_candidate(
        drafts,
        row,
        name_key="Primary Contact Name",
        email_key="Primary Contact Email",
        role_title="Primary Contact",
        role_category="executive",
        person_type="operator",
        primary_contact_flag=True,
        spokesperson_flag=True,
        source_system=source_system,
    )

    if source_table == "Mentors" or _value(row, "Mentor Name"):
        _append_candidate(
            drafts,
            row,
            name_key="Mentor Name" if _value(row, "Mentor Name") else "Full Name" if _value(row, "Full Name") else "Name",
            email_key="Email",
            role_title="Mentor",
            role_category="mentor",
            person_type="mentor",
            source_system=source_system,
        )

    if source_table == "Personnel":
        _append_candidate(
            drafts,
            row,
            name_key="Full Name" if _value(row, "Full Name") else "Name",
            email_key="Email",
            role_title=_value(row, "Title", "Role") or "Staff",
            role_category="staff",
            person_type="staff",
            source_system=source_system,
        )

    if not drafts:
        _append_candidate(
            drafts,
            row,
            name_key="Contact Name",
            email_key="Contact Email",
            role_title="Contact",
            role_category="other",
            person_type="other",
            source_system=source_system,
        )

    if not drafts and source_table == "Active Members":
        _try_append_member_side_person_from_personnel(
            drafts,
            flags,
            row,
            source_table=source_table,
            source_system=source_system,
        )

    if not drafts and _value(row, "Full Name", "Name"):
        generic_name = "Full Name" if _value(row, "Full Name") else "Name"
        default_type = "mentor" if source_table == "Mentors" else "staff" if source_table == "Personnel" else "other"
        _append_candidate(
            drafts,
            row,
            name_key=generic_name,
            email_key="Email",
            role_title=_value(row, "Title", "Role"),
            role_category="staff" if default_type == "staff" else "other",
            person_type=default_type,
            source_system=source_system,
        )

    if _value(row, "Personnel"):
        personnel_value = _value(row, "Personnel")
        # Extra personnel text stays review-first when structured people already
        # exist, or when the conservative single-person rule does not apply.
        if drafts and not any(
            draft.payload.get("person_resolution_basis") == "semi_structured_member_side"
            for draft in drafts
        ):
            add_review_flag(
                flags,
                "review_personnel_parse",
                source_table=source_table,
                row=row,
                source_system=source_system,
                source_field="Personnel",
                raw_value=personnel_value,
            )
        existing_flag_codes = {flag.code for flag in flags}
        if _looks_grouped(personnel_value) and "review_grouped_record_detected" not in existing_flag_codes:
            add_review_flag(
                flags,
                "review_grouped_record_detected",
                source_table=source_table,
                row=row,
                source_system=source_system,
                source_field="Personnel",
                raw_value=personnel_value,
            )

    draft_count_before_dedupe = len(drafts)
    drafts = _dedupe_people(drafts)
    if draft_count_before_dedupe > len(drafts):
        add_review_flag(
            flags,
            "review_duplicate_suspected",
            source_table=source_table,
            row=row,
            source_system=source_system,
            source_field="Founder Name",
            raw_value="%s | %s"
            % (_value(row, "Founder Name"), _value(row, "Primary Contact Name")),
            note="More than one person candidate collapsed to the same dedupe key.",
        )
    if not drafts:
        add_review_flag(
            flags,
            "review_no_person_found",
            source_table=source_table,
            row=row,
            source_system=source_system,
        )
    if any(not draft.payload.get("email") for draft in drafts):
        add_review_flag(
            flags,
            "review_person_missing_email",
            source_table=source_table,
            row=row,
            source_system=source_system,
            source_field="Email",
        )
    if any(_looks_like_placeholder(str(draft.payload.get("full_name") or "")) for draft in drafts):
        placeholder_name = next(
            (
                str(draft.payload.get("full_name") or "")
                for draft in drafts
                if _looks_like_placeholder(str(draft.payload.get("full_name") or ""))
            ),
            None,
        )
        add_review_flag(
            flags,
            "review_placeholder_record",
            source_table=source_table,
            row=row,
            source_system=source_system,
            source_field="Name",
            raw_value=placeholder_name,
        )
    if any(_looks_grouped(str(draft.payload.get("full_name") or "")) for draft in drafts):
        grouped_name = next(
            (
                str(draft.payload.get("full_name") or "")
                for draft in drafts
                if _looks_grouped(str(draft.payload.get("full_name") or ""))
            ),
            None,
        )
        add_review_flag(
            flags,
            "review_grouped_record_detected",
            source_table=source_table,
            row=row,
            source_system=source_system,
            source_field="Name",
            raw_value=grouped_name,
        )

    mentor_profile: Optional[dict[str, object]] = None
    mentor_draft = next((draft for draft in drafts if draft.payload["person_type"] == "mentor"), None)
    if mentor_draft:
        mentor_location_type = _infer_mentor_location_type(row)
        if (
            source_table == "Mentors"
            and _value(row, "Mentor Location Type", "Mentor Location", "Location Type", "Availability")
            and mentor_location_type is None
        ):
            add_review_flag(
                flags,
                "review_mentor_location_type",
                source_table=source_table,
                row=row,
                source_system=source_system,
                source_field="Mentor Location",
                raw_value=_value(row, "Mentor Location Type", "Mentor Location", "Location Type", "Availability"),
            )
        mentor_profile = {
            "person_id": None,
            "mentor_program_type": _value(row, "Mentor Program Type", "Program", "Program Type"),
            "mentor_location_type": mentor_location_type,
            "expertise_summary": _split_tags(
                mentor_draft.payload.get("expertise_tags"),
                _value(row, "Expertise Summary"),
            ),
            "share_email_permission": _truthy(_value(row, "Share Email Permission", "Share Email", "Share Email?")),
            "booking_link": _value(
                row,
                "Accelerator Meeting Request",
                "Incubator Meeting Request",
                "Booking Link",
                "Calendar Link",
                "Meeting Request Link",
                "Meeting Request Links",
            ),
            "mentor_active_flag": bool(mentor_draft.payload.get("active_flag")),
            "source_record_id": mentor_draft.payload.get("source_record_id"),
            "source_system": mentor_draft.payload.get("source_system"),
        }

    return PeopleNormalizationResult(people=drafts, mentor_profile=mentor_profile, review_flags=flags)
