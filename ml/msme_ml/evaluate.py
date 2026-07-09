"""Evaluation: discrimination, calibration, tier confusion, and a fairness check.

Fairness uses Fairlearn's MetricFrame when available, else a manual parity computation across
enterprise-size buckets (micro / small / medium).
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    roc_auc_score,
    roc_curve,
)

from .compose import pd_to_score
from .config import ARTIFACT_DIR, tier_for_score


def _tier_key(score: float) -> str:
    return tier_for_score(score)["tier"]


def evaluate(y_true: np.ndarray, pd_hat: np.ndarray, meta: pd.DataFrame) -> dict:
    auc = float(roc_auc_score(y_true, pd_hat))
    ap = float(average_precision_score(y_true, pd_hat))
    brier = float(brier_score_loss(y_true, pd_hat))

    # calibration (10 bins)
    bins = np.quantile(pd_hat, np.linspace(0, 1, 11))
    bins = np.unique(bins)
    calib = []
    idx = np.digitize(pd_hat, bins[1:-1])
    for b in np.unique(idx):
        mask = idx == b
        if mask.sum() > 0:
            calib.append({"bin": int(b), "mean_pred": round(float(pd_hat[mask].mean()), 4),
                          "obs_rate": round(float(y_true[mask].mean()), 4),
                          "n": int(mask.sum())})

    # tier confusion: predicted tier vs actual default rate within tier
    scores = np.array([pd_to_score(p) for p in pd_hat])
    tiers = [_tier_key(s) for s in scores]
    tdf = pd.DataFrame({"tier": tiers, "y": y_true})
    tier_table = (tdf.groupby("tier")["y"]
                  .agg(["count", "mean"]).rename(columns={"mean": "default_rate"})
                  .round(4).reset_index().to_dict("records"))

    # ROC curve (downsampled)
    fpr, tpr, _ = roc_curve(y_true, pd_hat)
    step = max(1, len(fpr) // 100)
    roc = {"fpr": [round(float(x), 4) for x in fpr[::step]],
           "tpr": [round(float(x), 4) for x in tpr[::step]]}

    return {
        "auc_roc": round(auc, 4),
        "average_precision": round(ap, 4),
        "brier_score": round(brier, 4),
        "n": int(len(y_true)),
        "base_default_rate": round(float(y_true.mean()), 4),
        "calibration": calib,
        "tier_confusion": tier_table,
        "roc_curve": roc,
        "fairness": fairness_check(y_true, pd_hat, meta),
    }


def fairness_check(y_true: np.ndarray, pd_hat: np.ndarray, meta: pd.DataFrame,
                   group_col: str = "segment", approve_pd_threshold: float = 0.10) -> dict:
    """Parity of AUC and approval rate across enterprise-size buckets."""
    groups = meta[group_col].to_numpy()
    approve = (pd_hat < approve_pd_threshold).astype(int)
    per_group = {}
    for g in np.unique(groups):
        mask = groups == g
        if mask.sum() < 10:
            continue
        try:
            g_auc = float(roc_auc_score(y_true[mask], pd_hat[mask])) \
                if len(np.unique(y_true[mask])) > 1 else None
        except ValueError:
            g_auc = None
        per_group[str(g)] = {
            "n": int(mask.sum()),
            "auc": round(g_auc, 4) if g_auc is not None else None,
            "approval_rate": round(float(approve[mask].mean()), 4),
            "default_rate": round(float(y_true[mask].mean()), 4),
        }
    rates = [v["approval_rate"] for v in per_group.values()]
    dpd = round(max(rates) - min(rates), 4) if rates else 0.0

    result = {"by_group": per_group, "demographic_parity_difference": dpd,
              "approve_pd_threshold": approve_pd_threshold}

    # augment with Fairlearn if present
    try:
        from fairlearn.metrics import MetricFrame, selection_rate

        mf = MetricFrame(metrics={"selection_rate": selection_rate},
                         y_true=y_true, y_pred=approve, sensitive_features=groups)
        result["fairlearn_selection_rate"] = {str(k): round(float(v), 4)
                                              for k, v in mf.by_group["selection_rate"].items()}
    except Exception:
        result["fairlearn_selection_rate"] = "fairlearn_unavailable"
    return result


def save_report(report: dict, name: str = "evaluation_report.json") -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    (ARTIFACT_DIR / name).write_text(json.dumps(report, indent=2))
