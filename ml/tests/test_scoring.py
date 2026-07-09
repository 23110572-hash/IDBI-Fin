"""End-to-end scoring test (skips gracefully if the model hasn't been trained yet)."""

import pytest

from msme_ml.config import ARTIFACT_DIR

_MODEL_READY = (ARTIFACT_DIR / "model_metadata.json").exists()


@pytest.mark.skipif(not _MODEL_READY, reason="model not trained (run python -m msme_ml.train)")
def test_score_produces_consistent_health_card():
    import pandas as pd

    from msme_ml.config import DATA_DIR
    from msme_ml.schema import FEATURE_NAMES
    from msme_ml.scoring import get_scorer

    df = pd.read_parquet(DATA_DIR / "test.parquet")
    scorer = get_scorer()
    row = df.iloc[0]
    fd = {k: (None if pd.isna(row[k]) else float(row[k])) for k in FEATURE_NAMES}
    av = {s: True for s in ["aa", "gst", "bureau", "epfo", "upi", "udyam", "macro", "electricity"]}
    card = scorer.score(fd, av)

    assert 0 <= card["composite_score"] <= 100
    assert 0 <= card["pd"] <= 1
    # composite consistent with PD
    assert abs(card["composite_score"] - 100 * (1 - card["pd"])) < 0.6
    # five pillars, each 0-100
    assert len(card["pillars"]) == 5
    assert all(0 <= p["sub_score"] <= 100 for p in card["pillars"])
    # exactly five reason codes
    assert len(card["reason_codes"]) == 5


def test_auc_target_met_if_trained():
    if not _MODEL_READY:
        pytest.skip("model not trained")
    import json

    meta = json.loads((ARTIFACT_DIR / "model_metadata.json").read_text())
    assert meta["auc_roc"] >= 0.80, f"AUC {meta['auc_roc']} below 0.80 target"
