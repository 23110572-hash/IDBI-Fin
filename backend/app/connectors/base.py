"""Common connector interface + deterministic borrower synthesis from identifiers.

For the MVP there are no live AA/GST/EPFO APIs, so each connector deterministically *synthesises*
its source payload for a given borrower (seeded by a hash of the identifiers). This is NOT a
hardcoded demo: every identifier yields a distinct firm whose payloads flow through the real
feature pipeline + model, producing a freshly computed score each time. When live rails (AA/ULI,
GST) become available post-shortlist, only these connectors are swapped — the interface is stable.
"""
from __future__ import annotations

import hashlib
from functools import lru_cache
from typing import Protocol

import numpy as np

# msme_ml is installed as a package (pip install -e ../ml)
from msme_ml.generate import SECTORS, SEGMENTS, _one_firm
from msme_ml.schema import features_for_source

UNAVAILABLE = "UNAVAILABLE"
RawPayload = dict


class Connector(Protocol):
    source: str

    async def fetch(self, consent_token: str | None, identifiers: dict) -> RawPayload | str: ...


def _seed_from_identifiers(identifiers: dict) -> int:
    key = f"{identifiers.get('urn','')}|{identifiers.get('pan','')}|{identifiers.get('gstin','')}"
    digest = hashlib.sha256(key.encode()).hexdigest()
    return int(digest[:8], 16)


@lru_cache(maxsize=2048)
def _firm_for_seed(seed: int) -> dict:
    """Deterministically derive a full firm (65 features + metadata) from a seed."""
    rng = np.random.default_rng(seed)
    # segment/sector chosen with the same population priors as the generator
    segment = SEGMENTS[int(rng.choice(len(SEGMENTS), p=[0.80, 0.17, 0.03]))]
    sector = SECTORS[int(rng.choice(len(SECTORS), p=[0.28, 0.24, 0.22, 0.18, 0.08]))]
    idx = seed % 10_000_000
    return _one_firm(rng, segment, sector, idx)


def firm_for_identifiers(identifiers: dict) -> dict:
    return _firm_for_seed(_seed_from_identifiers(identifiers))


def source_hints(firm: dict, source: str) -> dict:
    """Pre-derived feature contributions for a source (attached to its raw payload as a hint block
    for the feature pipeline; hard features are still recomputed from raw by features.py)."""
    hints = {}
    for name in features_for_source(source):
        v = firm.get(name)
        if v is not None and not (isinstance(v, float) and np.isnan(v)):
            hints[name] = float(v)
    return hints
