"""Celery app + tasks.

  * Electricity enrichment (off the <30s critical path): OCR a bill -> recompute utility features
    -> append an updated score to the ledger.
  * Mode B (portfolio monitoring): daily AA delta / monthly full recompute / quarterly retrain,
    scheduled via Celery beat. These run ONLY for already-disbursed borrowers.

When no broker/worker is present, `task_always_eager=True` runs tasks inline so local dev works.
"""
from __future__ import annotations

import asyncio

from celery import Celery
from celery.schedules import crontab

from .config import get_settings

_settings = get_settings()

celery_app = Celery("msme", broker=_settings.celery_broker_url,
                    backend=_settings.celery_result_backend)
celery_app.conf.update(
    task_always_eager=_settings.celery_task_always_eager,
    task_serializer="json", result_serializer="json", accept_content=["json"],
    timezone="Asia/Kolkata",
)

celery_app.conf.beat_schedule = {
    "mode-b-daily-aa-delta": {"task": "app.tasks.mode_b_daily_delta",
                              "schedule": crontab(hour=2, minute=0)},
    "mode-b-monthly-recompute": {"task": "app.tasks.mode_b_monthly_recompute",
                                 "schedule": crontab(hour=3, minute=0, day_of_month=1)},
    "mode-b-quarterly-retrain": {"task": "app.tasks.mode_b_quarterly_retrain",
                                 "schedule": crontab(hour=4, minute=0, day_of_month=1,
                                                     month_of_year="1,4,7,10")},
}


@celery_app.task(name="app.tasks.enrich_with_electricity")
def enrich_with_electricity(urn: str, pan: str, gstin: str | None, bill_fields: dict) -> dict:
    """Re-score the borrower WITH the electricity source now available (async enrichment)."""
    from .persistence import record_score
    from .scoring_service import data_quality_report, score_borrower

    identifiers = {"urn": urn, "pan": pan, "gstin": gstin}
    bundle = asyncio.run(_orchestrate_with_electricity(identifiers))
    features, availability = bundle["features"], bundle["availability"]
    # Fold the ACTUAL uploaded bill's OCR values into the utility features so the enrichment is
    # driven by the document the user provided (not just the synthesized profile).
    _merge_bill_features(features, availability, bill_fields)
    dq = data_quality_report(features, availability)
    result = score_borrower(features, availability)
    record_score(identifiers, result, features, availability, mode="monitoring",
                 note="electricity_enrichment")
    return {"score_id": result["score_id"],
            "composite_score": result["health_card"]["composite_score"],
            "health_card": result["health_card"],
            "bill_fields": bill_fields, "data_quality": dq}


async def _orchestrate_with_electricity(identifiers: dict) -> dict:
    from .orchestrator import orchestrate
    return await orchestrate(identifiers, include_electricity=True)


def _merge_bill_features(features: dict, availability: dict, bill_fields: dict) -> None:
    """Derive the 5 Utility features from a single uploaded bill and mark electricity available.

    A single bill can't give a trend/volatility, so those use neutral values; the utilisation ratio
    is computed from the real OCR'd units + sanctioned load.
    """
    units = bill_fields.get("units_consumed_kwh")
    load = bill_fields.get("sanctioned_load_kw")
    if units is None:
        return
    if load and load > 0:
        features["sanctioned_load_utilisation"] = float(min(units / (load * 730.0), 1.0))
    features["electricity_consumption_trend"] = 0.0          # neutral (one data point)
    features["consumption_volatility"] = 0.2                 # neutral
    features["bill_payment_regularity"] = 1.0                # a bill was produced
    features.setdefault("consumption_vs_turnover_consistency", 0.7)
    availability["electricity"] = True


@celery_app.task(name="app.tasks.mode_b_daily_delta")
def mode_b_daily_delta() -> dict:
    """Daily AA delta: re-score disbursed borrowers; emit alerts on tier crossings / score drops."""
    from .persistence import monitor_disbursed_borrowers
    return monitor_disbursed_borrowers(trigger="daily_delta")


@celery_app.task(name="app.tasks.mode_b_monthly_recompute")
def mode_b_monthly_recompute() -> dict:
    from .persistence import monitor_disbursed_borrowers
    return monitor_disbursed_borrowers(trigger="monthly_full")


@celery_app.task(name="app.tasks.mode_b_quarterly_retrain")
def mode_b_quarterly_retrain() -> dict:
    """Placeholder hook: production triggers a SageMaker retrain + PSI review job."""
    return {"status": "retrain_trigger_recorded", "note": "wired to MLOps pipeline in production"}
