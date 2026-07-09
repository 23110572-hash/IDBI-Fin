"""Runtime scorer — loads trained artifacts and produces a Health Card from a feature vector.

Imported directly by the FastAPI backend so inference is byte-for-byte consistent with training.
Loads the XGBoost Booster (not the sklearn wrapper) + SHAP explainer + metadata, and delegates
composition to compose.build_health_card.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .compose import build_health_card
from .config import ARTIFACT_DIR
from .explain import Explainer

try:
    import xgboost as xgb

    _HAS_XGB = True
except Exception:  # pragma: no cover
    _HAS_XGB = False


class HealthScorer:
    def __init__(self, artifact_dir: Path | str = ARTIFACT_DIR):
        self.artifact_dir = Path(artifact_dir)
        meta_path = self.artifact_dir / "model_metadata.json"
        if not meta_path.exists():
            raise FileNotFoundError(
                f"model_metadata.json not found in {self.artifact_dir}. Run `python -m msme_ml.train`."
            )
        self.metadata = json.loads(meta_path.read_text())
        self.selected_features: list[str] = self.metadata["selected_features"]
        self.model_version: str = self.metadata["model_version"]

        if not _HAS_XGB:
            raise RuntimeError("xgboost is required for scoring.")
        self.booster = xgb.Booster()
        self.booster.load_model(str(self.artifact_dir / "xgb_model.json"))
        self.explainer = Explainer(self.booster, feature_names=self.selected_features)

    # ------------------------------------------------------------------
    def _ordered_row(self, feature_dict: dict[str, float]) -> np.ndarray:
        row = []
        for f in self.selected_features:
            v = feature_dict.get(f)
            row.append(np.nan if v is None else float(v))
        return np.array([row], dtype=np.float32)

    def predict_pd(self, feature_dict: dict[str, float]) -> float:
        row = self._ordered_row(feature_dict)
        dmat = xgb.DMatrix(row, feature_names=self.selected_features, missing=np.nan)
        pd_value = float(self.booster.predict(dmat)[0])
        return pd_value

    def confidence(self, feature_dict: dict[str, float], available_sources: dict[str, bool]) -> float:
        """Simple confidence: fraction of selected features present + source availability."""
        present = sum(1 for f in self.selected_features
                      if not _is_nan(feature_dict.get(f)))
        feat_cov = present / max(len(self.selected_features), 1)
        src_cov = (sum(1 for v in available_sources.values() if v)
                   / max(len(available_sources), 1)) if available_sources else 0.5
        return round(0.5 * feat_cov + 0.5 * src_cov, 3)

    def score(self, feature_dict: dict[str, float], available_sources: dict[str, bool],
              top_k: int = 5) -> dict:
        pd_value = self.predict_pd(feature_dict)
        row = self._ordered_row(feature_dict)[0]
        shap_by_feature, reasons = self.explainer.explain_instance(
            row, feature_values={f: feature_dict.get(f) for f in self.selected_features}, top_k=top_k)
        conf = self.confidence(feature_dict, available_sources)
        card = build_health_card(pd_value, shap_by_feature, available_sources, reasons,
                                 self.model_version, conf)
        return card


def _is_nan(v) -> bool:
    try:
        return v is None or (isinstance(v, float) and np.isnan(v))
    except Exception:
        return True


_DEFAULT_SCORER: HealthScorer | None = None


def get_scorer(artifact_dir: Path | str = ARTIFACT_DIR) -> HealthScorer:
    """Process-wide cached scorer."""
    global _DEFAULT_SCORER
    if _DEFAULT_SCORER is None:
        _DEFAULT_SCORER = HealthScorer(artifact_dir)
    return _DEFAULT_SCORER
