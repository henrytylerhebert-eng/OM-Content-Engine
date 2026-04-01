"""Starter organization normalization for messy operational source rows."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Mapping, Optional
from urllib.parse import urlparse

from src.transform.review_flags import ReviewFlag, add_review_flag


@dataclass
class OrganizationNormalizationResult:
    """Normalized organization payload plus review flags."""

    organization: Optional[dict[str, object]]
    review_flags: list[ReviewFlag] = field(default_factory=list)


PARTNER_MEMBERSHIP_LEVELS = {"partner"}
STARTUP_MEMBERSHIP_LEVELS = {"standard", "build", "momentum"}


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
    return str(value).strip().lower() in {"1", "true", "yes", "y", "active"}


def _normalize_source_system(row: Mapping[str, object], fallback: str) -> str:
    return _value(row, "Source System") or fallback


def _normalize_membership_status(row: Mapping[str, object], source_table: str) -> Optional[str]:
    status = _value(
        row,
        "Membership Status",
        "Membership Status (from Application Link)",
        "Status",
        "Active Status",
    )
    if status:
        return status.strip().lower().replace(" ", "_")
    if source_table in {"Active Members", "Member Companies"}:
        return "active"
    return None


def _normalize_text(value: Optional[str]) -> str:
    if not value:
        return ""
    return " ".join(value.strip().lower().split())


def _normalized_membership_tier(row: Mapping[str, object]) -> Optional[str]:
    value = _value(row, "Membership Tier", "Confirmed Membership Level", "Tier")
    if not value:
        return None
    return _normalize_text(value)


def _looks_like_placeholder(value: Optional[str]) -> bool:
    if not value:
        return False
    lowered = _normalize_text(value)
    return lowered in {"tbd", "unknown", "n/a", "na", "placeholder", "test"} or lowered.startswith("tbd ")


def _website_host(row: Mapping[str, object]) -> str:
    website = _value(
        row,
        "Website",
        "Company Website",
        "Company Website (from Link to Application)",
    )
    if not website:
        return ""
    lowered = _normalize_text(website)
    if lowered in {"n/a", "na", "none", "none yet", "tbd"}:
        return ""
    candidate = website if "://" in website else "https://%s" % website
    parsed = urlparse(candidate)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _organization_text(row: Mapping[str, object]) -> str:
    parts = [
        _value(row, "Organization Name", "Company Name", "Member Company", "Startup Name", "Name"),
        _value(
            row,
            "Description",
            "Company Description",
            "Provide below a one to two sentence description of who your business serves/what you do. (from Link to Application)",
        ),
        _website_host(row),
    ]
    return " | ".join(part for part in parts if part)


def _matches_any(text: str, patterns: tuple[str, ...]) -> bool:
    lowered = _normalize_text(text)
    return any(pattern in lowered for pattern in patterns)


def _matches_regex_any(text: str, patterns: tuple[str, ...]) -> bool:
    lowered = _normalize_text(text)
    return any(re.search(pattern, lowered) is not None for pattern in patterns)


def _looks_internal(name: str, website_host: str) -> bool:
    return _matches_any(name, ("opportunity machine",)) or "opportunitymachine" in website_host


def _looks_university(name: str, website_host: str) -> bool:
    return (
        _matches_any(name, ("university", "college", "community college", "school of", "ul lafayette"))
        or website_host.endswith(".edu")
    )


def _looks_government(name: str, website_host: str, description: str) -> bool:
    return (
        website_host.endswith(".gov")
        or _matches_any(name, ("louisiana economic development", "department of", "office of", "city of", "parish"))
        or _matches_any(description, ("state agency", "economic development agency"))
    )


def _looks_nonprofit(name: str, website_host: str, description: str) -> bool:
    return (
        _matches_any(name, ("foundation", "association", "alliance", "coalition", "chamber"))
        or (
            website_host.endswith(".org")
            and _matches_any(description, ("mission statement", "service organization", "workforce initiatives", "nonprofit"))
        )
    )


def _looks_investor(name: str, website_host: str, description: str) -> bool:
    investor_name_patterns = (
        r"\bcapital\b",
        r"\bventures?\b",
        r"\bangel\b",
        r"\bfund\b",
    )
    investor_description_patterns = (
        "investor",
        "investment firm",
        "investment fund",
        "investment research",
        "venture capital",
        "angel investor",
        "deal sourcing",
        "deal diligence",
        "portfolio company",
        "private equity",
    )
    has_investor_name_signal = _matches_regex_any(name, investor_name_patterns)
    has_investor_description_signal = _matches_any(description, investor_description_patterns)
    return website_host.endswith(".vc") or has_investor_description_signal or (
        has_investor_name_signal and has_investor_description_signal
    )


def _looks_mentor_org(name: str, description: str) -> bool:
    return _matches_any(name, ("mentor network", "mentorship network")) or _matches_any(
        description,
        ("mentor network", "mentorship network", "mentor matching"),
    )


def _looks_service_provider(name: str, description: str) -> bool:
    strong_name_patterns = (
        "consulting",
        "legal",
        " law ",
        "financial planning",
        "advisors",
        "advisory",
        "insurance",
        "marketing",
        "creative",
        "notary",
        "billing",
    )
    strong_description_patterns = (
        "consulting",
        "legal services",
        "notarial services",
        "financial planning",
        "wealth management",
        "public relations",
        "marketing firm",
        "insurance",
        "medical billing",
    )
    normalized_name = " %s " % _normalize_text(name)
    normalized_description = _normalize_text(description)
    return any(pattern in normalized_name for pattern in strong_name_patterns) or any(
        pattern in normalized_description for pattern in strong_description_patterns
    )


def _has_startup_membership_signal(row: Mapping[str, object]) -> bool:
    membership_tier = _normalized_membership_tier(row)
    if membership_tier in STARTUP_MEMBERSHIP_LEVELS:
        return True
    if _value(row, "Accessible Space"):
        return True
    if _value(row, "Cohort", "Builder Cohort", "2.0 Cohort"):
        return True
    if _value(row, "Application Date", "Link to Application"):
        return True
    return False


def _is_sparse_organization_row(row: Mapping[str, object]) -> bool:
    context_fields = (
        ("Website", "Company Website"),
        ("Description", "Company Description"),
        ("Industry", "Sector"),
        ("Stage", "Company Stage"),
        ("Headquarters", "Location", "City"),
        ("Founder Name",),
        ("Founder Email",),
        ("Primary Contact Name",),
        ("Primary Contact Email",),
        ("Personnel",),
        ("Builder Cohort", "Cohort", "Cohort Name"),
    )
    populated = 0
    for keys in context_fields:
        if _value(row, *keys):
            populated += 1
    return populated <= 1


def _infer_org_type(
    row: Mapping[str, object],
    source_table: str,
    flags: list[ReviewFlag],
    *,
    source_system: str,
) -> str:
    explicit = _value(
        row,
        "Organization Type",
        "Org Type",
        "Member Type",
        "Category",
        "Company Type",
    )
    normalized = (explicit or "").strip().lower()

    explicit_map = {
        "startup": "startup",
        "startup company": "startup",
        "member company": "startup",
        "partner": "partner",
        "partner organization": "partner",
        "investor": "investor",
        "mentor org": "mentor_org",
        "mentor organization": "mentor_org",
        "mentor network": "mentor_org",
        "vc": "investor",
        "venture capital": "investor",
        "angel": "investor",
        "university": "university",
        "college": "university",
        "government": "government",
        "public sector": "government",
        "nonprofit": "nonprofit",
        "service provider": "service_provider",
        "service organization": "service_provider",
        "internal": "internal",
        "staff": "internal",
        "other": "other",
        "unknown": "unknown",
    }
    if normalized in explicit_map:
        return explicit_map[normalized]

    name = _value(row, "Organization Name", "Company Name", "Member Company", "Startup Name", "Name") or ""
    description = _value(
        row,
        "Description",
        "Company Description",
        "Provide below a one to two sentence description of who your business serves/what you do. (from Link to Application)",
    ) or ""
    website_host = _website_host(row)
    membership_tier = _normalized_membership_tier(row)

    if source_table == "Personnel":
        return "internal"
    if _looks_internal(name, website_host):
        return "internal"
    if _looks_government(name, website_host, description):
        return "government"
    if _looks_university(name, website_host):
        return "university"
    if _looks_investor(name, website_host, description):
        return "investor"
    if _looks_nonprofit(name, website_host, description):
        return "nonprofit"
    if _looks_mentor_org(name, description):
        return "mentor_org"
    if _looks_service_provider(name, description):
        return "service_provider"
    if membership_tier in PARTNER_MEMBERSHIP_LEVELS:
        return "partner"
    if _has_startup_membership_signal(row):
        return "startup"
    if source_table == "Member Companies":
        return "startup"

    add_review_flag(
        flags,
        "review_org_type",
        source_table=source_table,
        row=row,
        source_system=source_system,
        source_field="Member Type",
        raw_value=explicit or membership_tier or _organization_text(row),
        note="Organization type fell back to 'unknown' because the source value and operational context were too weak.",
    )
    return "unknown"


def normalize_organization_row(
    row: Mapping[str, object],
    source_table: str,
    source_system: str = "airtable_export",
) -> OrganizationNormalizationResult:
    """Create a first-pass organization payload from a raw source row.

    Active Members stays organization-first. Contact and cohort data are optional
    sidecars and should not block organization creation when the company or
    organization name is present.
    """

    flags: list[ReviewFlag] = []
    name = _value(
        row,
        "Organization Name",
        "Company Name",
        "Member Company",
        "Startup Name",
        "Employer",
        "Organization",
        "Name",
    )
    if not name:
        add_review_flag(
            flags,
            "review_missing_organization_name",
            source_table=source_table,
            row=row,
            source_system=source_system,
            source_field="Company Name",
        )
        return OrganizationNormalizationResult(organization=None, review_flags=flags)

    membership_status = _normalize_membership_status(row, source_table)
    active_flag = membership_status not in {"inactive", "former", "withdrawn"}
    if _value(row, "Active") is not None:
        active_flag = _truthy(_value(row, "Active"))

    org_type = _infer_org_type(row, source_table, flags, source_system=source_system)
    if _looks_like_placeholder(name):
        add_review_flag(
            flags,
            "review_placeholder_record",
            source_table=source_table,
            row=row,
            source_system=source_system,
            source_field="Company Name",
            raw_value=name,
        )
    if org_type == "internal":
        add_review_flag(
            flags,
            "review_internal_record_detected",
            source_table=source_table,
            row=row,
            source_system=source_system,
            source_field="Member Type",
            raw_value=_value(row, "Organization Type", "Org Type", "Member Type", "Category", "Company Type"),
        )
    if _is_sparse_organization_row(row):
        add_review_flag(
            flags,
            "review_sparse_record",
            source_table=source_table,
            row=row,
            source_system=source_system,
            note="Organization landed with very little supporting context beyond its name.",
        )
    content_eligible = org_type in {
        "startup",
        "partner",
        "investor",
        "university",
        "mentor_org",
        "service_provider",
        "government",
        "nonprofit",
    }
    spotlight_priority = 50 if org_type == "startup" else 25 if content_eligible else 0

    payload = {
        "name": name,
        "org_type": org_type,
        "membership_status": membership_status,
        "membership_tier": _value(row, "Membership Tier", "Confirmed Membership Level", "Tier"),
        "website": _value(
            row,
            "Website",
            "Company Website",
            "Company Website (from Link to Application)",
        ),
        "description": _value(
            row,
            "Description",
            "Company Description",
            "Provide below a one to two sentence description of who your business serves/what you do. (from Link to Application)",
        ),
        "industry": _value(row, "Industry", "Sector"),
        "stage": _value(row, "Stage", "Company Stage"),
        "headquarters_location": _value(row, "Headquarters", "Location", "City"),
        "active_flag": active_flag,
        "source_record_id": _value(row, "Record ID", "Airtable Record ID", "id"),
        "source_system": _normalize_source_system(row, source_system),
        "content_eligible": content_eligible,
        "spotlight_priority": spotlight_priority,
    }
    return OrganizationNormalizationResult(organization=payload, review_flags=flags)
