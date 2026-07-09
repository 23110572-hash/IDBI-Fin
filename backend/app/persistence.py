"""Persistence helpers over the ORM: PII masking, append-only ledger writes, portfolio/history
reads, and Mode-B monitoring (tier-crossing / score-drop alerts). PII is masked before storage."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import desc, select

from .db import session_scope
from .models import AlertRecord, ScoreLedgerEntry


def mask_pan(pan: str | None) -> str | None:
    if not pan or len(pan) < 5:
        return pan
    return pan[:2] + "*" * (len(pan) - 3) + pan[-1]


def mask_gstin(gstin: str | None) -> str | None:
    if not gstin or len(gstin) < 6:
        return gstin
    return gstin[:2] + "*" * (len(gstin) - 5) + gstin[-3:]


def record_score(identifiers: dict, result: dict, features: dict, availability: dict,
                 mode: str = "origination", consent_id: str | None = None,
                 note: str | None = None) -> dict:
    """Append a score to the ledger (never updated/deleted). Returns a serialisable summary."""
    card = result["health_card"]
    firm_meta = _infer_meta(identifiers)
    entry_id = result.get("score_id") or f"SC-{uuid.uuid4().hex[:16]}"
    sub_scores = {p["pillar"]: p["sub_score"] for p in card["pillars"]}
    # sanitise feature snapshot (JSON-safe; NaN -> None)
    snapshot = {k: (None if _is_nan(v) else float(v)) for k, v in features.items()}

    with session_scope() as s:
        entry = ScoreLedgerEntry(
            score_id=entry_id, urn=identifiers.get("urn"),
            business_name=identifiers.get("business_name"),
            consent_id=consent_id, mode=mode,
            model_version=card["model_version"], pd=card["pd"],
            composite_score=card["composite_score"], tier=card["tier"],
            tier_label=card["tier_label"], confidence=card["confidence"],
            sub_scores=sub_scores, reason_codes=card["reason_codes"], pillars=card["pillars"],
            available_sources=availability, feature_snapshot=snapshot,
            segment=firm_meta.get("segment"), sector=firm_meta.get("sector"),
        )
        s.add(entry)
    return {"score_id": entry_id, "mode": mode, "note": note}


def _infer_meta(identifiers: dict) -> dict:
    """Enterprise segment/sector for portfolio filtering (derived deterministically, same as the
    connectors), so ledger rows carry consistent metadata."""
    try:
        from .connectors.base import firm_for_identifiers
        firm = firm_for_identifiers(identifiers)
        return {"segment": firm.get("segment"), "sector": firm.get("sector")}
    except Exception:
        return {}


def get_portfolio() -> list[dict]:
    """Latest score per borrower (for the heat map)."""
    with session_scope() as s:
        rows = s.execute(select(ScoreLedgerEntry).order_by(desc(ScoreLedgerEntry.created_at))).scalars().all()
    latest: dict[str, dict] = {}
    for r in rows:
        if r.urn in latest:
            continue
        latest[r.urn] = {
            "urn": r.urn, "business_name": r.business_name, "score_id": r.score_id,
            "composite_score": r.composite_score, "tier": r.tier, "tier_label": r.tier_label,
            "pd": r.pd, "confidence": r.confidence, "segment": r.segment, "sector": r.sector,
            "sub_scores": r.sub_scores, "available_sources": r.available_sources,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
    return list(latest.values())


def get_history(urn: str) -> list[dict]:
    with session_scope() as s:
        rows = s.execute(
            select(ScoreLedgerEntry).where(ScoreLedgerEntry.urn == urn)
            .order_by(ScoreLedgerEntry.created_at)).scalars().all()
        return [{
            "score_id": r.score_id, "composite_score": r.composite_score, "tier": r.tier,
            "tier_label": r.tier_label, "pd": r.pd, "mode": r.mode,
            "model_version": r.model_version,
            "sub_scores": r.sub_scores, "reason_codes": r.reason_codes, "pillars": r.pillars,
            "available_sources": r.available_sources,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        } for r in rows]


def get_ledger_entry(score_id: str) -> dict | None:
    with session_scope() as s:
        r = s.execute(select(ScoreLedgerEntry).where(ScoreLedgerEntry.score_id == score_id)).scalar_one_or_none()
        if not r:
            return None
        return {
            "score_id": r.score_id, "urn": r.urn, "model_version": r.model_version,
            "pd": r.pd, "composite_score": r.composite_score, "tier": r.tier,
            "feature_snapshot": r.feature_snapshot, "reason_codes": r.reason_codes,
            "pillars": r.pillars, "available_sources": r.available_sources,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }


def create_alert(urn: str, atype: str, severity: str, message: str, action: str) -> dict:
    alert_id = f"AL-{uuid.uuid4().hex[:12]}"
    with session_scope() as s:
        s.add(AlertRecord(alert_id=alert_id, urn=urn, type=atype, severity=severity,
                          message=message, suggested_action=action))
    return {"alert_id": alert_id, "urn": urn, "type": atype, "severity": severity,
            "message": message, "suggested_action": action,
            "created_at": dt.datetime.now(dt.UTC).isoformat()}


def get_alerts(limit: int = 100) -> list[dict]:
    with session_scope() as s:
        rows = s.execute(select(AlertRecord).order_by(desc(AlertRecord.created_at)).limit(limit)).scalars().all()
        return [{"alert_id": r.alert_id, "urn": r.urn, "type": r.type, "severity": r.severity,
                 "message": r.message, "suggested_action": r.suggested_action,
                 "created_at": r.created_at.isoformat() if r.created_at else None} for r in rows]


def monitor_disbursed_borrowers(trigger: str = "daily_delta") -> dict:
    """Mode B: re-score each borrower in the ledger and alert on tier crossings / score drops >10.
    (In production this is restricted to disbursed accounts.)"""
    import asyncio

    from .orchestrator import orchestrate
    from .scoring_service import score_borrower

    alerts_created = 0
    scored = 0
    portfolio = get_portfolio()
    for b in portfolio:
        urn = b["urn"]
        prev_score = b["composite_score"]
        prev_tier = b["tier"]
        identifiers = {"urn": urn, "pan": "AAAAA0000A", "gstin": None,
                       "business_name": b.get("business_name")}
        try:
            bundle = asyncio.run(orchestrate(identifiers))
        except RuntimeError:  # already in an event loop
            loop = asyncio.new_event_loop()
            bundle = loop.run_until_complete(orchestrate(identifiers))
            loop.close()
        result = score_borrower(bundle["features"], bundle["availability"], include_scorecard=False)
        record_score(identifiers, result, bundle["features"], bundle["availability"],
                     mode="monitoring", note=trigger)
        scored += 1
        new = result["health_card"]
        if new["tier"] != prev_tier:
            create_alert(urn, "tier_crossing", "high",
                         f"Tier changed {prev_tier} -> {new['tier']}",
                         "Review borrower; reassess exposure.")
            alerts_created += 1
        elif prev_score - new["composite_score"] > 10:
            create_alert(urn, "score_drop", "medium",
                         f"Score dropped {prev_score:.0f} -> {new['composite_score']:.0f}",
                         "Investigate cash-flow / GST signals.")
            alerts_created += 1
    return {"trigger": trigger, "borrowers_scored": scored, "alerts_created": alerts_created}


def _is_nan(v) -> bool:
    try:
        return v is None or (isinstance(v, float) and v != v)
    except Exception:
        return True
