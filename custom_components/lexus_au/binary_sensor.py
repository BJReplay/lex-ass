"""Binary sensor entities for Lexus Connected AU."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import LexusAUCoordinator
from .entity import LexusAUEntity


@dataclass(frozen=True, kw_only=True)
class LexusAUBinarySensorDescription(BinarySensorEntityDescription):
    """Description of a Lexus AU binary sensor."""

    opening_keys: tuple[str, ...]


BINARY_SENSORS: tuple[LexusAUBinarySensorDescription, ...] = (
    LexusAUBinarySensorDescription(
        key="driver_side_door",
        translation_key="driver_side_door",
        device_class=BinarySensorDeviceClass.DOOR,
        opening_keys=("driver_side_door",),
    ),
    LexusAUBinarySensorDescription(
        key="passenger_side_door",
        translation_key="passenger_side_door",
        device_class=BinarySensorDeviceClass.DOOR,
        opening_keys=("passenger_side_door",),
    ),
    LexusAUBinarySensorDescription(
        key="rear_driver_side_door",
        translation_key="rear_driver_side_door",
        device_class=BinarySensorDeviceClass.DOOR,
        opening_keys=("rear_driver_side_door",),
    ),
    LexusAUBinarySensorDescription(
        key="rear_passenger_side_door",
        translation_key="rear_passenger_side_door",
        device_class=BinarySensorDeviceClass.DOOR,
        opening_keys=("rear_passenger_side_door",),
    ),
    LexusAUBinarySensorDescription(
        key="driver_side_window",
        translation_key="driver_side_window",
        device_class=BinarySensorDeviceClass.WINDOW,
        opening_keys=("driver_side_window",),
    ),
    LexusAUBinarySensorDescription(
        key="passenger_side_window",
        translation_key="passenger_side_window",
        device_class=BinarySensorDeviceClass.WINDOW,
        opening_keys=("passenger_side_window",),
    ),
    LexusAUBinarySensorDescription(
        key="rear_driver_side_window",
        translation_key="rear_driver_side_window",
        device_class=BinarySensorDeviceClass.WINDOW,
        opening_keys=("rear_driver_side_window",),
    ),
    LexusAUBinarySensorDescription(
        key="rear_passenger_side_window",
        translation_key="rear_passenger_side_window",
        device_class=BinarySensorDeviceClass.WINDOW,
        opening_keys=("rear_passenger_side_window",),
    ),
    LexusAUBinarySensorDescription(
        key="boot",
        translation_key="boot",
        device_class=BinarySensorDeviceClass.DOOR,
        opening_keys=("hatch", "trunk"),
    ),
    LexusAUBinarySensorDescription(
        key="bonnet",
        translation_key="bonnet",
        device_class=BinarySensorDeviceClass.OPENING,
        opening_keys=("bonnet",),
    ),
    LexusAUBinarySensorDescription(
        key="moonroof",
        translation_key="moonroof",
        device_class=BinarySensorDeviceClass.OPENING,
        opening_keys=("moonroof",),
    ),
)

ENGINE_BINARY_SENSORS: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(
        key="engine_running",
        translation_key="engine_running",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:engine-outline",
    ),
)

VEHICLE_HEALTH_DESCRIPTION = BinarySensorEntityDescription(
    key="vehicle_health",
    translation_key="vehicle_health",
    device_class=BinarySensorDeviceClass.PROBLEM,
    entity_category=EntityCategory.DIAGNOSTIC,
    icon="mdi:car-wrench",
)

DRIVING_DESCRIPTION = BinarySensorEntityDescription(
    key="driving",
    translation_key="driving",
    device_class=BinarySensorDeviceClass.MOVING,
    entity_category=EntityCategory.DIAGNOSTIC,
    icon="mdi:car-brake-parking",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Lexus AU binary sensors."""
    coordinator: LexusAUCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            *(
                LexusAUBinarySensor(coordinator, description)
                for description in BINARY_SENSORS
            ),
            *(
                LexusAUEngineRunningBinarySensor(coordinator, description)
                for description in ENGINE_BINARY_SENSORS
            ),
            LexusAUVehicleHealthBinarySensor(coordinator, VEHICLE_HEALTH_DESCRIPTION),
            LexusAUDrivingStatusBinarySensor(coordinator, DRIVING_DESCRIPTION),
        ]
    )


class LexusAUBinarySensor(LexusAUEntity, BinarySensorEntity):
    """Binary sensor derived from the current Lexus AU status snapshot."""

    entity_description: LexusAUBinarySensorDescription

    def __init__(
        self,
        coordinator: LexusAUCoordinator,
        description: LexusAUBinarySensorDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return true when the opening is open."""
        status = self.coordinator.data.status
        for opening_key in self.entity_description.opening_keys:
            opening_state = status.door_states.get(opening_key)
            if opening_state is None or opening_state.closed is None:
                continue
            return opening_state.closed is False
        return None


class LexusAUEngineRunningBinarySensor(LexusAUEntity, BinarySensorEntity):
    """Binary sensor derived from the current remote engine status."""

    entity_description: BinarySensorEntityDescription

    def __init__(
        self,
        coordinator: LexusAUCoordinator,
        description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return true when remote engine status reports running."""
        return self.coordinator.data.status.engine_running


class LexusAUVehicleHealthBinarySensor(LexusAUEntity, BinarySensorEntity):
    """Report whether the health endpoint lists active vehicle warnings."""

    entity_description: BinarySensorEntityDescription

    def __init__(
        self,
        coordinator: LexusAUCoordinator,
        description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the health sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return true for reported warnings and unknown for absent data."""
        health = self.coordinator.data.vehicle_health
        if health is None:
            return None
        warnings = health.get("warning")
        return len(warnings) > 0 if isinstance(warnings, list) else None

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        """Expose the warning objects returned by the health endpoint."""
        health = self.coordinator.data.vehicle_health
        warnings = health.get("warning") if health else None
        return {"warnings": warnings} if isinstance(warnings, list) else None


class LexusAUDrivingStatusBinarySensor(LexusAUEntity, BinarySensorEntity):
    """Infer whether the odometer advanced between successful polls."""

    entity_description: BinarySensorEntityDescription

    def __init__(
        self,
        coordinator: LexusAUCoordinator,
        description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the driving status sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return movement inferred from consecutive odometer values."""
        return self.coordinator._driving_since_last_poll

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Explain that this is a poll-based signal, not live vehicle state."""
        return {
            "note": "Reports whether the odometer advanced since the previous successful poll; this is not a live driving signal."
        }
