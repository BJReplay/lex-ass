"""Climate control entities for Lexus Connected AU."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import LexusAUCoordinator
from .entity import LexusAUEntity

_PRESET_MODES = ("none", "front_defrost", "rear_defrost", "both_defrost")


def _temperature(value: Any) -> float | None:
    if isinstance(value, dict):
        value = value.get("value")
    return float(value) if isinstance(value, (int, float)) else None


def _is_on(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.lower()
        if normalized in {"on", "true", "1"}:
            return True
        if normalized in {"off", "false", "0"}:
            return False
    return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Lexus climate entity."""
    coordinator: LexusAUCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([LexusAUClimate(coordinator)])


class LexusAUClimate(LexusAUEntity, ClimateEntity):
    """Control remote climate, target temperature, and defrost presets."""

    _attr_translation_key = "vehicle_climate"
    _attr_hvac_modes = (HVACMode.OFF, HVACMode.HEAT_COOL)
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.PRESET_MODE
    )
    _attr_preset_modes = _PRESET_MODES
    _attr_min_temp = 18
    _attr_max_temp = 29
    _attr_target_temperature_step = 1

    def __init__(self, coordinator: LexusAUCoordinator) -> None:
        """Initialize the Lexus climate entity."""
        super().__init__(coordinator, "vehicle_climate")
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS

    @property
    def hvac_mode(self) -> HVACMode:
        """Return the reported climate control state."""
        state = (self.coordinator.data.climate_status or {}).get("status")
        if state in {"starting", "running"}:
            return HVACMode.HEAT_COOL
        return HVACMode.OFF

    @property
    def current_temperature(self) -> float | None:
        """Return current cabin temperature when reported."""
        status = self.coordinator.data.climate_status or {}
        temperature = status.get("currentTemperature")
        unit = temperature.get("unit") if isinstance(temperature, dict) else None
        self._attr_temperature_unit = (
            UnitOfTemperature.FAHRENHEIT
            if isinstance(unit, str) and unit.upper().startswith("F")
            else UnitOfTemperature.CELSIUS
        )
        return _temperature(temperature)

    @property
    def target_temperature(self) -> float | None:
        """Return the saved target temperature."""
        settings = self.coordinator.data.climate_settings or {}
        temperature = settings.get("temperature")
        if temperature is None:
            temperature = (self.coordinator.data.climate_status or {}).get(
                "targetTemperature"
            )
        return _temperature(temperature)

    @property
    def preset_mode(self) -> str:
        """Return the active defrost preset based on saved settings."""
        heating = (self.coordinator.data.climate_settings or {}).get(
            "heatingOptions", {}
        )
        front = _is_on(heating.get("frontDefroster"))
        rear = _is_on(heating.get("rearDefogger"))
        if front and rear:
            return "both_defrost"
        if front:
            return "front_defrost"
        if rear:
            return "rear_defrost"
        return "none"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose current heating and seat settings for dashboards."""
        settings = self.coordinator.data.climate_settings or {}
        status = self.coordinator.data.climate_status or {}
        return {
            "duration_minutes": settings.get("duration") or status.get("duration"),
            "heating_options": settings.get("heatingOptions"),
            "seat_options": settings.get("seatOptions"),
            "climate_updated_at": status.get("updatedAt"),
        }

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set the target temperature and start climate control."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if not isinstance(temperature, (int, float)):
            return
        await self.coordinator.async_apply_climate_settings(
            temperature_override={
                "value": temperature,
                "unit": self._temperature_unit_code(),
            }
        )

    async def async_turn_on(self) -> None:
        """Start remote climate using the saved settings."""
        await self.coordinator.async_apply_climate_settings()

    async def async_turn_off(self) -> None:
        """Stop remote climate control."""
        await self.coordinator.async_stop_climate()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set front/rear defrost while preserving other climate settings."""
        if preset_mode not in _PRESET_MODES:
            return
        heating = {
            "frontDefroster": "on" if preset_mode in ("front_defrost", "both_defrost") else "off",
            "rearDefogger": "on" if preset_mode in ("rear_defrost", "both_defrost") else "off",
        }
        await self.coordinator.async_apply_climate_settings(
            heating_overrides=heating
        )

    def _temperature_unit_code(self) -> str:
        return "F" if self._attr_temperature_unit == UnitOfTemperature.FAHRENHEIT else "C"
