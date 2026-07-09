"""Training orchestrator — the single XGBoost decision model + SHAP + parallel WOE scorecard.

Pipeline:
  1. Load time-split train/val/test.
  2. Seven-gate feature selection (65 -> ~40-50).
  3. Train XGBoost (missing-native, class-imbalance aware) -> single PD.
  4. Evaluate on held-out test (target AUC >= 0.80) + calibration + tier confusion + fairness.
  5. Fit SHAP TreeExplainer; sanity-check the 5 grouped sub-scores.
  6. Fit the PARALLEL WOE scorecard (OptBinning) on top SHAP features (never blended).
  7. Track everything in MLflow (guarded) and persist artifacts for the backend.
"""
from __future__ import annotations

import datetime as dt
import json

import numpy as np
import pandas as pd
import xgboost as xgb

from .compose import sub_scores_from_shap
from .config import ARTIFACT_DIR, DATA_DIR, DEFAULT_SEED
from .evaluate import evaluate, save_report
from .explain import Explainer
from .scorecard import WOEScorecard
from .selection import run_selection

MODEL_VERSION_PREFIX = "xgb-msme"


def _load_splits():
    tr = pd.read_parquet(DATA_DIR / "train.parquet")
    va = pd.read_parquet(DATA_DIR / "val.parquet")
    te = pd.read_parquet(DATA_DIR / "test.parquet")
    return tr, va, te


def train(seed: int = DEFAULT_SEED) -> dict:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    tr, va, te = _load_splits()
    print(f"Loaded splits: train={len(tr)} val={len(va)} test={len(te)}")

    # --- seven-gate selection ---
    selected, gate_results = run_selection(tr, va)
    n_kept = len(selected)
    print(f"Seven-gate selection: kept {n_kept}/65 features")

    y_tr, y_va, y_te = tr["default"].to_numpy(), va["default"].to_numpy(), te["default"].to_numpy()
    X_tr, X_va, X_te = tr[selected], va[selected], te[selected]

    # --- XGBoost (single decision model) ---
    pos = max(int(y_tr.sum()), 1)
    neg = int((1 - y_tr).sum())
    scale_pos_weight = neg / pos
    params = dict(
        n_estimators=400, max_depth=5, learning_rate=0.05,
        subsample=0.85, colsample_bytree=0.8, min_child_weight=5,
        reg_lambda=1.5, reg_alpha=0.2, gamma=0.5,
        objective="binary:logistic", eval_metric="auc",
        scale_pos_weight=scale_pos_weight, tree_method="hist",
        random_state=seed, n_jobs=-1,
    )
    model = xgb.XGBClassifier(**params, early_stopping_rounds=40)
    model.fit(X_tr, y_tr, eval_set=[(X_va, y_va)], verbose=False)
    best_it = getattr(model, "best_iteration", None)
    print(f"XGBoost trained (best_iteration={best_it}, scale_pos_weight={scale_pos_weight:.2f})")

    # --- evaluate on held-out test ---
    pd_te = model.predict_proba(X_te)[:, 1]
    report = evaluate(y_te, pd_te, te[["segment", "sector", "is_ntc", "region"]])
    auc = report["auc_roc"]
    print(f"Held-out test AUC-ROC = {auc:.4f}  (target >= 0.80)")

    # NTC/NTB-only AUC (the population that matters)
    ntc_mask = te["is_ntc"].to_numpy().astype(bool)
    if ntc_mask.sum() > 10 and len(np.unique(y_te[ntc_mask])) > 1:
        from sklearn.metrics import roc_auc_score
        report["auc_roc_ntc"] = round(float(roc_auc_score(y_te[ntc_mask], pd_te[ntc_mask])), 4)
        print(f"NTC-only test AUC-ROC = {report['auc_roc_ntc']:.4f}")

    # --- SHAP + sub-score sanity ---
    explainer = Explainer(model, feature_names=selected)
    shap_by_feature, reasons = explainer.explain_instance(
        X_te.iloc[0].to_numpy(),
        feature_values=X_te.iloc[0].to_dict())
    composite0 = 100 * (1 - pd_te[0])
    subs0 = sub_scores_from_shap(shap_by_feature, composite0)
    print(f"SHAP OK (available={explainer.available}); "
          f"sample composite={composite0:.1f}, sub-scores={subs0}")

    # --- parallel WOE scorecard on top SHAP features (NOT blended) ---
    sv_all = explainer.shap_values(X_va.to_numpy())
    mean_abs = np.abs(sv_all).mean(axis=0)
    top_idx = np.argsort(mean_abs)[::-1][:min(18, len(selected))]
    top_features = [selected[i] for i in top_idx]
    scorecard = WOEScorecard(top_features)
    try:
        scorecard.fit(tr, tr["default"])
        scorecard.save()
        print(f"WOE scorecard fitted on {len(top_features)} top features (parallel artifact)")
    except Exception as exc:  # keep pipeline alive
        print(f"WOE scorecard skipped: {exc}")

    # --- persist artifacts ---
    model_version = f"{MODEL_VERSION_PREFIX}-{dt.datetime.now():%Y%m%d-%H%M%S}"
    # xgboost 2.0.3's sklearn-wrapper save_model is broken; persist the underlying Booster
    # (loadable by both the backend Booster API and SHAP TreeExplainer).
    model.get_booster().save_model(str(ARTIFACT_DIR / "xgb_model.json"))
    metadata = {
        "model_version": model_version,
        "created_utc": dt.datetime.now(dt.UTC).isoformat(),
        "selected_features": selected,
        "n_features": n_kept,
        "expected_value": explainer.expected_value,
        "params": params,
        "scale_pos_weight": scale_pos_weight,
        "best_iteration": int(best_it) if best_it is not None else None,
        "auc_roc": auc,
        "auc_roc_ntc": report.get("auc_roc_ntc"),
        "top_shap_features": top_features,
        "target_auc": 0.80,
        "auc_target_met": bool(auc >= 0.80),
    }
    (ARTIFACT_DIR / "model_metadata.json").write_text(json.dumps(metadata, indent=2))
    report["model_version"] = model_version
    report["n_features"] = n_kept
    save_report(report)
    print(f"Artifacts saved to {ARTIFACT_DIR}")

    # --- MLflow (guarded) ---
    _mlflow_log(params, report, model_version, n_kept)

    if auc < 0.80:
        print("WARNING: AUC below 0.80 target. Inspect feature selection / generator calibration.")
    else:
        print("SUCCESS: AUC target met.")
    return metadata


def _mlflow_log(params, report, model_version, n_features):
    try:
        import mlflow

        mlflow.set_tracking_uri((ARTIFACT_DIR / "mlruns").as_uri())
        mlflow.set_experiment("msme-financial-health-card")
        with mlflow.start_run(run_name=model_version):
            mlflow.log_params({k: str(v) for k, v in params.items()})
            mlflow.log_param("n_features", n_features)
            mlflow.log_metrics({
                "auc_roc": report["auc_roc"],
                "average_precision": report["average_precision"],
                "brier_score": report["brier_score"],
                "auc_roc_ntc": report.get("auc_roc_ntc") or 0.0,
                "demographic_parity_difference":
                    report["fairness"]["demographic_parity_difference"],
            })
            mlflow.log_artifact(str(ARTIFACT_DIR / "evaluation_report.json"))
            mlflow.log_artifact(str(ARTIFACT_DIR / "model_metadata.json"))
        print("MLflow run logged.")
    except Exception as exc:
        print(f"MLflow logging skipped ({type(exc).__name__}): {exc}")


if __name__ == "__main__":
    train()
