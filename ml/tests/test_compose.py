"""Tests for the score composer — the scoring-semantics invariants."""
from msme_ml.compose import pd_to_score, renormalise_weights, sub_scores_from_shap
from msme_ml.config import PILLAR_ORDER, tier_for_score


def test_pd_to_score_bounds():
    assert pd_to_score(0.0) == 100.0
    assert pd_to_score(1.0) == 0.0
    assert pd_to_score(0.28) == 72.0


def test_tier_mapping():
    assert tier_for_score(95)["tier"] == "excellent"
    assert tier_for_score(80)["tier"] == "good"
    assert tier_for_score(65)["tier"] == "fair"
    assert tier_for_score(50)["tier"] == "watch"
    assert tier_for_score(30)["tier"] == "risk"
    assert tier_for_score(10)["tier"] == "high_risk"


def test_renormalise_weights_sums_to_100_when_all_present():
    avail = {s: True for s in ["aa", "gst", "bureau", "epfo", "upi", "udyam", "macro", "electricity"]}
    w = renormalise_weights(avail)
    assert abs(sum(w.values()) - 100.0) < 0.5


def test_renormalise_redistributes_missing_bureau():
    # NTC: bureau source absent -> bureau weight 0, others scaled up to sum 100
    avail = {"aa": True, "gst": True, "bureau": False, "epfo": True, "upi": True,
             "udyam": True, "macro": True, "electricity": True}
    w = renormalise_weights(avail)
    assert w["bureau_credit_history"] == 0.0
    assert abs(sum(w.values()) - 100.0) < 0.5
    # cash flow (base 35) should be scaled above its base
    assert w["cash_flow_stability"] > 35.0


def test_sub_scores_present_for_all_pillars():
    # a small shap dict touching multiple categories
    shap = {"emi_to_inflow": 0.4, "filing_regularity": -0.3, "udyam_age": -0.2,
            "cibil_msme_score": -0.5, "sector_pmi": 0.1}
    subs = sub_scores_from_shap(shap, composite=70.0)
    assert set(subs.keys()) == set(PILLAR_ORDER)
    assert all(0 <= v <= 100 for v in subs.values())
