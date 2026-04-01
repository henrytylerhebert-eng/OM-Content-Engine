"""Tests for the first-pass content intelligence layer."""

import json

from src.enrich.content_intelligence import (
    build_content_intelligence_bundle,
    build_organization_content_intelligence,
    build_person_content_intelligence,
)
from src.models.content_intelligence import ContentIntelligence
from src.review.reviewed_truth import apply_content_bundle_overrides, load_override_document


def test_founder_with_assets_and_cohort_history_is_spotlight_ready() -> None:
    founder = {
        "id": 1,
        "full_name": "Priya Founder",
        "person_type": "founder",
        "active_flag": True,
        "bio": "Founder building an AI operations startup.",
        "headshot_url": "https://example.com/priya.jpg",
        "linkedin": "https://linkedin.com/in/priya",
        "location": "Lafayette, LA",
        "source_record_id": "rec_founder_001",
        "source_system": "airtable_export",
    }
    organization = {
        "id": 10,
        "name": "Acme AI",
        "org_type": "startup",
        "active_flag": True,
        "website": "https://acme.ai",
        "description": "Workflow software for industrial teams.",
    }
    affiliations = [{"person_id": 1, "organization_id": 10, "founder_flag": True, "spokesperson_flag": True}]
    cohorts = [{"id": 100, "cohort_name": "Builder Spring 2026", "active_flag": True}]
    participations = [{"organization_id": 10, "cohort_id": 100, "participation_status": "active"}]

    result = build_person_content_intelligence(
        founder,
        affiliations=affiliations,
        organizations=[organization],
        participations=participations,
        cohorts=cohorts,
    )

    assert result.intelligence["content_eligible"] is True
    assert result.intelligence["internally_usable"] is True
    assert result.intelligence["content_ready"] is True
    assert result.intelligence["founder_story_candidate"] is True
    assert result.intelligence["ecosystem_proof_candidate"] is True
    assert result.intelligence["spotlight_ready"] is True
    assert result.intelligence["externally_publishable"] is False
    assert result.review_flags == []

    ContentIntelligence(**result.intelligence)


def test_sparse_founder_generates_content_review_flags() -> None:
    founder = {
        "full_name": "Sparse Founder",
        "person_type": "founder",
        "active_flag": True,
        "source_record_id": "rec_founder_002",
        "source_system": "airtable_export",
    }

    result = build_person_content_intelligence(founder)
    flag_codes = [flag.code for flag in result.review_flags]

    assert result.intelligence["content_eligible"] is True
    assert result.intelligence["internally_usable"] is False
    assert result.intelligence["content_ready"] is False
    assert result.intelligence["spotlight_ready"] is False
    assert result.intelligence["externally_publishable"] is False
    assert "bio" in str(result.intelligence["missing_content_assets"])
    assert "review_content_profile_sparse" in flag_codes
    assert "review_missing_content_assets" in flag_codes


def test_operator_can_be_internally_usable_without_being_content_ready() -> None:
    operator = {
        "id": 7,
        "full_name": "Dana Operator",
        "person_type": "operator",
        "active_flag": True,
        "email": "dana@example.com",
        "source_record_id": "rec_operator_001",
        "source_system": "airtable_export",
    }

    result = build_person_content_intelligence(operator)
    flag_codes = [flag.code for flag in result.review_flags]

    assert result.intelligence["content_eligible"] is True
    assert result.intelligence["internally_usable"] is True
    assert result.intelligence["content_ready"] is False
    assert result.intelligence["spotlight_ready"] is False
    assert result.intelligence["externally_publishable"] is False
    assert "review_content_profile_sparse" in flag_codes


def test_founder_can_be_content_ready_without_being_spotlight_ready() -> None:
    founder = {
        "id": 8,
        "full_name": "Taylor Founder",
        "person_type": "founder",
        "active_flag": True,
        "bio": "Founder building workflow tools for local operators.",
        "location": "Lafayette, LA",
        "source_record_id": "rec_founder_003",
        "source_system": "airtable_export",
    }

    result = build_person_content_intelligence(founder)

    assert result.intelligence["content_eligible"] is True
    assert result.intelligence["internally_usable"] is True
    assert result.intelligence["content_ready"] is True
    assert result.intelligence["spotlight_ready"] is False
    assert result.intelligence["externally_publishable"] is False


def test_mentor_feature_candidate_can_still_show_missing_assets() -> None:
    mentor = {
        "id": 2,
        "full_name": "Morgan Mentor",
        "person_type": "mentor",
        "active_flag": True,
        "bio": "AI mentor for startup founders.",
        "linkedin": "https://linkedin.com/in/morgan",
        "expertise_tags": "AI, Go-to-market",
        "location": "Lafayette, LA",
        "speaker_ready": True,
        "source_record_id": "rec_mentor_010",
        "source_system": "airtable_export",
    }

    result = build_person_content_intelligence(mentor)

    assert result.intelligence["content_eligible"] is True
    assert result.intelligence["internally_usable"] is True
    assert result.intelligence["content_ready"] is True
    assert result.intelligence["mentor_story_candidate"] is True
    assert result.intelligence["spokesperson_candidate"] is True
    assert result.intelligence["spotlight_ready"] is True
    assert result.intelligence["externally_publishable"] is False
    assert "headshot" in str(result.intelligence["missing_content_assets"])


def test_partner_organization_with_assets_becomes_ecosystem_proof_candidate() -> None:
    partner = {
        "id": 20,
        "name": "Gulf South Innovation Hub",
        "org_type": "partner",
        "active_flag": True,
        "description": "Regional innovation partner supporting founders.",
        "website": "https://gulfinnovation.org",
        "industry": "Ecosystem Support",
        "headquarters_location": "Lafayette, LA",
        "source_record_id": "rec_partner_001",
        "source_system": "airtable_export",
    }
    people = [{"full_name": "Dana Partner", "public_facing_ready": True}]

    result = build_organization_content_intelligence(partner, affiliated_people=people)

    assert result.intelligence["content_eligible"] is True
    assert result.intelligence["internally_usable"] is True
    assert result.intelligence["content_ready"] is True
    assert result.intelligence["ecosystem_proof_candidate"] is True
    assert result.intelligence["spokesperson_candidate"] is True
    assert result.intelligence["spotlight_ready"] is True
    assert result.intelligence["externally_publishable"] is False


def test_internal_organization_is_not_content_eligible() -> None:
    internal_org = {
        "name": "Opportunity Machine Internal",
        "org_type": "internal",
        "active_flag": True,
        "source_record_id": "rec_internal_001",
        "source_system": "airtable_export",
    }

    result = build_organization_content_intelligence(internal_org)

    assert result.intelligence["content_eligible"] is False
    assert result.intelligence["internally_usable"] is False
    assert result.intelligence["content_ready"] is False
    assert result.intelligence["spotlight_ready"] is False
    assert result.intelligence["externally_publishable"] is False
    assert result.review_flags == []


def test_externally_publishable_can_only_be_set_through_reviewed_truth(tmp_path) -> None:
    mentor = {
        "id": 9,
        "full_name": "Morgan Publishable",
        "person_type": "mentor",
        "active_flag": True,
        "bio": "AI mentor for startup founders.",
        "linkedin": "https://linkedin.com/in/morganpublishable",
        "expertise_tags": "AI, Sales",
        "location": "Lafayette, LA",
        "speaker_ready": True,
        "source_record_id": "rec_mentor_999",
        "source_system": "airtable_export",
    }

    result = build_person_content_intelligence(mentor)
    assert result.intelligence["spotlight_ready"] is True
    assert result.intelligence["externally_publishable"] is False

    override_path = tmp_path / "overrides.json"
    override_path.write_text(
        json.dumps(
            {
                "version": 1,
                "rules": [
                    {
                        "id": "approve-public-use",
                        "target": "person_content",
                        "match": {"linked_person_id": 9},
                        "set": {"externally_publishable": True},
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    override_document = load_override_document(override_path)
    reviewed_bundle, _ = apply_content_bundle_overrides(
        {"people": [result.intelligence], "organizations": [], "review_rows": []},
        override_document,
    )

    assert reviewed_bundle["people"][0]["externally_publishable"] is True


def test_bundle_collects_people_organizations_and_review_rows() -> None:
    founder = {
        "id": 1,
        "full_name": "Priya Founder",
        "person_type": "founder",
        "active_flag": True,
        "bio": "Founder building an AI operations startup.",
        "headshot_url": "https://example.com/priya.jpg",
        "source_record_id": "rec_founder_100",
        "source_system": "airtable_export",
    }
    sparse_mentor = {
        "id": 2,
        "full_name": "Sparse Mentor",
        "person_type": "mentor",
        "active_flag": True,
        "source_record_id": "rec_mentor_100",
        "source_system": "airtable_export",
    }
    organization = {
        "id": 10,
        "name": "Acme AI",
        "org_type": "startup",
        "active_flag": True,
        "website": "https://acme.ai",
        "description": "Workflow software for industrial teams.",
        "source_record_id": "rec_org_100",
        "source_system": "airtable_export",
    }
    affiliations = [{"person_id": 1, "organization_id": 10, "founder_flag": True}]
    cohorts = [{"id": 100, "cohort_name": "Builder Spring 2026", "active_flag": True}]
    participations = [{"organization_id": 10, "cohort_id": 100, "participation_status": "active"}]

    bundle = build_content_intelligence_bundle(
        organizations=[organization],
        people_payloads=[founder, sparse_mentor],
        affiliations=affiliations,
        participations=participations,
        cohorts=cohorts,
    )

    assert len(bundle["people"]) == 2
    assert len(bundle["organizations"]) == 1
    assert len(bundle["review_rows"]) >= 1
    assert all("internally_usable" in item for item in bundle["people"])
    assert all("externally_publishable" in item for item in bundle["people"])
    assert any(row["flag_code"] == "review_content_profile_sparse" for row in bundle["review_rows"])
