"""Scoring service — bridges the orchestrator's feature vector to the shared HealthScorer and the
append-only Score Ledger. Also runs a lightweight Great Expectations-style data-quality gate."""
from __future__ import annotations

import math
import uuid

from msme_ml.scoring import HealthScorer, get_scorer

from .config import get_settings

_settings = get_settings()


def _scorer() -> HealthScorer:
    return get_scorer(_settings.artifact_dir)


def data_quality_report(features: dict, availability: dict) -> dict:
    """Minimal data-quality gate (schema/coverage). Great Expectations runs the fuller suite in
    the batch path; this keeps the online path fast."""
    n_total = len(features)
    n_present = sum(1 for v in features.values()
                    if v is not None and not (isinstance(v, float) and math.isnan(v)))
    sources_present = sum(1 for v in availability.values() if v)
    coverage = round(n_present / max(n_total, 1), 3)
    # AA is critical (cash flow); flag if absent
    critical_ok = availability.get("aa", False)
    return {
        "feature_coverage": coverage,
        "features_present": n_present,
        "features_total": n_total,
        "sources_present": sources_present,
        "critical_source_aa_present": critical_ok,
        "passed": bool(critical_ok and coverage >= 0.2),
    }


def score_borrower(features: dict, availability: dict, include_scorecard: bool = True) -> dict:
    scorer = _scorer()
    card = scorer.score(features, availability)
    result = {"score_id": f"SC-{uuid.uuid4().hex[:16]}", "health_card": card}
    if include_scorecard:
        result["scorecard"] = _scorecard_snapshot(scorer)
    return result


_SCORECARD_CACHE: dict | None = None


def _scorecard_snapshot(scorer: HealthScorer) -> dict | None:
    """Load the parallel WOE scorecard transparency artifact (does NOT affect the PD)."""
    global _SCORECARD_CACHE
    if _SCORECARD_CACHE is not None:
        return _SCORECARD_CACHE
    import json
    from pathlib import Path

    path = Path(_settings.artifact_dir) / "woe_scorecard_points.json"
    if path.exists():
        data = json.loads(path.read_text())
        # trim to a compact transparency view
        _SCORECARD_CACHE = {
            "engine": data.get("engine"),
            "note": data.get("note"),
            "features": data.get("features"),
            "points_table": data.get("points_table", [])[:60],
        }
        return _SCORECARD_CACHE
    return None
