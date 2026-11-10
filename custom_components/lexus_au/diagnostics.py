"""Redacted diagnostics for Lexus Connected AU."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import LexusAUCoordinator


def _iso(value: Any) -> str | None:
    """Return a timestamp as ISO text when available."""
    return value.isoformat() if value is not None else None


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return coordinator health without account credentials or location data."""
    coordinator: LexusAUCoordinator = hass.data[DOMAIN][entry.entry_id]
    snapshot = coordinator.data
    if snapshot is None:
        return {
            "coordinator": {"last_update_success": coordinator.last_update_success},
            "last_command": coordinator.client.last_command_result,
        }

    status = snapshot.status
    return {
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "last_exception_type": (
                type(coordinator.last_exception).__name__
                if coordinator.last_exception
                else None
            ),
            "update_interval_seconds": (
                coordinator.update_interval.total_seconds()
                if coordinator.update_interval
                else None
            ),
            "consecutive_poll_failures": coordinator._poll_failure_count,
        },
        "vehicle": {
            "model_name": snapshot.vehicle.model_name,
            "model_year": snapshot.vehicle.model_year,
        },
        "status": {
            "last_vehicle_update": _iso(status.last_vehicle_update),
            "location_available": (
                status.latitude is not None and status.longitude is not None
            ),
            "engine_running": status.engine_running,
            "all_doors_locked": status.all_doors_locked,
            "caution_count": status.caution_count,
        },
        "last_command": coordinator.client.last_command_result,
    }
