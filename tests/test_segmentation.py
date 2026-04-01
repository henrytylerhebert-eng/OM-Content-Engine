"""Tests for the first-pass ecosystem segmentation layer."""

from src.enrich.ecosystem_segments import (
    build_segment_bundle,
    segment_active_mentors,
    segment_active_startup_members,
    segment_alumni_founders,
    segment_content_ready_organizations,
    segment_content_ready_people,
    segment_current_cohort_founders,
    segment_internal_records,
    segment_local_mentors,
    segment_non_local_mentors,
    segment_partner_organizations,
    segment_review_needed_records,
)


def test_organization_segments_cover_startups_and_partners() -> None:
    organizations = [
        {"id": 1, "name": "Acme AI", "org_type": "startup", "active_flag": True},
        {"id": 2, "name": "Gulf Partner", "org_type": "partner", "active_flag": True},
        {"id": 3, "name": "UL Lafayette", "org_type": "university", "membership_tier": "Partner", "active_flag": True},
        {"id": 4, "name": "Dormant Startup", "org_type": "startup", "active_flag": False},
    ]

    startup_segment = segment_active_startup_members(organizations)
    partner_segment = segment_partner_organizations(organizations)

    assert [record["name"] for record in startup_segment] == ["Acme AI"]
    assert [record["name"] for record in partner_segment] == ["Gulf Partner", "UL Lafayette"]


def test_mentor_segments_split_active_local_and_non_local() -> None:
    people = [
        {"id": 10, "full_name": "Morgan Local", "person_type": "mentor", "active_flag": True},
        {"id": 11, "full_name": "Taylor Remote", "person_type": "mentor", "active_flag": True},
        {"id": 12, "full_name": "Jamie Inactive", "person_type": "mentor", "active_flag": False},
    ]
    mentor_profiles = [
        {"person_id": 10, "mentor_active_flag": True, "mentor_location_type": "local"},
        {"person_id": 11, "mentor_active_flag": True, "mentor_location_type": "remote"},
        {"person_id": 12, "mentor_active_flag": True, "mentor_location_type": "local"},
    ]

    active_mentors = segment_active_mentors(people, mentor_profiles)
    local_mentors = segment_local_mentors(people, mentor_profiles)
    non_local_mentors = segment_non_local_mentors(people, mentor_profiles)

    assert [record["full_name"] for record in active_mentors] == ["Morgan Local", "Taylor Remote"]
    assert [record["full_name"] for record in local_mentors] == ["Morgan Local"]
    assert [record["full_name"] for record in non_local_mentors] == ["Taylor Remote"]


def test_founder_segments_use_affiliations_participation_and_cohorts() -> None:
    people = [
        {"id": 20, "full_name": "Priya Current", "person_type": "founder", "active_flag": True},
        {"id": 21, "full_name": "Alex Alumni", "person_type": "founder", "active_flag": True},
    ]
    affiliations = [
        {"person_id": 20, "organization_id": 100, "founder_flag": True},
        {"person_id": 21, "organization_id": 101, "founder_flag": True},
    ]
    cohorts = [
        {"id": 200, "cohort_name": "Builder Spring 2026", "active_flag": True},
        {"id": 201, "cohort_name": "Builder Fall 2024", "active_flag": False},
    ]
    participations = [
        {"organization_id": 100, "cohort_id": 200, "participation_status": "active"},
        {"organization_id": 101, "cohort_id": 201, "participation_status": "alumni"},
    ]

    current_founders = segment_current_cohort_founders(people, affiliations, participations, cohorts)
    alumni_founders = segment_alumni_founders(people, affiliations, participations, cohorts)

    assert [record["full_name"] for record in current_founders] == ["Priya Current"]
    assert [record["full_name"] for record in alumni_founders] == ["Alex Alumni"]


def test_internal_and_content_ready_segments_are_rule_based() -> None:
    organizations = [
        {
            "id": 1,
            "name": "OM Internal",
            "org_type": "internal",
            "active_flag": True,
            "content_eligible": False,
            "spotlight_priority": 0,
        },
        {
            "id": 2,
            "name": "Spotlight Startup",
            "org_type": "startup",
            "active_flag": True,
            "content_eligible": True,
            "spotlight_priority": 50,
        },
    ]
    people = [
        {"id": 30, "full_name": "Staff Person", "person_type": "staff", "active_flag": True, "content_ready": False},
        {"id": 31, "full_name": "Story Founder", "person_type": "founder", "active_flag": True, "content_ready": True},
    ]

    internal_records = segment_internal_records(organizations, people)
    content_orgs = segment_content_ready_organizations(organizations)
    content_people = segment_content_ready_people(people)

    assert len(internal_records) == 2
    assert [record["name"] for record in content_orgs] == ["Spotlight Startup"]
    assert [record["full_name"] for record in content_people] == ["Story Founder"]


def test_review_needed_segment_returns_review_rows() -> None:
    review_rows = [
        {"flag_code": "review_missing_org_type", "source_table": "Active Members", "source_record_id": "rec_1"},
        {"flag_code": "review_person_missing_email", "source_table": "Mentors", "source_record_id": "rec_2"},
    ]

    result = segment_review_needed_records(review_rows)

    assert len(result) == 2
    assert result[0]["flag_code"] == "review_missing_org_type"


def test_segment_bundle_is_reporting_friendly() -> None:
    organizations = [
        {
            "id": 1,
            "name": "Acme AI",
            "org_type": "startup",
            "active_flag": True,
            "content_eligible": True,
            "spotlight_priority": 50,
        },
        {"id": 2, "name": "Partner Org", "org_type": "partner", "active_flag": True},
    ]
    people = [
        {"id": 10, "full_name": "Morgan Local", "person_type": "mentor", "active_flag": True, "content_ready": True},
        {"id": 11, "full_name": "Priya Founder", "person_type": "founder", "active_flag": True, "content_ready": True},
        {"id": 12, "full_name": "Staff Person", "person_type": "staff", "active_flag": True, "content_ready": False},
    ]
    mentor_profiles = [{"person_id": 10, "mentor_active_flag": True, "mentor_location_type": "local"}]
    affiliations = [{"person_id": 11, "organization_id": 1, "founder_flag": True}]
    cohorts = [{"id": 200, "cohort_name": "Builder Spring 2026", "active_flag": True}]
    participations = [{"organization_id": 1, "cohort_id": 200, "participation_status": "active"}]
    review_rows = [{"flag_code": "review_missing_org_type", "source_table": "Active Members", "source_record_id": "rec_1"}]

    bundle = build_segment_bundle(
        organizations=organizations,
        people_payloads=people,
        mentor_profiles=mentor_profiles,
        affiliations=affiliations,
        participations=participations,
        cohorts=cohorts,
        review_rows=review_rows,
    )

    assert bundle["active_startup_members"]["count"] == 1
    assert bundle["local_mentors"]["count"] == 1
    assert bundle["current_cohort_founders"]["count"] == 1
    assert bundle["review_needed_records"]["count"] == 1
    assert "rule" in bundle["content_ready_people"]
