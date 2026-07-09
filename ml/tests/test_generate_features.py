"""Tests for the generator and the feature pipeline."""
import math

import numpy as np

from msme_ml.features import availability_map, extract_features
from msme_ml.generate import generate
from msme_ml.raw_payloads import build_aa_statement
from msme_ml.schema import FEATURE_NAMES


def test_generate_shape_and_label():
    df = generate(n=800, seed=7, target_default_rate=0.09)
    # 65 features present
    for f in FEATURE_NAMES:
        assert f in df.columns
    assert set(df["default"].unique()).issubset({0, 1})
    # default rate roughly on target (loose bound for small n)
    assert 0.04 < df["default"].mean() < 0.16


def test_missingness_is_nan_for_ntc_bureau():
    df = generate(n=800, seed=7)
    ntc = df[df["is_ntc"] == 1]
    # NTC borrowers must have NaN bureau score (missing-as-feature)
    assert ntc["cibil_msme_score"].isna().all()


def test_feature_pipeline_from_aa_payload():
    rng = np.random.default_rng(1)
    aa = build_aa_statement(rng, avg_monthly_inflow=500000, inflow_outflow_ratio=1.2,
                            inflow_cov=0.3, emi_amount=40000, n_bounces=2, seasonality=0.2)
    record = {"aa": aa}
    feats = extract_features(record)
    assert len(feats) == 65
    # cash-flow features computed from raw transactions
    assert feats["avg_monthly_inflow"] > 0
    assert feats["cheque_bounce_count"] >= 2
    # a source that wasn't provided stays NaN
    assert math.isnan(feats["cibil_msme_score"])
    av = availability_map(record)
    assert av["aa"] is True and av["gst"] is False
