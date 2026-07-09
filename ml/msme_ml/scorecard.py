"""WOE Logistic scorecard — a PARALLEL, regulator-facing transparency artifact.

Built with OptBinning on the top SHAP features. It produces a points-based scorecard shown ALONGSIDE
the XGBoost decision. It NEVER feeds into or alters the PD (architecture.md 3.4 / 7).

If OptBinning is unavailable, a scikit-learn WOE-style logistic fallback is used so the pipeline
still emits a transparency artifact.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression  # always available

from .config import ARTIFACT_DIR

try:
    from optbinning import BinningProcess, Scorecard

    _HAS_OPTBINNING = True
except Exception:  # pragma: no cover
    _HAS_OPTBINNING = False


class WOEScorecard:
    """Thin wrapper over OptBinning's Scorecard (or a logistic fallback)."""

    def __init__(self, features: list[str]):
        self.features = features
        self._scorecard = None
        self._fallback = None
        self._table = None

    def fit(self, X: pd.DataFrame, y: pd.Series,
            min_score: float = 300, max_score: float = 900) -> WOEScorecard:
        Xf = X[self.features].copy()
        used_optbinning = False
        if _HAS_OPTBINNING:
            try:
                binning = BinningProcess(variable_names=self.features)
                estimator = LogisticRegression(max_iter=1000, solver="lbfgs")
                self._scorecard = Scorecard(
                    binning_process=binning, estimator=estimator,
                    scaling_method="min_max",
                    scaling_method_params={"min": min_score, "max": max_score},
                )
                self._scorecard.fit(Xf, y)
                try:
                    self._table = self._scorecard.table(style="detailed")
                except Exception:
                    self._table = self._scorecard.table()
                used_optbinning = True
            except Exception as exc:  # optbinning/sklearn API drift -> fall back
                print(f"  [scorecard] OptBinning path failed ({exc}); using logistic WOE fallback")
                self._scorecard = None
        if not used_optbinning:  # logistic fallback on median-imputed standardised features
            from sklearn.impute import SimpleImputer
            from sklearn.pipeline import Pipeline
            from sklearn.preprocessing import StandardScaler

            self._fallback = Pipeline([
                ("impute", SimpleImputer(strategy="median")),
                ("scale", StandardScaler()),
                ("lr", LogisticRegression(max_iter=1000)),
            ]).fit(Xf, y)
        return self

    def score(self, X: pd.DataFrame) -> np.ndarray:
        Xf = X[self.features].copy()
        if self._scorecard is not None:
            return self._scorecard.score(Xf)
        # fallback: map PD to a 300-900 band
        pd_hat = self._fallback.predict_proba(Xf)[:, 1]
        return 300 + (1 - pd_hat) * 600

    def points_table(self) -> list[dict]:
        """Return the scorecard points table as JSON-serialisable rows (transparency artifact)."""
        if self._table is not None:
            df = self._table.reset_index()
            df.columns = [str(c) for c in df.columns]
            keep = [c for c in df.columns
                    if c in ("Variable", "Bin", "WoE", "IV", "Points", "Coefficient")]
            return df[keep].round(4).astype(object).where(pd.notna(df[keep]), None).to_dict("records") \
                if keep else []
        if self._fallback is not None:
            lr = self._fallback.named_steps["lr"]
            return [{"Variable": f, "Coefficient": round(float(c), 4)}
                    for f, c in zip(self.features, lr.coef_[0], strict=False)]
        return []

    def save(self, path=None) -> None:
        path = path or (ARTIFACT_DIR / "woe_scorecard_points.json")
        ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "engine": "optbinning" if self._scorecard is not None else "logistic_fallback",
            "features": self.features,
            "note": "Parallel RBI-facing transparency scorecard. Does NOT feed the XGBoost PD.",
            "points_table": self.points_table(),
        }
        with open(path, "w") as fh:
            json.dump(payload, fh, indent=2, default=str)
