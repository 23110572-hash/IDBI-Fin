"""Global constants: pillars, display weights, risk tiers, paths.

These are the single source of truth for scoring semantics and are imported by both the
ML training code and (via the installed package) the FastAPI backend, so the two never drift.
"""
from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ML_DIR = Path(__file__).resolve().parent.parent          # .../ml
REPO_ROOT = ML_DIR.parent                                 # repo root
DATA_DIR = REPO_ROOT / "data"
RAW_PAYLOAD_DIR = DATA_DIR / "raw_payloads"
ARTIFACT_DIR = ML_DIR / "artifacts"

DEFAULT_SEED = 42

# ---------------------------------------------------------------------------
# Feature categories (7) -> the 5 display pillars.
#
# The 7 engineering categories collapse into 5 Health-Card pillars. UPI/behavioural signal
# is folded into Cash Flow (it is alternate cash-flow activity); Utility/electricity folds
# into Business Stability, per architecture.md 7.1.
# ---------------------------------------------------------------------------
CATEGORY_CASH_FLOW = "cash_flow"
CATEGORY_GST = "gst"
CATEGORY_BUREAU = "bureau"
CATEGORY_BUSINESS = "business_stability"
CATEGORY_BEHAVIOURAL = "behavioural_digital"
CATEGORY_MACRO = "macro"
CATEGORY_UTILITY = "utility"

# pillar keys
PILLAR_CASH_FLOW = "cash_flow_stability"
PILLAR_GST = "gst_compliance_revenue"
PILLAR_BUSINESS = "business_stability"
PILLAR_BUREAU = "bureau_credit_history"
PILLAR_MACRO = "macroeconomic_context"

# category -> pillar mapping
CATEGORY_TO_PILLAR: dict[str, str] = {
    CATEGORY_CASH_FLOW: PILLAR_CASH_FLOW,
    CATEGORY_BEHAVIOURAL: PILLAR_CASH_FLOW,     # UPI activity == alternate cash-flow signal
    CATEGORY_GST: PILLAR_GST,
    CATEGORY_BUSINESS: PILLAR_BUSINESS,
    CATEGORY_UTILITY: PILLAR_BUSINESS,          # electricity folds into Business Stability
    CATEGORY_BUREAU: PILLAR_BUREAU,
    CATEGORY_MACRO: PILLAR_MACRO,
}

# Display weights when ALL data present (must sum to 100).
PILLAR_DISPLAY_WEIGHTS: dict[str, float] = {
    PILLAR_CASH_FLOW: 35.0,
    PILLAR_GST: 30.0,
    PILLAR_BUSINESS: 20.0,
    PILLAR_BUREAU: 10.0,
    PILLAR_MACRO: 5.0,
}

PILLAR_LABELS: dict[str, str] = {
    PILLAR_CASH_FLOW: "Cash Flow Stability",
    PILLAR_GST: "GST Compliance & Revenue",
    PILLAR_BUSINESS: "Business Stability",
    PILLAR_BUREAU: "Bureau & Credit History",
    PILLAR_MACRO: "Macroeconomic Context",
}

PILLAR_PRIMARY_SOURCE: dict[str, str] = {
    PILLAR_CASH_FLOW: "Account Aggregator",
    PILLAR_GST: "GST Network",
    PILLAR_BUSINESS: "Udyam / EPFO / Electricity",
    PILLAR_BUREAU: "Credit Bureau",
    PILLAR_MACRO: "RBI / PMI",
}

# Ordered list of pillars (display order)
PILLAR_ORDER = [
    PILLAR_CASH_FLOW,
    PILLAR_GST,
    PILLAR_BUSINESS,
    PILLAR_BUREAU,
    PILLAR_MACRO,
]

# ---------------------------------------------------------------------------
# Risk tiers (architecture.md 7.2). Boundaries are on the 0-100 score.
# ---------------------------------------------------------------------------
# (min_score_inclusive, tier_key, label, action, segment_label)
RISK_TIERS = [
    (90, "excellent", "Excellent", "Auto-approve (STP)", "disciplined"),
    (75, "good", "Good", "Approve with standard conditions", "disciplined"),
    (60, "fair", "Fair", "Manual review by RM (human-in-loop)", "review"),
    (40, "watch", "Watch", "Decline with improvement feedback", "non_disciplined"),
    (20, "risk", "Risk", "Decline; refer to secured product", "non_disciplined"),
    (0, "high_risk", "High Risk", "Decline; fraud review if warranted", "no_go"),
]


def tier_for_score(score: float) -> dict:
    """Map a 0-100 score to its risk tier record."""
    for min_score, key, label, action, segment in RISK_TIERS:
        if score >= min_score:
            return {
                "tier": key,
                "label": label,
                "action": action,
                "segment": segment,
                "min_score": min_score,
            }
    # score below 0 (shouldn't happen) -> high risk
    _, key, label, action, segment = RISK_TIERS[-1]
    return {"tier": key, "label": label, "action": action, "segment": segment, "min_score": 0}
