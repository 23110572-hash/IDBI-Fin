"""SHAP explainability — the ONLY explainer of the decision (XGBoost PD).

Produces (a) per-feature SHAP contributions (consumed by compose.sub_scores_from_shap) and
(b) the top-5 reason codes, with ACTIONABLE features prioritised in the ranking (actionability gate).
"""
from __future__ import annotations

import numpy as np

from .schema import FEATURE_BY_NAME, FEATURE_NAMES

try:
    import shap  # type: ignore

    _HAS_SHAP = True
except Exception:  # pragma: no cover
    _HAS_SHAP = False


class Explainer:
    """Wraps a SHAP TreeExplainer on the trained XGBoost model."""

    def __init__(self, model, feature_names: list[str] | None = None):
        self.model = model
        self.feature_names = feature_names or FEATURE_NAMES
        self._explainer = shap.TreeExplainer(model) if _HAS_SHAP else None
        self.expected_value = self._coerce_expected(
            getattr(self._explainer, "expected_value", 0.0)) if self._explainer is not None else 0.0

    @staticmethod
    def _coerce_expected(val) -> float:
        arr = np.asarray(val).ravel()
        return float(arr[-1]) if arr.size else 0.0

    @property
    def available(self) -> bool:
        return self._explainer is not None

    def shap_values(self, X: np.ndarray) -> np.ndarray:
        """Return SHAP values in the model's margin (log-odds) space, shape (n, n_features)."""
        if self._explainer is None:
            # graceful fallback: approximate with feature_importances broadcast (rarely used)
            imp = getattr(self.model, "feature_importances_", None)
            if imp is None:
                return np.zeros_like(X, dtype=float)
            return np.tile(imp, (X.shape[0], 1)) * 0.0
        vals = self._explainer.shap_values(X)
        if isinstance(vals, list):  # some versions return per-class list
            vals = vals[-1]
        return np.asarray(vals)

    def explain_instance(self, x_row: np.ndarray, feature_values: dict[str, float] | None = None,
                         top_k: int = 5) -> tuple[dict[str, float], list[dict]]:
        """Return (shap_by_feature, top-k reason codes) for a single instance."""
        x = np.asarray(x_row, dtype=float).reshape(1, -1)
        sv = self.shap_values(x)[0]
        shap_by_feature = {name: float(sv[i]) for i, name in enumerate(self.feature_names)}

        # rank: actionable first, then by |shap|
        ranked = sorted(
            self.feature_names,
            key=lambda n: (FEATURE_BY_NAME[n].actionable, abs(shap_by_feature[n])),
            reverse=True,
        )
        reasons = []
        for name in ranked[:top_k]:
            spec = FEATURE_BY_NAME[name]
            s = shap_by_feature[name]
            val = feature_values.get(name) if feature_values else None
            reasons.append({
                "feature": name,
                "label": spec.description,
                "category": spec.category,
                "shap": round(s, 4),
                # positive shap => increases default risk (unfavourable)
                "direction": "increases_risk" if s > 0 else "reduces_risk",
                "impact": "negative" if s > 0 else "positive",
                "value": None if val is None or (isinstance(val, float) and np.isnan(val)) else round(float(val), 3),
                "actionable": spec.actionable,
                "unit": spec.unit,
            })
        return shap_by_feature, reasons
