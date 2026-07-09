"""msme_ml — MSME Financial Health Card ML package.

Synthetic data generation, feature pipeline, seven-gate selection, XGBoost training,
SHAP explainability, WOE scorecard, and score composition for the IDBI Innovate 2026
Track 03 MSME Financial Health Card.

Design invariants (from architecture.md / tech.md):
  * Single XGBoost decision model -> one PD. PDs are NEVER blended.
  * Score = 100 * (1 - PD) -> 6 risk tiers.
  * SHAP: top-5 reason codes + 5 sub-scores (grouped by pillar, normalised 0-100).
  * WOE scorecard is a PARALLEL regulator-facing artifact; it never alters the PD.
  * Dynamic pillar weighting is a DASHBOARD concern; the model is never re-weighted.
"""

__version__ = "0.1.0"

# --- native OpenMP runtime guard -----------------------------------------------------
# On Windows several packages (numpy/MKL, xgboost, optbinning->ortools, shap->llvmlite) each ship
# their own OpenMP runtime (libiomp5md / libomp). When two are loaded into the same process the
# Intel runtime aborts with a duplicate-library access violation (exit 0xC0000005). Allowing the
# duplicate is the supported workaround. Set BEFORE any native lib is imported.
import os as _os  # noqa: E402
import sys as _sys  # noqa: E402

_os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

# Empirically safe load order on Windows: optbinning (-> ortools native) MUST load before pandas
# (-> numpy/pyarrow native), otherwise ortools aborts with an access violation. optbinning is only
# needed for TRAINING the WOE scorecard; the scoring/backend path never imports it. So:
#   * preload optbinning ONLY if pandas has not been imported yet (the training CLI enters here
#     before pandas, so the order is correct); if pandas is already loaded (scoring / arbitrary
#     scripts) we skip it — it isn't needed and loading it now would crash.
#   * always preload xgboost then shap (safe in either order relative to pandas).
if "pandas" not in _sys.modules:
    try:  # pragma: no cover - environment dependent
        __import__("optbinning")
    except Exception:
        pass
for _mod in ("xgboost", "shap"):
    try:  # pragma: no cover - environment dependent
        __import__(_mod)
    except Exception:
        pass
