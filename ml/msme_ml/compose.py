"""Score composer — turns the single XGBoost PD into the Health Card.

Pure functions (no heavy deps) so the FastAPI backend imports these directly and stays byte-for-byte
consistent with training semantics.

  * Score = 100 * (1 - PD)  (the ONLY decision score; no PD blend).
  * 6 risk tiers via config.tier_for_score.
  * 5 sub-scores from SHAP contributions grouped by pillar, affinely aligned so their display-weighted
    average equals the composite (pillars always agree with the composite).
  * Dynamic pillar-weight renormalisation is a DASHBOARD concern: when a pillar has no data its weight
    is redistributed proportionally across the remaining pillars. The PD is NEVER re-weighted.
"""
from __future__ import annotations

import math

from .config import (
    CATEGORY_TO_PILLAR,
    PILLAR_DISPLAY_WEIGHTS,
    PILLAR_LABELS,
    PILLAR_ORDER,
    PILLAR_PRIMARY_SOURCE,
    tier_for_score,
)
from .schema import FEATURE_BY_NAME


def pd_to_score(pd_value: float) -> float:
    """Score = 100 * (1 - PD), clamped to [0, 100]."""
    return float(max(0.0, min(100.0, 100.0 * (1.0 - pd_value))))


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, x))))


def pillar_of(feature_name: str) -> str:
    return CATEGORY_TO_PILLAR[FEATURE_BY_NAME[feature_name].category]


def renormalise_weights(available_sources: dict[str, bool]) -> dict[str, float]:
    """Dashboard-only: redistribute weights of empty pillars across present pillars.

    A pillar is 'present' if at least one of its primary data sources is available. Bureau maps to
    the bureau source, cash flow to AA/UPI, gst to GST, business to Udyam/EPFO/electricity, macro
    is always present.
    """
    from .schema import FEATURE_NAMES

    # determine which pillars have any available source
    pillar_present: dict[str, bool] = {p: False for p in PILLAR_ORDER}
    for fname in FEATURE_NAMES:
        spec = FEATURE_BY_NAME[fname]
        if available_sources.get(spec.source, False):
            pillar_present[pillar_of(fname)] = True
    pillar_present["macroeconomic_context"] = True  # macro is pre-cached, always present

    present = [p for p in PILLAR_ORDER if pillar_present[p]]
    total_present_weight = sum(PILLAR_DISPLAY_WEIGHTS[p] for p in present)
    weights = {}
    for p in PILLAR_ORDER:
        if pillar_present[p]:
            # scale up proportionally so present weights sum to 100
            weights[p] = round(PILLAR_DISPLAY_WEIGHTS[p] * 100.0 / total_present_weight, 2)
        else:
            weights[p] = 0.0
    return weights


def sub_scores_from_shap(shap_by_feature: dict[str, float], composite: float,
                         scale: float = 1.6) -> dict[str, float]:
    """Group SHAP (log-odds toward default) by pillar -> 0-100 health sub-scores.

    Positive SHAP pushes toward default (unhealthy) -> lower sub-score. Sub-scores are affinely
    shifted so their equal... (display-weighted) average equals the composite, guaranteeing the
    pillars agree with the composite.
    """
    pillar_shap: dict[str, float] = {p: 0.0 for p in PILLAR_ORDER}
    pillar_has: dict[str, bool] = {p: False for p in PILLAR_ORDER}
    for fname, val in shap_by_feature.items():
        if fname not in FEATURE_BY_NAME:
            continue
        p = pillar_of(fname)
        if val is not None and not (isinstance(val, float) and math.isnan(val)):
            pillar_shap[p] += float(val)
            pillar_has[p] = True

    # raw health sub-score: negative shap (reduces default) -> high score
    raw = {p: 100.0 * _sigmoid(-scale * pillar_shap[p]) for p in PILLAR_ORDER}

    # affine-align the (present-pillar) weighted mean to the composite
    weights = renormalise_weights({FEATURE_BY_NAME[f].source: True for f in shap_by_feature})
    present = [p for p in PILLAR_ORDER if pillar_has[p]]
    if present:
        wsum = sum(weights[p] for p in present) or 1.0
        weighted_mean = sum(weights[p] * raw[p] for p in present) / wsum
        shift = composite - weighted_mean
    else:
        shift = 0.0
    return {p: round(max(0.0, min(100.0, raw[p] + shift)), 1) for p in PILLAR_ORDER}


def build_health_card(pd_value: float, shap_by_feature: dict[str, float],
                      available_sources: dict[str, bool], reason_codes: list[dict],
                      model_version: str, confidence: float) -> dict:
    """Assemble the full Health Card payload returned by the API / rendered by the dashboard."""
    composite = pd_to_score(pd_value)
    tier = tier_for_score(composite)
    subs = sub_scores_from_shap(shap_by_feature, composite)
    weights = renormalise_weights(available_sources)

    pillars = []
    for p in PILLAR_ORDER:
        pillars.append({
            "pillar": p,
            "label": PILLAR_LABELS[p],
            "primary_source": PILLAR_PRIMARY_SOURCE[p],
            "sub_score": subs[p],
            "display_weight": weights[p],
            "base_weight": PILLAR_DISPLAY_WEIGHTS[p],
            "available": weights[p] > 0,
        })

    return {
        "pd": round(float(pd_value), 4),
        "composite_score": round(composite, 1),
        "tier": tier["tier"],
        "tier_label": tier["label"],
        "action": tier["action"],
        "segment_label": tier["segment"],
        "confidence": round(float(confidence), 3),
        "pillars": pillars,
        "reason_codes": reason_codes,
        "model_version": model_version,
        "available_sources": available_sources,
    }
