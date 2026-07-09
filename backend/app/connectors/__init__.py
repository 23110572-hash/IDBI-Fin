"""Data-source connectors. AA-first, ULI-ready. Each implements the common interface
``fetch(consent_token, identifiers) -> RawPayload | UNAVAILABLE`` so a failing source degrades
gracefully instead of failing the request."""
