"""Starter cohort and participation normalization."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from calendar import monthrange
from typing import Mapping, Optional

from src.transform.review_flags import ReviewFlag, add_review_flag


@dataclass
class ParticipationNormalizationResult:
    """Program, cohort, and participation payloads plus review flags."""

    program: Optional[dict[str, object]] = None
    cohort: Optional[dict[str, object]] = None
    participation: Optional[dict[str, object]] = None
    review_flags: list[ReviewFlag] = field(default_factory=list)


@dataclass
class ParticipationBatchNormalizationResult:
    """Multiple cohort and participation payloads from one explicit cohort row."""

    programs: list[dict[str, object]] = field(default_factory=list)
    cohorts: list[dict[str, object]] = field(default_factory=list)
    participations: list[dict[str, object]] = field(default_factory=list)
    review_flags: list[ReviewFlag] = field(default_factory=list)


SEASON_MONTH_RANGES = {
    "spring": (1, 5),
    "summer": (6, 8),
    "fall": (9, 12),
    "winter": (12, 12),
}

MONTH_NUMBERS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

COHORT_STATUS_OVERRIDES = {
    "dropout": "withdrawn",
    "withdrawn": "withdrawn",
    "alumni": "alumni",
    "active": "active",
    "pending": "pending",
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


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    cleaned = value.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    try:
        return date.fromisoformat(cleaned)
    except ValueError:
        return None


def _normalize_text(value: Optional[str]) -> str:
    if not value:
        return ""
    return " ".join(value.strip().lower().split())


def _strip_program_prefix(value: Optional[str]) -> str:
    text = " ".join((value or "").strip().split())
    lowered = text.lower()
    for prefix in ("builder ", "accelerator ", "mentor "):
        if lowered.startswith(prefix):
            return text[len(prefix) :].strip()
    return text


def _parse_temporal_window_from_cohort_name(cohort_name: Optional[str]) -> tuple[Optional[date], Optional[date]]:
    cleaned = _strip_program_prefix(cohort_name)
    if not cleaned:
        return None, None

    parts = cleaned.split()
    if len(parts) == 2 and parts[0].lower() in SEASON_MONTH_RANGES and parts[1].isdigit():
        year = int(parts[1])
        start_month, end_month = SEASON_MONTH_RANGES[parts[0].lower()]
        start_year = year
        end_year = year
        if parts[0].lower() == "winter":
            start_year = year - 1
        start = date(start_year, start_month, 1)
        end = date(end_year, end_month, monthrange(end_year, end_month)[1])
        return start, end

    if len(parts) == 2 and parts[0].lower() in MONTH_NUMBERS and parts[1].isdigit():
        year = int(parts[1])
        month = MONTH_NUMBERS[parts[0].lower()]
        return date(year, month, 1), date(year, month, monthrange(year, month)[1])

    return None, None


def _infer_program_name(
    row: Mapping[str, object],
    cohort_name: Optional[str],
    *,
    source_table: str,
) -> Optional[str]:
    explicit = _value(row, "Program Name", "Program")
    if explicit:
        return explicit
    if source_table == "Cohorts" and any(
        _value(row, field)
        for field in ("Miro Link", "Customer Discovery Link", "Customer Discovery Tracker", "Welcome Email")
    ):
        return "Builder"
    if not cohort_name:
        return None
    lowered = _normalize_text(cohort_name)
    if "builder" in lowered:
        return "Builder"
    if "accelerator" in lowered:
        return "Accelerator"
    if "mentor" in lowered:
        return "Mentor"
    return cohort_name


def _infer_program_type(program_name: Optional[str]) -> Optional[str]:
    if not program_name:
        return None
    lowered = program_name.lower()
    if "builder" in lowered:
        return "builder"
    if "accelerator" in lowered:
        return "accelerator"
    if "mentor" in lowered:
        return "mentor"
    return "community"


def _normalize_status(
    row: Mapping[str, object],
    end_date: Optional[date],
    *,
    status_override: Optional[str] = None,
) -> str:
    if status_override:
        return status_override
    explicit = _value(row, "Participation Status", "Status")
    if explicit:
        lowered = explicit.lower()
        if lowered in {"active", "alumni", "pending", "withdrawn", "unknown"}:
            return lowered
    if end_date and end_date < date.today():
        return "alumni"
    return "active"


def _looks_invalid_cohort_value(value: Optional[str]) -> bool:
    if not value:
        return False
    lowered = " ".join(value.strip().lower().split())
    return lowered in {"tbd", "unknown", "n/a", "na"} or "pending" in lowered


def _split_cohort_tokens(value: Optional[str]) -> list[str]:
    if not value:
        return []
    normalized = value.replace(";", ",").replace("\n", ",")
    return [part.strip() for part in normalized.split(",") if part.strip()]


def _extract_cohort_labels_and_status(
    value: Optional[str],
    *,
    allow_multiple_labels: bool,
) -> tuple[list[str], Optional[str], Optional[str], Optional[str]]:
    """Split one cohort cell into labels plus an optional status override.

    Returns labels, status_override, error_code, and an optional note.
    """

    tokens = _split_cohort_tokens(value)
    labels: list[str] = []
    status_values: set[str] = set()
    invalid_tokens: list[str] = []

    for token in tokens:
        normalized_token = " ".join(token.strip().split())
        lowered = _normalize_text(normalized_token)
        if lowered in COHORT_STATUS_OVERRIDES:
            status_values.add(COHORT_STATUS_OVERRIDES[lowered])
            continue
        if _is_explicit_cohort_label(normalized_token):
            labels.append(normalized_token)
            continue
        invalid_tokens.append(normalized_token)

    if invalid_tokens:
        return [], None, "invalid", "These tokens did not look like safe cohort labels or known status markers: %s." % ", ".join(
            invalid_tokens
        )
    if not labels:
        return [], None, "invalid", "No usable cohort label remained after separating known status markers."
    if len(status_values) > 1:
        return [], None, "invalid", "More than one status marker was present in the same cohort cell."

    status_override = next(iter(status_values)) if status_values else None
    if not allow_multiple_labels and len(labels) > 1:
        return labels, status_override, "multiple_labels", "This row still contains more than one cohort label."
    if allow_multiple_labels and len(labels) > 1 and status_override is not None:
        return (
            labels,
            status_override,
            "ambiguous_status_across_labels",
            "A single status marker could not be safely assigned across multiple cohort labels.",
        )
    return labels, status_override, None, None


def _is_explicit_cohort_label(value: str) -> bool:
    lowered = _normalize_text(_strip_program_prefix(value))
    if not lowered:
        return False
    if lowered == "individual track":
        return True
    parts = lowered.split()
    if len(parts) == 2 and parts[0] in SEASON_MONTH_RANGES and parts[1].isdigit():
        return True
    if len(parts) == 2 and parts[0] in MONTH_NUMBERS and parts[1].isdigit():
        return True
    return "cohort" in lowered


def _build_normalized_participation_payloads(
    row: Mapping[str, object],
    *,
    source_table: str,
    source_system: str,
    cohort_name: str,
    status_override: Optional[str] = None,
) -> ParticipationNormalizationResult:
    program_name = _infer_program_name(row, cohort_name, source_table=source_table)
    program_type = _infer_program_type(program_name)
    start_date = _parse_date(_value(row, "Start Date"))
    end_date = _parse_date(_value(row, "End Date"))
    if start_date is None and end_date is None:
        start_date, end_date = _parse_temporal_window_from_cohort_name(cohort_name)
    active_flag = end_date is None or end_date >= date.today()
    source_record_id = _value(row, "Record ID", "Airtable Record ID", "id")
    source_system_value = _value(row, "Source System") or source_system
    notes = _value(row, "Notes", "Feedback", "Membership History")

    program = {
        "program_name": program_name,
        "program_type": program_type,
        "active_flag": active_flag,
        "source_record_id": source_record_id,
        "source_system": source_system_value,
    }
    cohort = {
        "cohort_name": cohort_name,
        "program_id": None,
        "start_date": start_date,
        "end_date": end_date,
        "active_flag": active_flag,
        "source_record_id": source_record_id,
        "source_system": source_system_value,
    }
    participation = {
        "person_id": None,
        "organization_id": None,
        "cohort_id": None,
        "cohort_name": cohort_name,
        "participation_status": _normalize_status(row, end_date, status_override=status_override),
        "notes": notes,
        "source_record_id": source_record_id,
        "source_system": source_system_value,
    }
    return ParticipationNormalizationResult(program=program, cohort=cohort, participation=participation)


def normalize_participation_row(
    row: Mapping[str, object],
    source_table: str,
    source_system: str = "airtable_export",
) -> ParticipationNormalizationResult:
    """Create program, cohort, and participation payloads from a raw row.

    The current implementation only trusts one clean cohort token per row.
    Multi-value cohort cells are sent to review instead of being split in-place.
    """

    flags: list[ReviewFlag] = []
    cohort_name = _value(row, "Cohort Name", "Cohort", "Builder Cohort", "Name")
    if not cohort_name:
        add_review_flag(
            flags,
            "review_missing_cohort_name",
            source_table=source_table,
            row=row,
            source_system=source_system,
            source_field="Cohort",
        )
        return ParticipationNormalizationResult(review_flags=flags)
    if _looks_invalid_cohort_value(cohort_name):
        add_review_flag(
            flags,
            "review_invalid_cohort_parse",
            source_table=source_table,
            row=row,
            source_system=source_system,
            source_field="Cohort",
            raw_value=cohort_name,
        )
        return ParticipationNormalizationResult(review_flags=flags)
    labels, status_override, error_code, note = _extract_cohort_labels_and_status(
        cohort_name,
        allow_multiple_labels=False,
    )
    if error_code == "multiple_labels":
        add_review_flag(
            flags,
            "review_multi_value_cohort_parse",
            source_table=source_table,
            row=row,
            source_system=source_system,
            source_field="Cohort",
            raw_value=cohort_name,
            note=note,
        )
        return ParticipationNormalizationResult(review_flags=flags)
    if error_code is not None:
        add_review_flag(
            flags,
            "review_invalid_cohort_parse",
            source_table=source_table,
            row=row,
            source_system=source_system,
            source_field="Cohort",
            raw_value=cohort_name,
            note=note,
        )
        return ParticipationNormalizationResult(review_flags=flags)

    result = _build_normalized_participation_payloads(
        row,
        source_table=source_table,
        source_system=source_system,
        cohort_name=labels[0],
        status_override=status_override,
    )
    result.review_flags = flags
    return result


def normalize_explicit_cohort_row(
    row: Mapping[str, object],
    source_table: str,
    source_system: str = "airtable_export",
) -> ParticipationBatchNormalizationResult:
    """Normalize one explicit cohort export row into one or more cohort links.

    The explicit `Cohorts` export is allowed to split multiple clean cohort labels
    from the same row. Status tokens like `Dropout` are treated as participation
    status overrides rather than extra cohort names.
    """

    flags: list[ReviewFlag] = []
    cohort_value = _value(row, "Cohort", "Cohort Name", "Builder Cohort", "Name")
    if not cohort_value:
        add_review_flag(
            flags,
            "review_missing_cohort_name",
            source_table=source_table,
            row=row,
            source_system=source_system,
            source_field="Cohort",
        )
        return ParticipationBatchNormalizationResult(review_flags=flags)
    if _looks_invalid_cohort_value(cohort_value):
        add_review_flag(
            flags,
            "review_invalid_cohort_parse",
            source_table=source_table,
            row=row,
            source_system=source_system,
            source_field="Cohort",
            raw_value=cohort_value,
        )
        return ParticipationBatchNormalizationResult(review_flags=flags)

    labels, status_override, error_code, note = _extract_cohort_labels_and_status(
        cohort_value,
        allow_multiple_labels=True,
    )
    if error_code is not None:
        add_review_flag(
            flags,
            "review_invalid_cohort_parse",
            source_table=source_table,
            row=row,
            source_system=source_system,
            source_field="Cohort",
            raw_value=cohort_value,
            note=note,
        )
        return ParticipationBatchNormalizationResult(review_flags=flags)

    programs: list[dict[str, object]] = []
    cohorts: list[dict[str, object]] = []
    participations: list[dict[str, object]] = []
    seen_program_names: set[str] = set()
    seen_cohort_names: set[str] = set()

    for label in labels:
        normalized = _build_normalized_participation_payloads(
            row,
            source_table=source_table,
            source_system=source_system,
            cohort_name=label,
            status_override=status_override,
        )
        if normalized.program is not None:
            program_name = str(normalized.program.get("program_name") or "")
            if program_name not in seen_program_names:
                seen_program_names.add(program_name)
                programs.append(normalized.program)
        if normalized.cohort is not None:
            cohort_name = str(normalized.cohort.get("cohort_name") or "")
            if cohort_name not in seen_cohort_names:
                seen_cohort_names.add(cohort_name)
                cohorts.append(normalized.cohort)
        if normalized.participation is not None:
            participations.append(normalized.participation)

    return ParticipationBatchNormalizationResult(
        programs=programs,
        cohorts=cohorts,
        participations=participations,
        review_flags=flags,
    )
