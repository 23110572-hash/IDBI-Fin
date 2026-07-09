"""Generate data/DATA_DICTIONARY.md from the feature schema (single source of truth)."""
from __future__ import annotations

from msme_ml.config import CATEGORY_TO_PILLAR, DATA_DIR, PILLAR_LABELS
from msme_ml.schema import FEATURES

CATEGORY_LABELS = {
    "cash_flow": "1. Cash Flow Stability (AA)",
    "gst": "2. GST Compliance & Revenue",
    "bureau": "3. Bureau & Credit History",
    "business_stability": "4. Business Stability",
    "behavioural_digital": "5. Behavioural & Digital (UPI)",
    "macro": "6. Macroeconomic Context",
    "utility": "7. Utility & Infrastructure (Electricity)",
}
CATEGORY_ORDER = ["cash_flow", "gst", "bureau", "business_stability", "behavioural_digital",
                  "macro", "utility"]


def main() -> None:
    lines = [
        "# Data Dictionary — The 65 Features",
        "",
        "> Auto-generated from `ml/msme_ml/schema.py` (the single source of truth). Regenerate with "
        "`python -m tools.gen_data_dictionary`.",
        "",
        f"Total features: **{len(FEATURES)}** across 7 engineering categories, mapped to 5 Health-Card "
        "pillars. Missing sources are emitted as NaN (missing-as-feature) and handled natively by "
        "XGBoost.",
        "",
    ]
    for cat in CATEGORY_ORDER:
        feats = [f for f in FEATURES if f.category == cat]
        pillar = PILLAR_LABELS[CATEGORY_TO_PILLAR[cat]]
        lines.append(f"## {CATEGORY_LABELS[cat]}  ({len(feats)} features)")
        lines.append("")
        lines.append(f"*Health-Card pillar:* **{pillar}**")
        lines.append("")
        lines.append("| # | Feature | Source | Unit | Higher is better | Actionable | Definition |")
        lines.append("|---|---------|--------|------|------------------|------------|------------|")
        for i, f in enumerate(feats, 1):
            hib = "yes" if f.higher_is_better else "no"
            act = "yes" if f.actionable else "-"
            lines.append(f"| {i} | `{f.name}` | {f.source} | {f.unit} | {hib} | {act} | "
                         f"{f.description} |")
        lines.append("")
    out = DATA_DIR / "DATA_DICTIONARY.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out} ({len(FEATURES)} features)")


if __name__ == "__main__":
    main()
