"""Helpers for redacting sensitive Lexus account data from logs."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

SENSITIVE_KEYS = {
    "access_token",
    "authorization",
    "id_token",
    "password",
    "refresh_token",
    "vin",
    "x-api-key",
    "api_key",
    "api-key",
    "guid",
    "x-guid",
    "deviceid",
    "device_id",
    "latitude",
    "longitude",
    "lat",
    "lon",
    "startlat",
    "startlon",
    "endlat",
    "endlon",
    "route",
    "location",
    "vehiclelocation",
    "message",
    "notifications",
    "notes",
    "servicingdealer",
    "serviceprovider",
}

FULLY_REDACTED_KEYS = {
    "latitude",
    "longitude",
    "lat",
    "lon",
    "startlat",
    "startlon",
    "endlat",
    "endlon",
    "route",
    "location",
    "vehiclelocation",
    "message",
    "notifications",
    "notes",
    "servicingdealer",
    "serviceprovider",
}


def redact_value(value: str | None, keep: int = 4) -> str:
    """Return a partially redacted string."""
    if not value:
        return ""
    if len(value) <= keep * 2:
        return "*" * len(value)
    return f"{value[:keep]}...{value[-keep:]}"


def redact_mapping(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Redact a mapping recursively."""
    redacted: dict[str, Any] = {}
    for key, value in payload.items():
        normalized_key = key.lower().replace("-", "_")
        if normalized_key in SENSITIVE_KEYS:
            redacted[key] = (
                "**REDACTED**"
                if normalized_key in FULLY_REDACTED_KEYS
                else redact_value(str(value))
            )
            continue

        if isinstance(value, Mapping):
            redacted[key] = redact_mapping(value)
            continue

        if isinstance(value, list):
            redacted[key] = [
                redact_mapping(item) if isinstance(item, Mapping) else item for item in value
            ]
            continue

        redacted[key] = value

    return redacted
