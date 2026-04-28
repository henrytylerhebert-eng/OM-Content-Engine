"""Constants and enums for the portfolio workflow scaffold."""

from __future__ import annotations

from enum import Enum


class DomainKey(str, Enum):
    """Approved Opportunity Machine domain anchors."""

    PROBLEM_RISK = "problem_risk"
    CUSTOMER_RISK = "customer_risk"
    MARKET_RISK = "market_risk"
    PRODUCT_RISK = "product_risk"
    TECHNICAL_RISK = "technical_risk"
    BUSINESS_MODEL_RISK = "business_model_risk"
    GO_TO_MARKET_RISK = "go_to_market_risk"
    TEAM_RISK = "team_risk"
    OPERATIONAL_RISK = "operational_risk"
    CREDIBILITY_RISK = "credibility_risk"
    FINANCIAL_READINESS_RISK = "financial_readiness_risk"
    CAPITAL_FIT_RISK = "capital_fit_risk"


class TruthStage(str, Enum):
    """Lifecycle stages for portfolio truth promotion."""

    RAW_INPUT = "raw_input"
    EXTRACTED_SIGNAL = "extracted_signal"
    INTERPRETED_EVIDENCE = "interpreted_evidence"
    REVIEWED_EVIDENCE = "reviewed_evidence"
    INTERNALLY_APPROVED_OUTPUT = "internally_approved_output"
    EXTERNALLY_APPROVED_OUTPUT = "externally_approved_output"


class ReviewStatus(str, Enum):
    """Review status applied to portfolio records."""

    PENDING_REVIEW = "pending_review"
    IN_REVIEW = "in_review"
    REVIEWED = "reviewed"
    INTERNALLY_APPROVED = "internally_approved"
    EXTERNALLY_APPROVED = "externally_approved"
    SUPPRESSED = "suppressed"


class DiscoverySourceKind(str, Enum):
    """Supported discovery source kinds for phase one."""

    AIRTABLE_RECORD = "airtable_record"
    GOOGLE_DOC = "google_doc"
    GOOGLE_FORM_RESPONSE = "google_form_response"
    GOOGLE_DRIVE_FILE = "google_drive_file"
    TRANSCRIPT = "transcript"
    MEETING_NOTE = "meeting_note"
    MANUAL_ENTRY = "manual_entry"
    SIMULATION_HYPOTHESIS = "simulation_hypothesis"


class EvidenceType(str, Enum):
    """Evidence shapes supported by the scaffold."""

    FOUNDER_CLAIM = "founder_claim"
    INTERVIEW_QUOTE = "interview_quote"
    OBSERVATION = "observation"
    METRIC = "metric"
    DOCUMENT_SIGNAL = "document_signal"
    SUPPORT_REQUEST = "support_request"


class ScoreConfidence(str, Enum):
    """Allowed confidence levels for portfolio score drafts."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class ScoreStatus(str, Enum):
    """Lifecycle status for domain score drafts."""

    DRAFT = "draft"
    REVIEW_READY = "review_ready"
    REVIEWED = "reviewed"


class ReviewSeverity(str, Enum):
    """Review queue severities."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class QueueStatus(str, Enum):
    """Workflow status for portfolio review queue items."""

    OPEN = "open"
    RESOLVED = "resolved"
    DEFERRED = "deferred"


class ReportAudience(str, Enum):
    """Target audience for report draft shells."""

    FOUNDER = "founder"
    INTERNAL = "internal"


class DraftStatus(str, Enum):
    """Lifecycle marker for draft-oriented outputs."""

    DRAFT = "draft"
    REVIEW_READY = "review_ready"
    REVIEWED = "reviewed"


class CapitalReadinessStatus(str, Enum):
    """Conservative readiness states for phase-one draft outputs."""

    NOT_YET_ASSESSED = "not_yet_assessed"
    NEEDS_REVIEW = "needs_review"
    EMERGING = "emerging"
    READY_TO_DISCUSS = "ready_to_discuss"


PORTFOLIO_QUEUE_REASON_CODES = (
    "missing_organization_link",
    "missing_source_locator",
    "missing_evidence_statement",
    "missing_primary_domain",
    "review_stage_promotion",
)

EVIDENCE_LEVELS = tuple(range(8))

OM_DOMAIN_KEYS = tuple(domain.value for domain in DomainKey)
