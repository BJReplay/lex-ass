"""Data coordinator for Lexus Connected AU."""

from __future__ import annotations

import asyncio
import logging
import random
import re
from collections.abc import Callable
from datetime import timedelta
from time import monotonic
from typing import Any

import httpx
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import LexusAUAuthError, LexusAUClient, LexusAURequestError, LexusAUSnapshot
from .const import (
    BACKGROUND_POLL_JITTER_RATIO,
    BACKGROUND_POLL_MAX_BACKOFF_FACTOR,
    COMMAND_CONFIRMATION_POLL_INTERVAL_SECONDS,
    COMMAND_CONFIRMATION_TIMEOUT_SECONDS,
    CONF_REFRESH_INTERVAL_SECONDS,
    DEFAULT_REFRESH_INTERVAL_SECONDS,
    DOMAIN,
)

LOGGER = logging.getLogger(__name__)

SnapshotPredicate = Callable[[LexusAUSnapshot], bool]


def _seat_write_options(options: dict[str, Any]) -> dict[str, str]:
    """Translate reported seat levels into climate-control write modes."""
    result: dict[str, str] = {}
    for key, value in options.items():
        if value == "off":
            result[key] = "off"
        elif value in {"low", "medium", "high", "heater"}:
            result[key] = "heater"
        elif value == "ventilation":
            result[key] = value
    return result


def _climate_command_failed(response: dict[str, Any]) -> bool:
    if response.get("errors"):
        return True
    payload = response.get("payload")
    return_code = payload.get("returnCode") if isinstance(payload, dict) else None
    if return_code is not None and return_code != "000000":
        return True
    status = response.get("status")
    if isinstance(status, str):
        return status.lower() in {"error", "failed", "rejected"}
    if isinstance(status, dict):
        messages = status.get("messages")
        if isinstance(messages, list):
            return any(
                isinstance(message, dict)
                and isinstance(message.get("responseCode"), str)
                and re.search(r"(?<!\d)[45]\d{2}(?!\d)", message["responseCode"])
                is not None
                for message in messages
            )
    return False


class LexusAUCoordinator(DataUpdateCoordinator[LexusAUSnapshot]):
    """Coordinate Lexus Australia status polling and commands."""

    def __init__(
        self,
        hass,
        entry: ConfigEntry,
        client: LexusAUClient,
    ) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self.client = client
        self._command_confirmation_task: asyncio.Task | None = None
        self._last_odometer: float | None = None
        self._driving_since_last_poll: bool | None = None
        self._base_refresh_interval_seconds = entry.options.get(
            CONF_REFRESH_INTERVAL_SECONDS,
            DEFAULT_REFRESH_INTERVAL_SECONDS,
        )
        self._poll_failure_count = 0
        update_interval = timedelta(
            seconds=self._next_background_poll_seconds(),
        )
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=update_interval,
            always_update=False,
        )

    async def _async_update_data(self) -> LexusAUSnapshot:
        """Fetch the latest vehicle snapshot."""
        try:
            snapshot = await self.client.async_get_snapshot()
        except LexusAUAuthError as err:
            self._apply_next_background_poll(success=False)
            raise ConfigEntryAuthFailed from err
        except (LexusAURequestError, httpx.HTTPError) as err:
            self._apply_next_background_poll(success=False)
            raise UpdateFailed(str(err)) from err
        else:
            odometer = snapshot.status.odometer
            if odometer is not None:
                self._driving_since_last_poll = (
                    None
                    if self._last_odometer is None
                    else odometer > self._last_odometer
                )
                self._last_odometer = odometer
            self._apply_next_background_poll(success=True)
            return snapshot

    async def async_refresh_vehicle(self) -> None:
        """Request a fresh upload from the vehicle, then refresh coordinator data."""
        await self._async_request_remote_refresh()
        await self.async_request_refresh()

    async def async_refresh_electric_realtime_status(self) -> None:
        """Request fresh electric data and update coordinator state."""
        await self.client.async_refresh_electric_realtime_status()
        await self.async_request_refresh()

    async def async_refresh_recent_trips(self) -> None:
        """Fetch fresh trip history and update coordinator state."""
        await self.client.async_refresh_recent_trips()
        await self.async_request_refresh()

    async def async_set_climate(self, body: dict[str, Any]) -> None:
        """Send a climate command and reject an explicit backend failure."""
        response = await self.client.async_set_climate(body)
        if _climate_command_failed(response):
            raise HomeAssistantError("Lexus rejected the climate-control command.")
        try:
            await self.client.async_refresh_climate_status()
        except (LexusAURequestError, httpx.HTTPError) as err:
            LOGGER.debug("Climate status refresh request failed: %s", err)
        await self.async_request_refresh()

    async def async_apply_climate_settings(
        self,
        *,
        heating_overrides: dict[str, str] | None = None,
        seat_overrides: dict[str, str] | None = None,
        temperature_override: dict[str, Any] | None = None,
    ) -> None:
        """Start climate with current settings preserved and requested overrides."""
        settings = self.data.climate_settings or {}
        body: dict[str, Any] = {
            "command": "start",
            "duration": settings.get("duration"),
            "temperature": temperature_override or settings.get("temperature"),
            "heatingOptions": dict(settings.get("heatingOptions") or {}),
            "seatOptions": _seat_write_options(
                dict(settings.get("seatOptions") or {})
            ),
            "saveSettings": True,
        }
        body["heatingOptions"].update(heating_overrides or {})
        body["seatOptions"].update(seat_overrides or {})
        await self.async_set_climate(
            {key: value for key, value in body.items() if value is not None}
        )

    async def async_stop_climate(self) -> None:
        """Stop remote climate control."""
        await self.async_set_climate({"command": "stop"})

    async def async_shutdown(self) -> None:
        """Cancel outstanding background work."""
        await self._async_cancel_command_confirmation_task()

    async def async_lock_doors(self) -> None:
        """Lock the vehicle and confirm the updated state."""
        await self.client.async_lock_doors()
        await self._async_begin_command_confirmation(
            command_name="door lock",
            predicate=_snapshot_is_locked,
        )

    async def async_unlock_doors(self) -> None:
        """Unlock the vehicle and confirm the updated state."""
        await self.client.async_unlock_doors()
        await self._async_begin_command_confirmation(
            command_name="door unlock",
            predicate=_snapshot_is_unlocked,
        )

    async def async_engine_start(self) -> None:
        """Start the vehicle engine using the inferred AU command."""
        await self.client.async_start_engine_inferred()
        await self._async_begin_command_confirmation(
            command_name="engine start",
            predicate=lambda snapshot: snapshot.status.engine_running is True,
        )

    async def async_engine_stop(self) -> None:
        """Stop the vehicle engine using the inferred AU command."""
        await self.client.async_stop_engine_inferred()
        await self._async_begin_command_confirmation(
            command_name="engine stop",
            predicate=lambda snapshot: snapshot.status.engine_running is False,
        )

    async def async_lock_boot_trial(self) -> None:
        """Trial boot lock using the inferred AU command pattern."""
        await self.client.async_lock_boot_trial()
        await self._async_begin_command_confirmation(
            command_name="boot lock",
            predicate=_snapshot_is_boot_locked,
        )

    async def async_unlock_boot_trial(self) -> None:
        """Trial boot unlock using the inferred AU command pattern."""
        await self.client.async_unlock_boot_trial()
        await self._async_begin_command_confirmation(
            command_name="boot unlock",
            predicate=_snapshot_is_boot_unlocked,
        )

    async def async_flash_hazards(self) -> None:
        """Flash hazards using the confirmed command sequence."""
        await self.client.async_flash_hazards()
        await self.async_refresh_vehicle()

    async def async_flash_headlights_trial(self) -> None:
        """Trial the headlight flash command."""
        await self.client.async_flash_headlights_trial()

    async def async_sound_horn_trial(self) -> None:
        """Trial the horn command."""
        await self.client.async_sound_horn_trial()

    async def async_buzzer_warning_trial(self) -> None:
        """Trial the buzzer command."""
        await self.client.async_buzzer_warning_trial()

    async def _async_request_remote_refresh(self) -> None:
        """Request that the vehicle upload fresh state."""
        try:
            await self.client.async_refresh_remote_status()
        except LexusAURequestError as err:
            LOGGER.debug("Vehicle refresh request failed: %s", err)

    async def _async_begin_command_confirmation(
        self,
        *,
        command_name: str,
        predicate: SnapshotPredicate,
    ) -> None:
        """Run an immediate refresh, then keep polling briefly until the state matches."""
        await self._async_cancel_command_confirmation_task()
        await self.async_refresh_vehicle()

        if self.data is not None and predicate(self.data):
            LOGGER.debug("%s confirmed on immediate refresh", command_name)
            return

        LOGGER.debug(
            "Starting command confirmation polling for %s every %ss for up to %ss",
            command_name,
            COMMAND_CONFIRMATION_POLL_INTERVAL_SECONDS,
            COMMAND_CONFIRMATION_TIMEOUT_SECONDS,
        )
        self._command_confirmation_task = self.hass.async_create_task(
            self._async_command_confirmation_loop(
                command_name=command_name,
                predicate=predicate,
            )
        )

    async def _async_command_confirmation_loop(
        self,
        *,
        command_name: str,
        predicate: SnapshotPredicate,
    ) -> None:
        """Perform short-lived faster polling while waiting for a command result."""
        deadline = monotonic() + COMMAND_CONFIRMATION_TIMEOUT_SECONDS
        try:
            while monotonic() < deadline:
                await asyncio.sleep(COMMAND_CONFIRMATION_POLL_INTERVAL_SECONDS)
                await self.async_refresh_vehicle()

                if self.data is not None and predicate(self.data):
                    LOGGER.debug("%s confirmed during command confirmation polling", command_name)
                    return

            LOGGER.debug("%s confirmation polling timed out", command_name)
        except asyncio.CancelledError:
            LOGGER.debug("%s confirmation polling cancelled", command_name)
            raise
        except (LexusAURequestError, httpx.HTTPError, UpdateFailed) as err:
            LOGGER.debug("%s confirmation polling failed: %s", command_name, err)
        finally:
            if self._command_confirmation_task is asyncio.current_task():
                self._command_confirmation_task = None

    async def _async_cancel_command_confirmation_task(self) -> None:
        """Cancel any existing command-confirmation poller."""
        task = self._command_confirmation_task
        if task is None:
            return

        self._command_confirmation_task = None
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    def _apply_next_background_poll(self, *, success: bool) -> None:
        """Update the coordinator interval using jitter and capped backoff."""
        if success:
            self._poll_failure_count = 0
        else:
            self._poll_failure_count += 1

        next_poll_seconds = self._next_background_poll_seconds()
        self.update_interval = timedelta(seconds=next_poll_seconds)
        LOGGER.debug(
            "Next background poll in %.1fs (success=%s, consecutive_failures=%d)",
            next_poll_seconds,
            success,
            self._poll_failure_count,
        )

    def _next_background_poll_seconds(self) -> float:
        """Calculate the next background poll using jitter and capped backoff."""
        backoff_factor = min(
            2 ** self._poll_failure_count,
            BACKGROUND_POLL_MAX_BACKOFF_FACTOR,
        )
        interval_seconds = self._base_refresh_interval_seconds * backoff_factor
        jitter_window = interval_seconds * BACKGROUND_POLL_JITTER_RATIO
        if jitter_window <= 0:
            return float(interval_seconds)
        return max(
            1.0,
            interval_seconds + random.uniform(-jitter_window, jitter_window),
        )


def _snapshot_is_locked(snapshot: LexusAUSnapshot) -> bool:
    """Return true when the current snapshot shows the vehicle locked."""
    status = snapshot.status
    return status.all_doors_locked is True or status.driver_door_locked is True


def _snapshot_is_unlocked(snapshot: LexusAUSnapshot) -> bool:
    """Return true when the current snapshot shows the vehicle unlocked."""
    status = snapshot.status
    if status.all_doors_locked is not None:
        return status.all_doors_locked is False
    return status.driver_door_locked is False


def _snapshot_is_boot_locked(snapshot: LexusAUSnapshot) -> bool:
    """Return true when the current snapshot shows the hatch or trunk locked."""
    for key in ("hatch", "trunk"):
        opening_state = snapshot.status.door_states.get(key)
        if opening_state and opening_state.locked is not None:
            return opening_state.locked is True
    return False


def _snapshot_is_boot_unlocked(snapshot: LexusAUSnapshot) -> bool:
    """Return true when the current snapshot shows the hatch or trunk unlocked."""
    for key in ("hatch", "trunk"):
        opening_state = snapshot.status.door_states.get(key)
        if opening_state and opening_state.locked is not None:
            return opening_state.locked is False
    return False
