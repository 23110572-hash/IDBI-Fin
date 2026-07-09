"""Seven-gate feature selection: narrows the 65 raw features to ~40-50.

Gates (architecture.md / tech.md 4.6):
  1. Information Value (IV)   — predictive strength (WOE-based, NaN kept as its own bin).
  2. Regulatory              — whitelist must-keep; blacklist prohibited proxies.
  3. Availability            — non-null rate (kept low so NTC bureau still qualifies as a signal).
  4. Predictive Stability    — PSI(train vs val) <= 0.25 (drift guard).
  5. Actionability           — informational: actionable features are flagged for reason-code ranking.
  6. Fairness                — drop features that proxy protected attributes (none present here).
  7. Cost-Benefit            — drop very-low-IV features from high-cost sources.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from .config import ARTIFACT_DIR
from .schema import FEATURE_BY_NAME, FEATURE_NAMES

# Gate 2 — regulatory whitelist (credit-relevant, defensible; always retained if available)
REGULATORY_WHITELIST = {
    "cibil_msme_score", "delinquency_depth", "gst_compliance_rating", "filing_regularity",
    "inflow_outflow_ratio", "emi_to_inflow",
}
# Gate 6 — prohibited proxies for protected attributes (none in this feature set)
FAIRNESS_BLACKLIST: set[str] = set()

IV_MIN = 0.02
PSI_MAX = 0.25
AVAIL_MIN = 0.05
TARGET_MIN, TARGET_MAX = 40, 50


@dataclass
class GateResult:
    feature: str
    iv: float
    availability: float
    psi: float
    actionable: bool
    regulatory: bool
    fairness_ok: bool
    selected: bool
    reason: str


def _bin_iv(x: pd.Series, y: pd.Series, bins: int = 10) -> float:
    """Information Value with NaN as an explicit bin (missing-as-feature aware)."""
    df = pd.DataFrame({"x": x.values, "y": y.values})
    total_pos = max(df["y"].sum(), 1)
    total_neg = max((1 - df["y"]).sum(), 1)
    iv = 0.0
    nan_mask = df["x"].isna()
    groups = []
    if nan_mask.any():
        groups.append(df[nan_mask])
    non_nan = df[~nan_mask]
    if len(non_nan) > 0:
        try:
            non_nan = non_nan.copy()
            non_nan["b"] = pd.qcut(non_nan["x"], q=min(bins, non_nan["x"].nunique()),
                                   duplicates="drop")
            for _, g in non_nan.groupby("b", observed=True):
                groups.append(g)
        except (ValueError, IndexError):
            groups.append(non_nan)
    for g in groups:
        pos = g["y"].sum()
        neg = (1 - g["y"]).sum()
        dist_pos = pos / total_pos
        dist_neg = neg / total_neg
        if dist_pos > 0 and dist_neg > 0:
            iv += (dist_pos - dist_neg) * np.log(dist_pos / dist_neg)
    return float(iv)


def _psi(expected: pd.Series, actual: pd.Series, bins: int = 10) -> float:
    """Population Stability Index between two samples (NaN treated as a bin)."""
    e_nan = expected.isna().mean()
    a_nan = actual.isna().mean()
    psi = 0.0
    if e_nan > 0 or a_nan > 0:
        e, a = max(e_nan, 1e-4), max(a_nan, 1e-4)
        psi += (a - e) * np.log(a / e)
    e_vals = expected.dropna()
    if e_vals.nunique() < 2:
        return float(abs(psi))
    try:
        edges = np.unique(np.quantile(e_vals, np.linspace(0, 1, bins + 1)))
        e_hist = np.histogram(e_vals, bins=edges)[0] / max(len(e_vals), 1)
        a_hist = np.histogram(actual.dropna(), bins=edges)[0] / max(len(actual.dropna()), 1)
        e_hist = np.clip(e_hist, 1e-4, None)
        a_hist = np.clip(a_hist, 1e-4, None)
        psi += float(np.sum((a_hist - e_hist) * np.log(a_hist / e_hist)))
    except (ValueError, IndexError):
        pass
    return float(abs(psi))


def run_selection(train: pd.DataFrame, val: pd.DataFrame, y_col: str = "default",
                  save: bool = True) -> tuple[list[str], list[GateResult]]:
    y = train[y_col]
    results: list[GateResult] = []
    for name in FEATURE_NAMES:
        spec = FEATURE_BY_NAME[name]
        iv = _bin_iv(train[name], y)
        avail = float(train[name].notna().mean())
        psi = _psi(train[name], val[name]) if name in val.columns else 0.0
        regulatory = name in REGULATORY_WHITELIST
        fairness_ok = name not in FAIRNESS_BLACKLIST

        selected, reason = True, "passed all gates"
        if not fairness_ok:
            selected, reason = False, "gate6: fairness proxy"
        elif avail < AVAIL_MIN and not regulatory:
            selected, reason = False, f"gate3: availability {avail:.2f}<{AVAIL_MIN}"
        elif psi > PSI_MAX and not regulatory:
            selected, reason = False, f"gate4: PSI {psi:.2f}>{PSI_MAX}"
        elif iv < IV_MIN and not regulatory:
            selected, reason = False, f"gate1/7: low IV {iv:.3f}"
        elif regulatory and not selected:
            selected, reason = True, "gate2: regulatory whitelist"

        results.append(GateResult(name, round(iv, 4), round(avail, 3), round(psi, 4),
                                   spec.actionable, regulatory, fairness_ok, selected, reason))

    selected = [r.feature for r in results if r.selected]

    # enforce target band 40-50
    if len(selected) > TARGET_MAX:
        ranked = sorted([r for r in results if r.selected],
                        key=lambda r: (r.regulatory, r.iv), reverse=True)
        keep = {r.feature for r in ranked[:TARGET_MAX]}
        for r in results:
            if r.selected and r.feature not in keep:
                r.selected = False
                r.reason = "gate7: cost-benefit trim (>50)"
        selected = [r.feature for r in results if r.selected]
    elif len(selected) < TARGET_MIN:
        pool = sorted([r for r in results if not r.selected and r.fairness_ok],
                      key=lambda r: r.iv, reverse=True)
        for r in pool[: TARGET_MIN - len(selected)]:
            r.selected = True
            r.reason = "restored to reach target min"
        selected = [r.feature for r in results if r.selected]

    if save:
        ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        (ARTIFACT_DIR / "selected_features.json").write_text(json.dumps(selected, indent=2))
        (ARTIFACT_DIR / "feature_selection_report.json").write_text(
            json.dumps([asdict(r) for r in results], indent=2))
    return selected, results


if __name__ == "__main__":
    from .config import DATA_DIR
    tr = pd.read_parquet(DATA_DIR / "train.parquet")
    va = pd.read_parquet(DATA_DIR / "val.parquet")
    sel, res = run_selection(tr, va)
    print(f"selected {len(sel)}/65 features")
    for r in sorted(res, key=lambda r: r.iv, reverse=True)[:15]:
        print(f"  {r.feature:38s} IV={r.iv:.3f} avail={r.availability:.2f} "
              f"PSI={r.psi:.3f} {'KEEP' if r.selected else 'drop'}")
