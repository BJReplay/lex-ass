"""Seat-heater select entities for Lexus Connected AU."""

from __future__ import annotations

from typing import Any, ClassVar

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import LexusAUCoordinator
from .entity import LexusAUEntity

_OPTIONS = ("off", "low", "medium", "high")
_SEATS = (
    ("driverSeat", "seat_heater_driver"),
    ("passengerSeat", "seat_heater_passenger"),
    ("rearDriverSeat", "seat_heater_rear_driver"),
    ("rearPassengerSeat", "seat_heater_rear_passenger"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up seat-heater selects for reported seats."""
    coordinator: LexusAUCoordinator = hass.data[DOMAIN][entry.entry_id]
    settings = coordinator.data.climate_settings or {}
    seats = settings.get("seatOptions")
    if not isinstance(seats, dict):
        return

    entities = [
        LexusAUSeatHeaterSelect(coordinator, field, key)
        for field, key in _SEATS
        if seats.get(field) in _OPTIONS
    ]
    async_add_entities(entities)


class LexusAUSeatHeaterSelect(LexusAUEntity, SelectEntity):
    """Control a reported seat-heater level."""

    _attr_options: ClassVar[list[str]] = list(_OPTIONS)
    entity_description: SelectEntityDescription

    def __init__(
        self, coordinator: LexusAUCoordinator, seat_field: str, key: str
    ) -> None:
        """Initialize a seat-heater select."""
        super().__init__(coordinator, key)
        self._seat_field = seat_field
        self.entity_description = SelectEntityDescription(
            key=key,
            translation_key=key,
            icon="mdi:car-seat-heater",
        )
        self._pending_option: str | None = None

    @property
    def current_option(self) -> str | None:
        """Return the requested option or the last reported seat level."""
        if self._pending_option is not None:
            return self._pending_option
        seats = (self.coordinator.data.climate_settings or {}).get("seatOptions", {})
        option = seats.get(self._seat_field) if isinstance(seats, dict) else None
        return option if option in _OPTIONS else None

    async def async_select_option(self, option: str) -> None:
        """Set a seat heater level through the climate-control endpoint."""
        if option not in _OPTIONS:
            raise HomeAssistantError(f"Unsupported seat-heater level: {option}")
        previous = self._pending_option
        self._pending_option = option
        self.async_write_ha_state()
        try:
            await self.coordinator.async_apply_climate_settings(
                seat_overrides={
                    self._seat_field: "off" if option == "off" else "heater"
                }
            )
        except Exception as err:
            self._pending_option = previous
            self.async_write_ha_state()
            if isinstance(err, HomeAssistantError):
                raise
            raise HomeAssistantError("Failed to set the seat heater") from err

    @callback
    def _handle_coordinator_update(self) -> None:
        """Clear the optimistic selection once the new mode is reported."""
        super()._handle_coordinator_update()
        if self._pending_option is None:
            return
        seats = (self.coordinator.data.climate_settings or {}).get("seatOptions", {})
        value = seats.get(self._seat_field) if isinstance(seats, dict) else None
        if value not in _OPTIONS:
            return
        if (value != "off") == (self._pending_option != "off"):
            self._pending_option = None
            self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Indicate that non-off settings request heater mode."""
        return {"control_mode": "heater" if self.current_option != "off" else "off"}
