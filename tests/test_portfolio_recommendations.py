"""Tests for rules-based portfolio recommendation assembly."""

from src.portfolio.recommendations import (
    attach_portfolio_recommendation_draft,
    build_portfolio_recommendation_draft_from_bundle,
)
from src.reporting.portfolio_pipeline import build_local_portfolio_bundle


def test_build_portfolio_recommendation_draft_from_example_bundle_is_conservative_and_traceable() -> None:
    bundle = build_local_portfolio_bundle()
    recommendation = build_portfolio_recommendation_draft_from_bundle(bundle)

    assert recommendation.organization_id == "org:acme_automation"
    assert recommendation.draft_status == "draft"
    assert recommendation.audience == "internal"
    assert recommendation.top_risks[0].startswith("Product Risk:")
    assert recommendation.strongest_signals[0].startswith("Reviewed signal:")
    assert recommendation.strongest_signals[1].startswith("Pending review signal:")
    assert recommendation.support_recommendations == [
        "Route product onboarding support before capital introductions."
    ]
    assert recommendation.likely_near_term_capital_path_label == "pre-seed venture (emerging draft)"
    assert recommendation.what_not_to_pursue_yet == [
        "Do not start a pre-seed venture process yet.",
        "Do not treat Product Risk as resolved yet.",
        "Do not present unreviewed evidence as capital-ready proof yet.",
    ]
    assert "domain_score:org_acme_automation:customer_risk" in recommendation.linked_domain_score_ids
    assert "capital_readiness:org_acme_automation:internal:2026_q2" in recommendation.linked_capital_readiness_draft_ids


def test_attach_portfolio_recommendation_draft_updates_snapshot_metadata() -> None:
    bundle = build_local_portfolio_bundle(overrides_path=None)
    updated_bundle = attach_portfolio_recommendation_draft(bundle, generated_by="portfolio_recommendation_test")

    assert "portfolio_recommendation_draft" in updated_bundle
    assert updated_bundle["portfolio_snapshot"]["portfolio_recommendation_draft_id"].startswith(
        "portfolio_recommendation:org_acme_automation"
    )
    assert updated_bundle["portfolio_snapshot"]["portfolio_recommendation_draft_status"] == "draft"
    assert updated_bundle["portfolio_recommendation_draft"]["generated_by"] == "portfolio_recommendation_test"
