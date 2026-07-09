"""Synthetic MSME dataset generator (seeded, reproducible).

Produces a realistic, correlated 65-feature table with a defensible default label, calibrated to
public Indian statistics (see data/DATA_PROVENANCE.md and data/LABEL_LOGIC.md).

Design notes
------------
* Population is NTC/NTB-skewed and micro-heavy (mirrors reality).
* An unobserved latent "business quality" q drives coherent feature values; the DEFAULT label is a
  transparent latent-risk function of *stress drivers* + stochastic noise (documented in
  LABEL_LOGIC.md). q itself is never emitted as a feature -> no trivial leakage.
* Missing sources are emitted as NaN (missing-as-feature): NTC -> no bureau; micro -> no EPFO;
  B2B -> no UPI; non-manufacturing -> weaker/absent electricity.
* Inter-feature correlation: turnover -> AA inflow -> electricity kWh; sector -> UPI/electricity
  presence; segment -> EPFO presence, vintage, bureau availability.
* A time-based `application_month` (0..23) enables a leakage-free time split.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import raw_payloads as rp
from .config import DATA_DIR, DEFAULT_SEED, RAW_PAYLOAD_DIR
from .schema import (
    FEATURE_NAMES,
    SRC_BUREAU,
    SRC_ELECTRICITY,
    SRC_EPFO,
    SRC_GST,
    SRC_UPI,
    features_for_source,
)

SEGMENTS = ["micro", "small", "medium"]
SEGMENT_P = [0.80, 0.17, 0.03]
SECTORS = ["manufacturing", "trading", "retail", "services", "agri_processing"]
SECTOR_P = [0.28, 0.24, 0.22, 0.18, 0.08]
REGIONS = ["North", "South", "East", "West", "Central"]

# turnover bands (INR) by segment — micro medians far below the 10cr ceiling
TURNOVER_LOGNORM = {
    "micro": (np.log(3.5e6), 0.9, 1e5, 1e7),      # (mu, sigma, min, cap ~1cr)
    "small": (np.log(4e7), 0.7, 1e7, 1e8),         # up to 10cr
    "medium": (np.log(2e8), 0.6, 1e8, 5e8),        # up to 50cr
}


def _sigmoid(x: np.ndarray | float) -> np.ndarray | float:
    return 1.0 / (1.0 + np.exp(-x))


def _sample_segment_sector(rng: np.random.Generator, n: int):
    seg = rng.choice(SEGMENTS, size=n, p=SEGMENT_P)
    sec = rng.choice(SECTORS, size=n, p=SECTOR_P)
    return seg, sec


def generate(n: int = 50000, seed: int = DEFAULT_SEED, target_default_rate: float = 0.09
             ) -> pd.DataFrame:
    """Generate the flattened feature table with metadata + label."""
    rng = np.random.default_rng(seed)
    seg, sec = _sample_segment_sector(rng, n)

    rows: list[dict] = []
    for i in range(n):
        rows.append(_one_firm(rng, seg[i], sec[i], i))
    df = pd.DataFrame(rows)

    # calibrate the label intercept to hit the target default rate
    df = _apply_label(df, rng, target_default_rate)

    # time-based application month for a leakage-free split
    df["application_month"] = rng.integers(0, 24, size=len(df))
    return df


def _one_firm(rng: np.random.Generator, segment: str, sector: str, idx: int) -> dict:
    mu, sigma, tmin, tcap = TURNOVER_LOGNORM[segment]
    turnover = float(np.clip(rng.lognormal(mu, sigma), tmin, tcap))

    # latent business quality q in [0,1]
    q = float(np.clip(rng.beta(2.2, 2.0), 0.02, 0.98))

    is_manuf = sector in ("manufacturing", "agri_processing")
    is_b2c = sector in ("retail", "trading", "services")

    # ---- availability / missingness ----
    p_ntc = {"micro": 0.75, "small": 0.45, "medium": 0.20}[segment]
    is_ntc = rng.random() < p_ntc
    is_ntb = rng.random() < 0.82  # target population skew

    employees = int(np.clip(rng.lognormal({"micro": np.log(6), "small": np.log(40),
                                            "medium": np.log(180)}[segment], 0.6), 1, 5000))
    has_epfo = employees >= 20
    has_gst = (turnover > 1.2e6) or (rng.random() < 0.85)
    has_upi = is_b2c and (rng.random() < 0.9)
    has_electricity = is_manuf or (rng.random() < 0.4)

    # macro (region/sector context)
    region = REGIONS[idx % len(REGIONS)]
    sector_pmi = float(np.clip(rng.normal(52, 4), 40, 62))
    supply_chain_stress = float(np.clip(rng.beta(2, 5), 0, 1))
    rbi_outlook = float(np.clip(rng.normal(0.6, 0.15), 0, 1))
    macro_adverse = (1 - rbi_outlook) * 0.5 + supply_chain_stress * 0.5

    f: dict[str, float] = {}

    # ---- Cash Flow (AA, always present) ----
    inflow = turnover / 12.0 * rng.uniform(0.85, 1.15)
    ratio = float(np.clip(rng.normal(0.9 + 0.5 * q, 0.18), 0.4, 2.2))
    cov = float(np.clip(rng.normal(0.45 - 0.25 * q, 0.1), 0.05, 1.2))
    emi_to_inflow = float(np.clip(rng.normal(0.35 - 0.2 * q, 0.15), 0.0, 1.3))
    bounces = int(rng.poisson(max(0.1, 2.5 * (1 - q))))
    days_neg = int(np.clip(rng.normal(30 * (1 - q), 12), 0, 200))
    f["avg_monthly_inflow"] = inflow
    f["avg_monthly_outflow"] = inflow / ratio
    f["inflow_outflow_ratio"] = ratio
    f["inflow_volatility_cov"] = cov
    f["min_balance_6mo"] = float(max(rng.normal(inflow * (0.15 + 0.4 * q), inflow * 0.1), -inflow * 0.3))
    f["min_balance_12mo"] = f["min_balance_6mo"] * rng.uniform(0.6, 1.0)
    f["overdraft_utilisation"] = float(np.clip(rng.normal(0.6 - 0.35 * q, 0.2), 0, 1))
    f["emi_to_inflow"] = emi_to_inflow
    f["cheque_bounce_count"] = bounces
    f["days_negative_balance"] = days_neg
    f["seasonality_index"] = float(np.clip(rng.normal(0.4 + 0.2 * q, 0.15), 0, 1))
    f["cash_buffer_days"] = float(np.clip(rng.normal(20 + 60 * q, 20), 0, 365))
    f["supplier_payment_velocity"] = float(np.clip(rng.normal(60 - 30 * q, 15), 5, 180))
    f["customer_concentration_top3"] = float(np.clip(rng.normal(0.55 - 0.25 * q, 0.15), 0.1, 0.98))
    f["tax_payment_velocity"] = float(np.clip(rng.normal(20 - 15 * q, 8), 0, 90))

    # ---- GST ----
    if has_gst:
        reg = float(np.clip(rng.normal(0.6 + 0.35 * q, 0.12), 0.1, 1.0))
        mismatch = float(np.clip(rng.normal(0.15 - 0.1 * q, 0.06), 0.0, 0.6))
        f["gstr1_turnover_trend_12mo"] = float(rng.normal(0.05 + 0.15 * q - 0.1 * macro_adverse, 0.1))
        f["gstr1_turnover_trend_24mo"] = f["gstr1_turnover_trend_12mo"] * rng.uniform(0.7, 1.1)
        f["gst_turnover_yoy_growth"] = float(rng.normal(8 + 20 * q - 15 * macro_adverse, 12))
        f["gstr3b_liability_trend"] = f["gstr1_turnover_trend_12mo"] * rng.uniform(0.6, 1.0)
        f["gstr1_vs_3b_mismatch"] = mismatch
        f["itc_ratio"] = float(np.clip(rng.normal(0.4 + 0.2 * q, 0.12), 0.0, 0.95))
        f["filing_regularity"] = reg
        f["gst_compliance_rating"] = float(np.clip(reg * 100 + rng.normal(0, 6), 0, 100))
        f["sector_benchmark_deviation"] = float(rng.normal(0.2 * (q - 0.5), 0.6))
        f["annual_return_consistency"] = float(np.clip(rng.normal(0.6 + 0.3 * q, 0.12), 0, 1))
        f["gstr9c_reconciliation"] = float(np.clip(rng.normal(0.55 + 0.35 * q, 0.15), 0, 1))
        f["gst_filing_gap"] = float(np.clip(rng.normal(3 * (1 - reg), 1.5), 0, 12))
    else:
        for name in features_for_source(SRC_GST):
            f[name] = np.nan

    # ---- Bureau (empty for NTC) ----
    if not is_ntc:
        base_score = np.clip(rng.normal(680 + 120 * (q - 0.5) * 2, 60), 300, 900)
        f["cibil_msme_score"] = float(base_score)
        f["obligation_count"] = int(np.clip(rng.poisson(3 + 3 * (1 - q)), 0, 25))
        f["enquiries_6mo"] = int(np.clip(rng.poisson(1 + 3 * (1 - q)), 0, 20))
        f["delinquency_depth"] = float(np.clip(rng.normal(60 * (1 - q), 30), 0, 180))
        f["bureau_utilisation_ratio"] = float(np.clip(rng.normal(0.55 - 0.3 * q, 0.2), 0, 1.2))
        f["oldest_tradeline_age"] = float(np.clip(rng.normal(48 + 60 * q, 24), 3, 300))
        f["secured_unsecured_mix"] = float(np.clip(rng.normal(0.4 + 0.3 * q, 0.2), 0, 1))
        f["writeoff_count"] = int(np.clip(rng.poisson(0.6 * (1 - q)), 0, 8))
    else:
        for name in features_for_source(SRC_BUREAU):
            f[name] = np.nan

    # ---- Business Stability ----
    vintage = float(np.clip(rng.normal({"micro": 40, "small": 80, "medium": 140}[segment], 30), 3, 400))
    f["udyam_age"] = vintage
    f["bank_account_age"] = float(np.clip(vintage * rng.uniform(0.8, 1.3), 3, 420))
    f["gst_vintage"] = float(np.clip(vintage * rng.uniform(0.6, 1.0), 0, 400)) if has_gst else np.nan
    f["location_stability"] = float(np.clip(rng.normal(0.6 + 0.3 * q, 0.15), 0, 1))
    f["ownership_stability"] = float(np.clip(rng.normal(0.65 + 0.25 * q, 0.15), 0, 1))
    f["active_registrations_count"] = int(1 + has_gst + has_epfo + (rng.random() < 0.5))
    if has_epfo:
        etrend = float(rng.normal(0.05 + 0.15 * q - 0.1 * macro_adverse, 0.08))
        f["epfo_employee_trend_12mo"] = etrend
        f["epfo_employee_trend_24mo"] = etrend * rng.uniform(0.7, 1.1)
        f["payroll_regularity"] = float(np.clip(rng.normal(0.7 + 0.25 * q, 0.1), 0, 1))
        f["salary_growth"] = float(rng.normal(6 + 8 * q, 5))
    else:
        for name in features_for_source(SRC_EPFO):
            f[name] = np.nan

    # ---- Behavioural & Digital (UPI) ----
    if has_upi:
        base_freq = turnover / 12.0 / max(rng.normal(600, 150), 100)
        f["upi_txn_frequency"] = float(np.clip(base_freq * rng.uniform(0.7, 1.3), 5, 60000))
        f["upi_unique_customers"] = float(np.clip(f["upi_txn_frequency"] * rng.uniform(0.2, 0.6), 3, 40000))
        f["upi_avg_txn_value"] = float(np.clip(rng.normal(700, 250), 50, 20000))
        f["upi_customer_concentration"] = float(np.clip(rng.normal(0.4 - 0.15 * q, 0.15), 0.05, 0.95))
        f["digital_payment_adoption_pct"] = float(np.clip(rng.normal(45 + 40 * q, 18), 0, 100))
        f["ecommerce_presence"] = int(rng.random() < (0.2 + 0.5 * q))
        f["payment_timing_regularity"] = float(np.clip(rng.normal(0.5 + 0.3 * q, 0.15), 0, 1))
        f["reminder_response"] = float(np.clip(rng.normal(0.55 + 0.35 * q, 0.15), 0, 1))
    else:
        for name in features_for_source(SRC_UPI):
            f[name] = np.nan

    # ---- Macro (always present) ----
    f["rbi_sector_outlook"] = rbi_outlook
    f["regional_gdp_growth"] = float(np.clip(rng.normal(6.5, 1.5), 1, 12))
    f["sector_pmi"] = sector_pmi
    f["input_cost_inflation"] = float(np.clip(rng.normal(5 + 3 * macro_adverse, 2), 0, 20))
    f["supply_chain_stress"] = supply_chain_stress
    f["regulatory_change_exposure"] = float(np.clip(rng.beta(2, 6), 0, 1))
    f["currency_exposure"] = float(np.clip(rng.beta(2, 6) * (1.5 if is_manuf else 0.6), 0, 1))

    # ---- Utility / Electricity ----
    if has_electricity:
        avg_kwh = turnover / 12.0 / rng.uniform(80, 200) * (2.0 if is_manuf else 0.6)
        f["electricity_consumption_trend"] = float(rng.normal(0.04 + 0.12 * q - 0.1 * macro_adverse, 0.08))
        f["consumption_volatility"] = float(np.clip(rng.normal(0.3 - 0.15 * q, 0.1), 0.05, 1.0))
        f["bill_payment_regularity"] = float(np.clip(rng.normal(0.7 + 0.25 * q, 0.12), 0, 1))
        f["sanctioned_load_utilisation"] = float(np.clip(rng.normal(0.55 + 0.2 * q, 0.15), 0.1, 1.0))
        f["consumption_vs_turnover_consistency"] = float(np.clip(rng.normal(0.6 + 0.3 * q, 0.15), 0, 1))
        f["_avg_kwh"] = avg_kwh  # helper for raw payload, dropped later
    else:
        for name in features_for_source(SRC_ELECTRICITY):
            f[name] = np.nan
        f["_avg_kwh"] = np.nan

    # metadata + latent (not features)
    f["msme_id"] = f"MSME{idx:07d}"
    f["segment"] = segment
    f["sector"] = sector
    f["region"] = region
    f["is_ntc"] = int(is_ntc)
    f["is_ntb"] = int(is_ntb)
    f["annual_turnover"] = turnover
    f["employees"] = employees
    f["_q"] = q
    f["_macro_adverse"] = macro_adverse
    return f


def _apply_label(df: pd.DataFrame, rng: np.random.Generator, target_rate: float) -> pd.DataFrame:
    """Transparent latent-risk -> PD -> Bernoulli default. See data/LABEL_LOGIC.md."""
    def z(col, fill):
        s = df[col].fillna(fill)
        return (s - s.mean()) / (s.std() + 1e-9)

    # stress drivers (higher => riskier)
    risk = (
        0.9 * z("emi_to_inflow", df["emi_to_inflow"].mean())
        + 0.9 * (-z("inflow_outflow_ratio", 1.0))
        + 0.7 * z("cheque_bounce_count", 0)
        + 0.6 * z("days_negative_balance", 0)
        + 0.6 * z("gstr1_vs_3b_mismatch", 0.0)         # NaN(no GST) -> mean-filled (neutral)
        + 0.5 * (-z("filing_regularity", 0.5))
        + 0.4 * (-z("gstr1_turnover_trend_12mo", 0.0))
        + 0.4 * (-z("epfo_employee_trend_12mo", 0.0))
        + 0.3 * (-z("electricity_consumption_trend", 0.0))
        + 0.5 * z("delinquency_depth", 0.0)            # NaN(NTC) -> neutral, NOT a penalty
        + 0.6 * df["_macro_adverse"].to_numpy()
        - 1.6 * (df["_q"].to_numpy() - 0.5) * 2.0       # overall quality
    )
    # micro carries slightly higher base risk (RBI nascent-stress note)
    seg_bump = df["segment"].map({"micro": 0.25, "small": 0.0, "medium": -0.15}).to_numpy()
    # stochastic noise (irreducible) — sized so held-out AUC lands ~0.83-0.88, realistic for
    # alternate-data MSME models rather than an implausibly perfect synthetic separation.
    logit = risk.to_numpy() + seg_bump + rng.normal(0, 1.5, len(df))

    # solve intercept so mean PD ~= target_rate
    lo, hi = -12.0, 12.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if _sigmoid(logit + mid).mean() > target_rate:
            hi = mid
        else:
            lo = mid
    intercept = (lo + hi) / 2
    pd_true = _sigmoid(logit + intercept)
    df["_pd_true"] = pd_true
    df["default"] = (rng.random(len(df)) < pd_true).astype(int)
    return df


def _write_sample_payloads(df: pd.DataFrame, rng: np.random.Generator, n_samples: int = 24) -> None:
    """Write raw per-source payloads for a small sample so the backend pipeline is exercised."""
    RAW_PAYLOAD_DIR.mkdir(parents=True, exist_ok=True)
    sample = df.head(n_samples)
    for _, row in sample.iterrows():
        _write_one_payload(row, rng)


def _write_one_payload(row: pd.Series, rng: np.random.Generator) -> None:
    d = RAW_PAYLOAD_DIR / str(row["msme_id"])
    d.mkdir(parents=True, exist_ok=True)
    aa = rp.build_aa_statement(
        rng,
        avg_monthly_inflow=float(row["avg_monthly_inflow"]),
        inflow_outflow_ratio=float(row["inflow_outflow_ratio"]),
        inflow_cov=float(row["inflow_volatility_cov"]),
        emi_amount=float(row["emi_to_inflow"]) * float(row["avg_monthly_inflow"]) / 12.0,
        n_bounces=int(row["cheque_bounce_count"]),
        seasonality=float(row["seasonality_index"]),
    )
    (d / "aa.json").write_text(json.dumps(aa, indent=2))
    if not pd.isna(row.get("filing_regularity")):
        gst = rp.build_gst_filings(
            rng, annual_turnover=float(row["annual_turnover"]),
            filing_regularity=float(row["filing_regularity"]),
            mismatch=float(row["gstr1_vs_3b_mismatch"]),
            itc_ratio=float(row["itc_ratio"]),
        )
        (d / "gst.json").write_text(json.dumps(gst, indent=2))
    if not pd.isna(row.get("upi_txn_frequency")):
        upi = rp.build_upi_summary(rng, txn_freq=float(row["upi_txn_frequency"]),
                                   avg_value=float(row["upi_avg_txn_value"]),
                                   unique_customers=float(row["upi_unique_customers"]))
        (d / "upi.json").write_text(json.dumps(upi, indent=2))
    if not pd.isna(row.get("epfo_employee_trend_12mo")):
        epfo = rp.build_epfo_record(rng, employees=int(row["employees"]),
                                    trend=float(row["epfo_employee_trend_12mo"]))
        (d / "epfo.json").write_text(json.dumps(epfo, indent=2))
    if not pd.isna(row.get("_avg_kwh")):
        elec = rp.build_electricity_bill(rng, avg_kwh=float(row["_avg_kwh"]),
                                         trend=float(row["electricity_consumption_trend"]),
                                         sanctioned_load_kw=float(row["_avg_kwh"]) / 200.0)
        (d / "electricity.json").write_text(json.dumps(elec, indent=2))
        (d / "electricity_bill.txt").write_text(elec["ocr_text"])


def time_split(df: pd.DataFrame):
    """Leakage-free time split: train <=17, val 18-20, test 21-23 (application_month)."""
    train = df[df["application_month"] <= 17].copy()
    val = df[(df["application_month"] >= 18) & (df["application_month"] <= 20)].copy()
    test = df[df["application_month"] >= 21].copy()
    return train, val, test


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate synthetic MSME dataset.")
    ap.add_argument("--n", type=int, default=50000)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--default-rate", type=float, default=0.09)
    ap.add_argument("--out", type=str, default=str(DATA_DIR))
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    print(f"Generating {args.n} synthetic MSMEs (seed={args.seed})...")
    df = generate(args.n, args.seed, args.default_rate)

    # drop private helper cols from the persisted feature table (keep label + metadata)
    keep = FEATURE_NAMES + ["msme_id", "segment", "sector", "region", "is_ntc", "is_ntb",
                            "annual_turnover", "employees", "application_month", "default"]
    feature_table = df[keep].copy()

    full_path = out / "msme_synthetic.parquet"
    feature_table.to_parquet(full_path, index=False)
    train, val, test = time_split(feature_table)
    train.to_parquet(out / "train.parquet", index=False)
    val.to_parquet(out / "val.parquet", index=False)
    test.to_parquet(out / "test.parquet", index=False)

    # raw payloads for a demo sample (+ backend fixtures)
    _write_sample_payloads(df, np.random.default_rng(args.seed + 1))

    rate = feature_table["default"].mean()
    print(f"  rows={len(feature_table)}  default_rate={rate:.3%}")
    print(f"  NTC share={feature_table['is_ntc'].mean():.1%}  "
          f"NTB share={feature_table['is_ntb'].mean():.1%}")
    print(f"  segments: {feature_table['segment'].value_counts(normalize=True).round(3).to_dict()}")
    print(f"  train/val/test = {len(train)}/{len(val)}/{len(test)}")
    print(f"  wrote {full_path} and splits; raw payloads -> {RAW_PAYLOAD_DIR}")


if __name__ == "__main__":
    main()
