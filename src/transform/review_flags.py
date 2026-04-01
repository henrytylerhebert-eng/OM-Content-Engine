"""Shared review flag definitions and helpers for conservative normalization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Optional, Sequence, Union


REVIEW_FLAG_CATEGORIES = {
    "unknown_entity_type",
    "ambiguous_personnel_parse",
    "sparse_record",
    "placeholder_record",
    "duplicate_suspected",
    "invalid_cohort_parse",
    "missing_name",
    "missing_org_type",
    "internal_record_detected",
    "grouped_record_detected",
}


@dataclass(frozen=True)
class ReviewFlagDefinition:
    """Definition for a review flag emitted during normalization."""

    code: str
    category: str
    severity: str
    description: str
    recommended_action: str


@dataclass(frozen=True)
class ReviewFlag:
    """Structured review flag with enough source context for later review."""

    code: str
    category: str
    severity: str
    description: str
    recommended_action: str
    source_table: str
    source_record_id: Optional[str] = None
    source_system: Optional[str] = None
    record_label: Optional[str] = None
    source_field: Optional[str] = None
    raw_value: Optional[str] = None
    note: Optional[str] = None

    def to_queue_row(self) -> dict[str, Optional[str]]:
        """Return a flat row shape suitable for exports or local review."""

        return {
            "source_table": self.source_table,
            "source_record_id": self.source_record_id,
            "source_system": self.source_system,
            "record_label": self.record_label,
            "flag_code": self.code,
            "flag_type": self.category,
            "category": self.category,
            "severity": self.severity,
            "source_field": self.source_field,
            "raw_value": self.raw_value,
            "description": self.description,
            "recommended_action": self.recommended_action,
            "note": self.note,
        }


ReviewFlagLike = Union[str, ReviewFlag]


REVIEW_FLAG_DEFINITIONS = {
    "review_unknown_entity_type": ReviewFlagDefinition(
        code="review_unknown_entity_type",
        category="unknown_entity_type",
        severity="medium",
        description="Entity type could not be classified with confidence from the source value.",
        recommended_action="Confirm what kind of record this row represents before trusting the normalized entity type.",
    ),
    "review_missing_org_type": ReviewFlagDefinition(
        code="review_missing_org_type",
        category="missing_org_type",
        severity="medium",
        description="Organization type was missing or too weak to classify confidently.",
        recommended_action="Confirm whether the organization is a startup, partner, investor, university, service provider, internal entity, or other.",
    ),
    "review_missing_organization_name": ReviewFlagDefinition(
        code="review_missing_organization_name",
        category="missing_name",
        severity="high",
        description="No organization name was found in the source row.",
        recommended_action="Check the source columns or confirm the row should not create an organization record.",
    ),
    "review_no_person_found": ReviewFlagDefinition(
        code="review_no_person_found",
        category="missing_name",
        severity="medium",
        description="No person candidate could be extracted from the row.",
        recommended_action="Check whether the row should create a founder, mentor, staff, or contact record.",
    ),
    "review_person_missing_email": ReviewFlagDefinition(
        code="review_person_missing_email",
        category="sparse_record",
        severity="low",
        description="A person record was created without an email address.",
        recommended_action="Add or validate the best available email for matching and outreach.",
    ),
    "review_personnel_parse": ReviewFlagDefinition(
        code="review_personnel_parse",
        category="ambiguous_personnel_parse",
        severity="medium",
        description="Personnel field contains extra people that should not be trusted as a clean structured import.",
        recommended_action="Parse the personnel list manually and confirm which entries are real people and what roles they hold.",
    ),
    "review_member_side_person_multiple_candidates": ReviewFlagDefinition(
        code="review_member_side_person_multiple_candidates",
        category="ambiguous_personnel_parse",
        severity="medium",
        description="Semi-structured member-side text appears to contain more than one person candidate.",
        recommended_action="Keep the row review-first until a single named person can be confirmed from the source or reviewed truth.",
    ),
    "review_member_side_person_name_incomplete": ReviewFlagDefinition(
        code="review_member_side_person_name_incomplete",
        category="missing_name",
        severity="medium",
        description="Semi-structured member-side text did not contain one clear full-name candidate.",
        recommended_action="Use a structured name field or reviewed truth before creating a person from this row.",
    ),
    "review_member_side_person_generic_email": ReviewFlagDefinition(
        code="review_member_side_person_generic_email",
        category="sparse_record",
        severity="medium",
        description="Only a generic or role-based email was available for the semi-structured member-side person candidate.",
        recommended_action="Confirm a person-specific email before creating a person from this row.",
    ),
    "review_member_side_person_context_ambiguous": ReviewFlagDefinition(
        code="review_member_side_person_context_ambiguous",
        category="ambiguous_personnel_parse",
        severity="medium",
        description="The row did not provide one resolved organization or cohort context for a semi-structured member-side person candidate.",
        recommended_action="Resolve the row to one clear organization or cohort context before creating a person record.",
    ),
    "review_sparse_record": ReviewFlagDefinition(
        code="review_sparse_record",
        category="sparse_record",
        severity="low",
        description="The source row has very little usable information for confident normalization.",
        recommended_action="Check whether more source data exists before relying on this record downstream.",
    ),
    "review_content_profile_sparse": ReviewFlagDefinition(
        code="review_content_profile_sparse",
        category="sparse_record",
        severity="medium",
        description="The content profile is too sparse to trust for spotlights or polished external use.",
        recommended_action="Add core profile assets such as bio, headshot, website, description, expertise, or cohort history before using this record in content workflows.",
    ),
    "review_missing_content_assets": ReviewFlagDefinition(
        code="review_missing_content_assets",
        category="sparse_record",
        severity="low",
        description="The record is missing content assets that would improve a story or promotion package.",
        recommended_action="Fill in the missing content assets listed on the review row before sending the record into design or scheduling workflows.",
    ),
    "review_placeholder_record": ReviewFlagDefinition(
        code="review_placeholder_record",
        category="placeholder_record",
        severity="medium",
        description="The record appears to use placeholder text rather than a real name or label.",
        recommended_action="Replace the placeholder value with the actual record name or keep it out of normalized outputs.",
    ),
    "review_duplicate_suspected": ReviewFlagDefinition(
        code="review_duplicate_suspected",
        category="duplicate_suspected",
        severity="medium",
        description="The row appears to describe the same person more than once.",
        recommended_action="Confirm whether duplicate contacts should be merged before trusting affiliations or outreach lists.",
    ),
    "review_no_affiliation_people": ReviewFlagDefinition(
        code="review_no_affiliation_people",
        category="sparse_record",
        severity="low",
        description="No people were available to build affiliation records.",
        recommended_action="Check whether the row should produce person records before building affiliations.",
    ),
    "review_affiliation_missing_organization": ReviewFlagDefinition(
        code="review_affiliation_missing_organization",
        category="missing_name",
        severity="medium",
        description="People were found, but no organization was available for the affiliation.",
        recommended_action="Confirm whether the source row includes an organization or should stay person-only.",
    ),
    "review_missing_cohort_name": ReviewFlagDefinition(
        code="review_missing_cohort_name",
        category="missing_name",
        severity="high",
        description="No cohort name could be extracted from the row.",
        recommended_action="Check the source columns or confirm the row belongs in a different transform path.",
    ),
    "review_multi_value_cohort_parse": ReviewFlagDefinition(
        code="review_multi_value_cohort_parse",
        category="invalid_cohort_parse",
        severity="medium",
        description="Multi-value cohort field could not be safely split into clean cohort tokens.",
        recommended_action="Split the cohort values manually and remove any notes or status text before trusting the participation records.",
    ),
    "review_invalid_cohort_parse": ReviewFlagDefinition(
        code="review_invalid_cohort_parse",
        category="invalid_cohort_parse",
        severity="medium",
        description="Cohort text includes notes, delimiters, or placeholder text that cannot be trusted as a clean cohort label.",
        recommended_action="Clean the cohort value before using it to create or join participation records.",
    ),
    "review_participation_link_unresolved": ReviewFlagDefinition(
        code="review_participation_link_unresolved",
        category="missing_name",
        severity="medium",
        description="A cohort participation row could not be linked to a normalized organization or person with confidence.",
        recommended_action="Confirm the company or participant identity before creating a cohort participation record.",
    ),
    "review_mentor_location_type": ReviewFlagDefinition(
        code="review_mentor_location_type",
        category="sparse_record",
        severity="medium",
        description="Mentor location or availability text was too ambiguous to normalize confidently.",
        recommended_action="Confirm whether the mentor should be labeled local, remote, or hybrid.",
    ),
    "review_employer_organization": ReviewFlagDefinition(
        code="review_employer_organization",
        category="unknown_entity_type",
        severity="medium",
        description="Employer or organization text was not clearly a real organization record.",
        recommended_action="Confirm whether the employer value should create an organization and affiliation or stay as raw provenance only.",
    ),
    "review_missing_interaction_subject": ReviewFlagDefinition(
        code="review_missing_interaction_subject",
        category="missing_name",
        severity="high",
        description="Interaction row did not identify a person, organization, or requestor.",
        recommended_action="Confirm who or what the interaction is about before using it downstream.",
    ),
    "review_missing_interaction_date": ReviewFlagDefinition(
        code="review_missing_interaction_date",
        category="sparse_record",
        severity="medium",
        description="Interaction row did not include a usable date.",
        recommended_action="Check the source row for meeting, request, submission, or feedback timestamp fields.",
    ),
    "review_internal_record_detected": ReviewFlagDefinition(
        code="review_internal_record_detected",
        category="internal_record_detected",
        severity="low",
        description="The row appears to represent an internal Opportunity Machine record.",
        recommended_action="Confirm whether the record should stay in the intelligence layer and whether it needs to be segmented separately from external ecosystem records.",
    ),
    "review_grouped_record_detected": ReviewFlagDefinition(
        code="review_grouped_record_detected",
        category="grouped_record_detected",
        severity="medium",
        description="The row appears to describe a group, team, or collection rather than a single person.",
        recommended_action="Split the grouped record manually or keep it out of person-level outputs.",
    ),
    "review_org_type": ReviewFlagDefinition(
        code="review_org_type",
        category="missing_org_type",
        severity="medium",
        description="Legacy alias for missing or weak organization type classification.",
        recommended_action="Use `review_missing_org_type` for new code paths and confirm the correct organization type.",
    ),
}


def _value(row: Mapping[str, object], *keys: str) -> Optional[str]:
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        cleaned = str(value).strip()
        if cleaned:
            return cleaned
    return None


def _infer_record_label(row: Mapping[str, object]) -> Optional[str]:
    return _value(
        row,
        "Organization Name",
        "Company Name",
        "Member Company",
        "Startup Name",
        "Full Name",
        "Mentor Name",
        "Founder Name",
        "Primary Contact Name",
        "Contact Name",
        "Requestor Name",
        "Name",
    )


def get_review_flag_definition(code: str) -> Optional[ReviewFlagDefinition]:
    """Return the known definition for a review flag code."""

    return REVIEW_FLAG_DEFINITIONS.get(code)


def build_review_flag(
    code: str,
    *,
    source_table: str,
    row: Optional[Mapping[str, object]] = None,
    source_record_id: Optional[str] = None,
    source_system: Optional[str] = None,
    record_label: Optional[str] = None,
    source_field: Optional[str] = None,
    raw_value: Optional[object] = None,
    note: Optional[str] = None,
) -> ReviewFlag:
    """Create a structured review flag with definition and source context."""

    definition = get_review_flag_definition(code)
    if definition is None:
        definition = ReviewFlagDefinition(
            code=code,
            category="sparse_record",
            severity="medium",
            description="Unregistered review flag emitted by a transform.",
            recommended_action="Review the transform logic and add a formal flag definition if this code is expected.",
        )

    context_record_id = source_record_id or (_value(row or {}, "Record ID", "Airtable Record ID", "id"))
    context_source_system = source_system or (_value(row or {}, "Source System"))
    context_record_label = record_label or _infer_record_label(row or {})
    context_raw_value = None if raw_value is None else str(raw_value)

    return ReviewFlag(
        code=definition.code,
        category=definition.category,
        severity=definition.severity,
        description=definition.description,
        recommended_action=definition.recommended_action,
        source_table=source_table,
        source_record_id=context_record_id,
        source_system=context_source_system,
        record_label=context_record_label,
        source_field=source_field,
        raw_value=context_raw_value,
        note=note,
    )


def add_review_flag(
    flags: list[ReviewFlag],
    code: str,
    *,
    source_table: str,
    row: Optional[Mapping[str, object]] = None,
    source_record_id: Optional[str] = None,
    source_system: Optional[str] = None,
    record_label: Optional[str] = None,
    source_field: Optional[str] = None,
    raw_value: Optional[object] = None,
    note: Optional[str] = None,
) -> ReviewFlag:
    """Build a structured review flag and append it to a list."""

    flag = build_review_flag(
        code,
        source_table=source_table,
        row=row,
        source_record_id=source_record_id,
        source_system=source_system,
        record_label=record_label,
        source_field=source_field,
        raw_value=raw_value,
        note=note,
    )
    flags.append(flag)
    return flag


def review_flag_codes(flags: Sequence[ReviewFlagLike]) -> list[str]:
    """Return just the flag codes from review flags or raw flag codes."""

    return [flag.code if isinstance(flag, ReviewFlag) else str(flag) for flag in flags]


def build_review_queue_rows(
    *,
    source_table: str,
    source_record_id: Optional[str],
    flag_codes: Iterable[ReviewFlagLike],
    record_label: Optional[str] = None,
) -> list[dict[str, Optional[str]]]:
    """Convert review flags or raw codes into review queue rows."""

    rows: list[dict[str, Optional[str]]] = []
    for item in flag_codes:
        if isinstance(item, ReviewFlag):
            flag = item
        else:
            flag = build_review_flag(
                str(item),
                source_table=source_table,
                source_record_id=source_record_id,
                record_label=record_label,
            )

        row = flag.to_queue_row()
        row["source_table"] = row["source_table"] or source_table
        row["source_record_id"] = row["source_record_id"] or source_record_id
        row["record_label"] = row["record_label"] or record_label
        rows.append(row)
    return rows
