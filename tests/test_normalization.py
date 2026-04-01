"""Bootstrap-focused tests for first-pass normalization behavior."""

from src.models.affiliation import Affiliation
from src.models.cohort import Cohort
from src.models.interaction import Interaction
from src.models.mentor_profile import MentorProfile
from src.models.organization import Organization
from src.models.participation import Participation
from src.models.person import Person
from src.models.program import Program
from src.reporting.segments import (
    build_active_founder_segment,
    build_content_ready_people_segment,
    build_local_ai_mentor_segment,
)
from src.transform.normalize_affiliations import normalize_affiliations_from_row
from src.transform.normalize_interactions import normalize_interaction_row
from src.transform.normalize_organizations import normalize_organization_row
from src.transform.normalize_participation import normalize_explicit_cohort_row, normalize_participation_row
from src.transform.normalize_people import normalize_people_from_row
from src.transform.review_flags import build_review_queue_rows, review_flag_codes
from tests.fixtures.pilot_rows import (
    ACTIVE_MEMBER_GROUPED_PERSONNEL_ROW,
    ACTIVE_MEMBER_INTERNAL_ROW,
    ACTIVE_MEMBER_MULTI_COHORT_ROW,
    ACTIVE_MEMBER_PARTNER_ROW,
    ACTIVE_MEMBER_SEMI_STRUCTURED_FIRST_NAME_ROW,
    ACTIVE_MEMBER_SEMI_STRUCTURED_GENERIC_EMAIL_ROW,
    ACTIVE_MEMBER_SEMI_STRUCTURED_MULTI_CONTEXT_ROW,
    ACTIVE_MEMBER_SEMI_STRUCTURED_SINGLE_ROW,
    ACTIVE_MEMBER_SPARSE_ROW,
    ACTIVE_MEMBER_STARTUP_ROW,
    AMBIGUOUS_MEMBER_ROW,
    COHORT_ROW,
    COHORT_EXPORT_DELTA_ROW,
    CONNECTION_ROW,
    MENTOR_ROW,
    MENTOR_SPARSE_ROW,
)


def test_mixed_member_row_splits_into_org_people_and_affiliations() -> None:
    row = ACTIVE_MEMBER_STARTUP_ROW

    org_result = normalize_organization_row(row, source_table="Active Members")
    people_result = normalize_people_from_row(row, source_table="Active Members")
    affiliation_result = normalize_affiliations_from_row(
        row,
        source_table="Active Members",
        people=people_result.people,
        organization=org_result.organization,
    )

    assert org_result.organization is not None
    assert org_result.organization["name"] == "Acme AI"
    assert org_result.organization["org_type"] == "startup"
    assert org_result.organization["source_record_id"] == "rec_member_001"
    assert len(people_result.people) == 2
    assert len(affiliation_result.affiliations) == 2

    founder = people_result.people[0]
    contact = people_result.people[1]
    assert founder.payload["person_type"] == "founder"
    assert contact.payload["person_type"] == "operator"
    assert founder.payload["person_resolution_basis"] == "structured_field"
    assert contact.payload["person_resolution_basis"] == "structured_field"

    Organization(**org_result.organization)
    Person(**founder.payload)
    Person(**contact.payload)
    Affiliation(**affiliation_result.affiliations[0])


def test_mentor_row_creates_person_and_mentor_profile() -> None:
    row = MENTOR_ROW

    people_result = normalize_people_from_row(row, source_table="Mentors")

    assert len(people_result.people) == 1
    assert people_result.mentor_profile is not None
    assert people_result.people[0].payload["person_type"] == "mentor"
    assert people_result.mentor_profile["mentor_location_type"] == "local"
    assert people_result.mentor_profile["share_email_permission"] is True
    assert people_result.people[0].payload["source_record_id"] == "rec_mentor_001"

    Person(**people_result.people[0].payload)
    MentorProfile(**people_result.mentor_profile)


def test_partner_member_row_maps_to_partner_organization() -> None:
    result = normalize_organization_row(ACTIVE_MEMBER_PARTNER_ROW, source_table="Active Members")

    assert result.organization is not None
    assert result.organization["org_type"] == "partner"
    assert result.organization["name"] == "Gulf Coast Manufacturing Network"
    assert result.review_flags == []


def test_grouped_personnel_field_stays_review_first() -> None:
    result = normalize_people_from_row(
        ACTIVE_MEMBER_GROUPED_PERSONNEL_ROW,
        source_table="Active Members",
    )
    flag_codes = review_flag_codes(result.review_flags)

    assert len(result.people) == 2
    assert "review_personnel_parse" in flag_codes
    assert "review_grouped_record_detected" in flag_codes


def test_valid_dual_signal_member_side_person_is_created_conservatively() -> None:
    result = normalize_people_from_row(
        ACTIVE_MEMBER_SEMI_STRUCTURED_SINGLE_ROW,
        source_table="Active Members",
    )

    assert len(result.people) == 1
    assert result.people[0].payload["full_name"] == "Morgan Rivers"
    assert result.people[0].payload["email"] == "morgan@signalworks.example"
    assert result.people[0].payload["person_type"] == "operator"
    assert result.people[0].payload["person_resolution_basis"] == "semi_structured_member_side"
    assert result.review_flags == []


def test_multi_person_member_side_personnel_stays_review_only() -> None:
    row = {
        "Record ID": "rec_member_semi_multi_001",
        "Company Name": "Signal Works",
        "Membership Status": "Active",
        "Personnel": "Morgan Rivers - CEO; Jamie Wells - COO",
        "Primary Email (from Link to Application)": "morgan@signalworks.example",
    }

    result = normalize_people_from_row(row, source_table="Active Members")
    flag_codes = review_flag_codes(result.review_flags)

    assert result.people == []
    assert "review_personnel_parse" in flag_codes
    assert "review_member_side_person_multiple_candidates" in flag_codes
    assert "review_no_person_found" in flag_codes


def test_first_name_only_member_side_person_candidate_stays_review_only() -> None:
    result = normalize_people_from_row(
        ACTIVE_MEMBER_SEMI_STRUCTURED_FIRST_NAME_ROW,
        source_table="Active Members",
    )
    flag_codes = review_flag_codes(result.review_flags)

    assert result.people == []
    assert "review_member_side_person_name_incomplete" in flag_codes
    assert "review_no_person_found" in flag_codes


def test_generic_email_member_side_person_candidate_stays_review_only() -> None:
    result = normalize_people_from_row(
        ACTIVE_MEMBER_SEMI_STRUCTURED_GENERIC_EMAIL_ROW,
        source_table="Active Members",
    )
    flag_codes = review_flag_codes(result.review_flags)

    assert result.people == []
    assert "review_member_side_person_generic_email" in flag_codes
    assert "review_no_person_found" in flag_codes


def test_multi_context_member_side_person_candidate_stays_review_only() -> None:
    result = normalize_people_from_row(
        ACTIVE_MEMBER_SEMI_STRUCTURED_MULTI_CONTEXT_ROW,
        source_table="Active Members",
    )
    flag_codes = review_flag_codes(result.review_flags)

    assert result.people == []
    assert "review_member_side_person_context_ambiguous" in flag_codes
    assert "review_no_person_found" in flag_codes


def test_sparse_active_member_row_is_flagged_for_review() -> None:
    result = normalize_organization_row(ACTIVE_MEMBER_SPARSE_ROW, source_table="Active Members")
    flag_codes = review_flag_codes(result.review_flags)

    assert result.organization is not None
    assert result.organization["org_type"] == "unknown"
    assert "review_org_type" in flag_codes
    assert "review_sparse_record" in flag_codes


def test_internal_member_row_is_classified_and_flagged() -> None:
    result = normalize_organization_row(ACTIVE_MEMBER_INTERNAL_ROW, source_table="Active Members")
    flag_codes = review_flag_codes(result.review_flags)

    assert result.organization is not None
    assert result.organization["org_type"] == "internal"
    assert "review_internal_record_detected" in flag_codes


def test_cohort_row_maps_to_program_cohort_and_participation() -> None:
    row = COHORT_ROW

    result = normalize_participation_row(row, source_table="Cohorts")

    assert result.program is not None
    assert result.cohort is not None
    assert result.participation is not None
    assert result.program["program_name"] == "Builder"
    assert result.cohort["cohort_name"] == "Builder Spring 2026"
    assert result.participation["participation_status"] == "active"
    assert result.participation["source_record_id"] == "rec_cohort_001"

    Program(**result.program)
    Cohort(**result.cohort)
    Participation(**result.participation)


def test_multi_cohort_member_row_is_sent_to_review_for_manual_split() -> None:
    result = normalize_participation_row(
        ACTIVE_MEMBER_MULTI_COHORT_ROW,
        source_table="Active Members",
    )
    flag_codes = review_flag_codes(result.review_flags)

    assert result.program is None
    assert result.cohort is None
    assert result.participation is None
    assert "review_multi_value_cohort_parse" in flag_codes


def test_explicit_cohort_export_row_splits_multiple_cohorts() -> None:
    result = normalize_explicit_cohort_row(COHORT_EXPORT_DELTA_ROW, source_table="Cohorts")

    assert len(result.programs) == 1
    assert result.programs[0]["program_name"] == "Builder"
    assert [cohort["cohort_name"] for cohort in result.cohorts] == ["Spring 2025", "Fall 2025"]
    assert len(result.participations) == 2
    assert result.participations[0]["participation_status"] == "alumni"
    assert result.participations[1]["participation_status"] == "alumni"
    assert result.review_flags == []


def test_explicit_cohort_export_row_converts_dropout_to_withdrawn() -> None:
    row = {
        "Company Name": "Example Startup",
        "Cohort": "Fall 2025,Dropout",
        "Miro Link": "https://miro.example.com/example",
        "Primary Email (from Link to Application)": "founder@example.com",
    }

    result = normalize_explicit_cohort_row(row, source_table="Cohorts")

    assert len(result.cohorts) == 1
    assert result.cohorts[0]["cohort_name"] == "Fall 2025"
    assert len(result.participations) == 1
    assert result.participations[0]["participation_status"] == "withdrawn"


def test_active_member_cohort_value_splits_status_from_identity_when_safe() -> None:
    row = {
        "Record ID": "rec_member_status_001",
        "Company Name": "Signal Works",
        "Cohort": "Fall 2025,Dropout",
        "Program Name": "Builder",
    }

    result = normalize_participation_row(row, source_table="Active Members")

    assert result.review_flags == []
    assert result.cohort is not None
    assert result.participation is not None
    assert result.cohort["cohort_name"] == "Fall 2025"
    assert result.participation["cohort_name"] == "Fall 2025"
    assert result.participation["participation_status"] == "withdrawn"


def test_explicit_cohort_row_with_multiple_labels_and_one_status_stays_review_first() -> None:
    row = {
        "Company Name": "Signal Works",
        "Cohort": "Spring 2025,Fall 2025,Dropout",
        "Miro Link": "https://miro.example.com/signal",
    }

    result = normalize_explicit_cohort_row(row, source_table="Cohorts")
    flag_codes = review_flag_codes(result.review_flags)

    assert result.cohorts == []
    assert result.participations == []
    assert "review_invalid_cohort_parse" in flag_codes


def test_ambiguous_row_is_flagged_instead_of_force_classified() -> None:
    row = AMBIGUOUS_MEMBER_ROW

    result = normalize_organization_row(row, source_table="Active Members")
    flag_codes = review_flag_codes(result.review_flags)

    assert result.organization is not None
    assert result.organization["org_type"] == "unknown"
    assert "review_org_type" in flag_codes


def test_connection_row_maps_to_interaction() -> None:
    result = normalize_interaction_row(CONNECTION_ROW, source_table="Connections")

    assert len(result.interactions) == 1
    assert result.interactions[0]["interaction_type"] == "connection"
    assert result.review_flags == []

    Interaction(**result.interactions[0])


def test_sparse_mentor_row_keeps_person_and_flags_missing_email() -> None:
    people_result = normalize_people_from_row(MENTOR_SPARSE_ROW, source_table="Mentors")
    flag_codes = review_flag_codes(people_result.review_flags)

    assert len(people_result.people) == 1
    assert people_result.people[0].payload["full_name"] == "Jordan Sparse"
    assert "review_person_missing_email" in flag_codes


def test_active_member_alias_fields_map_to_expected_targets() -> None:
    row = {
        "Record ID": "rec_member_alias_001",
        "Company Name": "Signal Works",
        "Member Type": "Startup",
        "Membership Status": "Active",
        "Confirmed Membership Level": "Builder Plus",
        "Website": "https://signalworks.example",
    }

    result = normalize_organization_row(row, source_table="Active Members")

    assert result.organization is not None
    assert result.organization["membership_status"] == "active"
    assert result.organization["membership_tier"] == "Builder Plus"
    assert result.organization["website"] == "https://signalworks.example"


def test_active_member_airtable_export_alias_fields_map_to_expected_targets() -> None:
    row = {
        "Company Name": "A&H Ammunition",
        "Membership Status (from Application Link)": "Active",
        "Confirmed Membership Level": "Standard",
        "Company Website (from Link to Application)": "https://www.ahammunition.com/",
        "Provide below a one to two sentence description of who your business serves/what you do. (from Link to Application)": "Manufacturing and ammunition brokering services.",
    }

    result = normalize_organization_row(row, source_table="Active Members")

    assert result.organization is not None
    assert result.organization["membership_status"] == "active"
    assert result.organization["membership_tier"] == "Standard"
    assert result.organization["website"] == "https://www.ahammunition.com/"
    assert result.organization["description"] == "Manufacturing and ammunition brokering services."


def test_membership_level_standard_defaults_to_startup() -> None:
    row = {
        "Company Name": "Signal Works",
        "Confirmed Membership Level": "Standard",
        "Membership Status (from Application Link)": "Active",
    }

    result = normalize_organization_row(row, source_table="Active Members")

    assert result.organization is not None
    assert result.organization["org_type"] == "startup"


def test_partner_membership_level_stays_partner_without_stronger_override() -> None:
    row = {
        "Company Name": "Acadiana Software Group",
        "Confirmed Membership Level": "Partner",
        "Membership Status (from Application Link)": "Active",
    }

    result = normalize_organization_row(row, source_table="Active Members")

    assert result.organization is not None
    assert result.organization["org_type"] == "partner"


def test_government_org_type_can_be_derived_from_name_and_domain() -> None:
    row = {
        "Company Name": "Louisiana Economic Development",
        "Confirmed Membership Level": "Partner",
        "Company Website (from Link to Application)": "https://www.opportunitylouisiana.gov",
    }

    result = normalize_organization_row(row, source_table="Active Members")

    assert result.organization is not None
    assert result.organization["org_type"] == "government"


def test_university_org_type_can_be_derived_from_name() -> None:
    row = {
        "Company Name": "UL Lafayette",
        "Confirmed Membership Level": "Partner",
    }

    result = normalize_organization_row(row, source_table="Active Members")

    assert result.organization is not None
    assert result.organization["org_type"] == "university"


def test_adventure_name_does_not_trigger_investor_classification() -> None:
    row = {
        "Company Name": "AdventureGo",
        "Confirmed Membership Level": "Standard",
        "Membership Status (from Application Link)": "Active",
        "Accessible Space": "1 Shared Desk",
        "Cohort": "Summer 2024",
        "Provide below a one to two sentence description of who your business serves/what you do. (from Link to Application)": "Travel planning and local discovery app.",
    }

    result = normalize_organization_row(row, source_table="Active Members")

    assert result.organization is not None
    assert result.organization["org_type"] == "startup"


def test_archangel_name_does_not_trigger_investor_classification_without_investment_context() -> None:
    row = {
        "Company Name": "Archangel Dominion, LLC",
        "Confirmed Membership Level": "Standard",
        "Membership Status (from Application Link)": "Active",
        "Accessible Space": "1 Shared Desk",
        "Provide below a one to two sentence description of who your business serves/what you do. (from Link to Application)": "Software and server resources for local companies and nonprofits.",
    }

    result = normalize_organization_row(row, source_table="Active Members")

    assert result.organization is not None
    assert result.organization["org_type"] == "startup"


def test_generic_investment_language_does_not_force_investor_classification() -> None:
    row = {
        "Company Name": "Mother Honey",
        "Confirmed Membership Level": "Standard",
        "Membership Status (from Application Link)": "Active",
        "Accessible Space": "1 Shared Desk",
        "Provide below a one to two sentence description of who your business serves/what you do. (from Link to Application)": "Workplace wellness workshops with a strong ROI for employers already making a mental health investment.",
    }

    result = normalize_organization_row(row, source_table="Active Members")

    assert result.organization is not None
    assert result.organization["org_type"] == "startup"


def test_mentor_alias_fields_map_to_expected_person_and_profile() -> None:
    row = {
        "Record ID": "rec_mentor_alias_001",
        "Name": "Rae Mentor",
        "Email": "rae@example.com",
        "Area of Expertise": "AI; Product Strategy",
        "Mailing Address": "Baton Rouge, LA",
        "Mentor Location": "Remote",
        "Time Zone": "America/Chicago",
        "Share Email?": "yes",
        "Meeting Request Link": "https://calendar.example.com/rae",
        "Program": "Builder",
        "Status": "Active",
    }

    result = normalize_people_from_row(row, source_table="Mentors")

    assert len(result.people) == 1
    assert result.people[0].payload["full_name"] == "Rae Mentor"
    assert result.people[0].payload["expertise_tags"] == "AI, Product Strategy"
    assert result.people[0].payload["location"] == "Baton Rouge, LA"
    assert result.people[0].payload["timezone"] == "America/Chicago"
    assert result.mentor_profile is not None
    assert result.mentor_profile["mentor_program_type"] == "Builder"
    assert result.mentor_profile["mentor_location_type"] == "remote"
    assert result.mentor_profile["share_email_permission"] is True
    assert result.mentor_profile["booking_link"] == "https://calendar.example.com/rae"


def test_mentor_airtable_export_alias_fields_map_to_expected_targets() -> None:
    row = {
        "Name": "Theresa Test",
        "Area of Expertise": "test Area of Expertise",
        "Email": "theresa@example.com",
        "Bio": "test bio",
        "LinkedIn Profile": "https://www.linkedin.com/in/theresagoldkamp/",
        "Mailing Address": "test Mailing Address",
        "Accelerator Meeting Request": "https://airtable.com/shrcGlzQ8nkE1v068",
        "Share Email?": "Always share my email",
        "Time Zone": "CT",
        "Status": "Active",
    }

    result = normalize_people_from_row(row, source_table="Mentors")

    assert len(result.people) == 1
    assert result.people[0].payload["linkedin"] == "https://www.linkedin.com/in/theresagoldkamp/"
    assert result.people[0].payload["location"] == "test Mailing Address"
    assert result.people[0].payload["timezone"] == "CT"
    assert result.people[0].payload["expertise_tags"] == "test Area of Expertise"
    assert result.mentor_profile is not None
    assert result.mentor_profile["share_email_permission"] is True
    assert result.mentor_profile["booking_link"] == "https://airtable.com/shrcGlzQ8nkE1v068"


def test_placeholder_person_record_is_flagged_for_review() -> None:
    row = {
        "Record ID": "rec_mentor_placeholder_001",
        "Name": "TBD Mentor",
        "Email": "placeholder@example.com",
        "Status": "Active",
    }

    result = normalize_people_from_row(row, source_table="Mentors")
    flag_codes = review_flag_codes(result.review_flags)

    assert len(result.people) == 1
    assert "review_placeholder_record" in flag_codes


def test_review_queue_rows_include_severity_and_action() -> None:
    rows = build_review_queue_rows(
        source_table="Active Members",
        source_record_id="rec_ambiguous_001",
        flag_codes=["review_org_type"],
        record_label="Community Network",
    )

    assert len(rows) == 1
    assert rows[0]["severity"] == "medium"
    assert rows[0]["flag_code"] == "review_org_type"
    assert rows[0]["recommended_action"] is not None


def test_segment_outputs_cover_founders_mentors_and_content_ready_people() -> None:
    founder_people = normalize_people_from_row(ACTIVE_MEMBER_STARTUP_ROW, source_table="Active Members").people
    mentor_result = normalize_people_from_row(MENTOR_ROW, source_table="Mentors")

    people_payloads = [draft.payload for draft in founder_people] + [draft.payload for draft in mentor_result.people]
    mentor_profiles = [mentor_result.mentor_profile] if mentor_result.mentor_profile else []

    founder_segment = build_active_founder_segment(people_payloads)
    mentor_segment = build_local_ai_mentor_segment(people_payloads, mentor_profiles)
    content_ready_segment = build_content_ready_people_segment(people_payloads)

    assert len(founder_segment) == 1
    assert founder_segment[0]["full_name"] == "Jane Founder"
    assert len(mentor_segment) == 1
    assert mentor_segment[0]["full_name"] == "Morgan Guide"
    assert any(person["full_name"] == "Morgan Guide" for person in content_ready_segment)
