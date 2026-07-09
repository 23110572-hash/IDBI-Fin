"""Orchestrator — fires the real-time connectors in parallel after consent, enforces per-source
timeouts, degrades gracefully on partial failure, assembles the unified record, and derives the
65-feature vector via the shared feature pipeline."""
from __future__ import annotations

import asyncio
import time

from msme_ml.features import availability_map, extract_features

from .config import get_settings
from .connectors.base import UNAVAILABLE
from .connectors.synth import ELECTRICITY_CONNECTOR, REALTIME_CONNECTORS

_settings = get_settings()


async def _fetch_one(connector, consent_token: str | None, identifiers: dict, timeout: float):
    """Fetch a single source with a hard timeout; any failure -> UNAVAILABLE (graceful degrade)."""
    started = time.perf_counter()
    try:
        payload = await asyncio.wait_for(
            connector.fetch(consent_token, identifiers), timeout=timeout)
        status = "unavailable" if payload == UNAVAILABLE else "ok"
        return connector.source, payload, status, round((time.perf_counter() - started) * 1000)
    except TimeoutError:
        return connector.source, UNAVAILABLE, "timeout", round((time.perf_counter() - started) * 1000)
    except Exception as exc:  # never fail the whole request on one source
        return connector.source, UNAVAILABLE, f"error:{type(exc).__name__}", \
            round((time.perf_counter() - started) * 1000)


async def orchestrate(identifiers: dict, consent_token: str | None = None,
                      include_electricity: bool = False) -> dict:
    """Run Mode-A parallel acquisition -> unified record -> feature vector.

    Electricity is OFF the critical path by default (async OCR enrichment). Pass
    include_electricity=True only when a bill has already been processed.
    """
    timeout = _settings.connector_timeout_seconds
    connectors = list(REALTIME_CONNECTORS)
    if include_electricity:
        connectors.append(ELECTRICITY_CONNECTOR)

    results = await asyncio.gather(
        *[_fetch_one(c, consent_token, identifiers, timeout) for c in connectors])

    record: dict = {}
    diagnostics: list[dict] = []
    for source, payload, status, latency_ms in results:
        diagnostics.append({"source": source, "status": status, "latency_ms": latency_ms})
        if payload != UNAVAILABLE:
            record[source] = payload

    features = extract_features(record)
    availability = availability_map(record)
    return {
        "record": record,
        "features": features,
        "availability": availability,
        "diagnostics": diagnostics,
    }
