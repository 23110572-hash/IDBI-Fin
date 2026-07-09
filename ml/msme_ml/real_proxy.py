"""Optional methodology validation on a REAL public proxy dataset.

There is no public Indian MSME alternate-data + default dataset, so to show the approach is not
overfit to synthetic structure we can validate the *methodology* on the U.S. SBA 7(a)/504 national
small-business loan dataset, which has real charge-off (default) labels.

This is a METHODOLOGY sanity check only — the SBA feature space differs from the Indian
alternate-data feature space, so the AUC is not directly comparable. It answers the judges'
question: "does your modelling approach work on real defaults at all?"

Usage:
    python -m msme_ml.real_proxy --csv path/to/SBAnational.csv

Dataset: https://data.sba.gov/dataset/7-a-504-foia  (or the Kaggle "SBA loans" mirror).
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split


def _clean_currency(s: pd.Series) -> pd.Series:
    return (s.astype(str).str.replace(r"[$,]", "", regex=True)
            .replace({"": np.nan, "nan": np.nan}).astype(float))


def run(csv_path: str) -> dict:
    import xgboost as xgb

    df = pd.read_csv(csv_path, low_memory=False)
    # Label: MIS_Status == 'CHGOFF' (charged off / default) vs 'P I F' (paid in full)
    if "MIS_Status" not in df.columns:
        raise ValueError("Expected SBA schema with a 'MIS_Status' column.")
    df = df[df["MIS_Status"].isin(["CHGOFF", "P I F"])].copy()
    y = (df["MIS_Status"] == "CHGOFF").astype(int)

    num_cols = ["Term", "NoEmp", "CreateJob", "RetainedJob", "DisbursementGross",
                "GrAppv", "SBA_Appv"]
    for c in ("DisbursementGross", "GrAppv", "SBA_Appv"):
        if c in df.columns:
            df[c] = _clean_currency(df[c])
    feats = [c for c in num_cols if c in df.columns]
    X = df[feats].apply(pd.to_numeric, errors="coerce")

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
    model = xgb.XGBClassifier(n_estimators=300, max_depth=5, learning_rate=0.05,
                              subsample=0.85, colsample_bytree=0.8,
                              eval_metric="auc", tree_method="hist", random_state=42)
    model.fit(X_tr, y_tr)
    auc = float(roc_auc_score(y_te, model.predict_proba(X_te)[:, 1]))
    result = {"real_proxy": "SBA-national", "n": int(len(df)), "features": feats,
              "auc_roc": round(auc, 4), "default_rate": round(float(y.mean()), 4)}
    print(result)
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="Path to SBA national loans CSV")
    args = ap.parse_args()
    run(args.csv)
