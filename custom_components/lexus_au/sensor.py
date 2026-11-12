"""Sensor entities for Lexus Connected AU."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import LexusAUCoordinator
from .entity import LexusAUEntity


@dataclass(frozen=True, kw_only=True)
class LexusAUSensorDescription(SensorEntityDescription):
    """Description of a Lexus AU status sensor."""

    value_attr: str
    unit_attr: str | None = None
    section_attr: str = "status"
    attributes_attr: str | None = None


SENSORS: tuple[LexusAUSensorDescription, ...] = (
    LexusAUSensorDescription(
        key="last_vehicle_update",
        translation_key="last_vehicle_update",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_attr="last_vehicle_update",
    ),
    LexusAUSensorDescription(
        key="last_location_update",
        translation_key="last_location_update",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_attr="location_updated_at",
    ),
    LexusAUSensorDescription(
        key="location_name",
        translation_key="location_name",
        icon="mdi:map-marker",
        value_attr="location_display_name",
    ),
    LexusAUSensorDescription(
        key="fuel_level",
        translation_key="fuel_level",
        icon="mdi:gas-station",
        native_unit_of_measurement=PERCENTAGE,
        value_attr="fuel_level",
    ),
    LexusAUSensorDescription(
        key="distance_to_empty",
        translation_key="distance_to_empty",
        icon="mdi:map-marker-distance",
        value_attr="distance_to_empty",
        unit_attr="distance_to_empty_unit",
    ),
    LexusAUSensorDescription(
        key="odometer",
        translation_key="odometer",
        icon="mdi:counter",
        value_attr="odometer",
        unit_attr="odometer_unit",
    ),
    LexusAUSensorDescription(
        key="trip_a",
        translation_key="trip_a",
        icon="mdi:map-marker-path",
        value_attr="trip_a",
        unit_attr="trip_a_unit",
    ),
    LexusAUSensorDescription(
        key="trip_b",
        translation_key="trip_b",
        icon="mdi:map-marker-path",
        value_attr="trip_b",
        unit_attr="trip_b_unit",
    ),
    LexusAUSensorDescription(
        key="vehicle_speed",
        translation_key="vehicle_speed",
        icon="mdi:speedometer",
        value_attr="speed",
        unit_attr="speed_unit",
    ),
    LexusAUSensorDescription(
        key="caution_count",
        translation_key="caution_count",
        icon="mdi:alert-circle-outline",
        value_attr="caution_count",
    ),
    LexusAUSensorDescription(
        key="front_left_tire_pressure",
        translation_key="front_left_tire_pressure",
        device_class=SensorDeviceClass.PRESSURE,
        icon="mdi:car-tire-alert",
        value_attr="front_left_tire_pressure",
        unit_attr="front_left_tire_pressure_unit",
    ),
    LexusAUSensorDescription(
        key="front_right_tire_pressure",
        translation_key="front_right_tire_pressure",
        device_class=SensorDeviceClass.PRESSURE,
        icon="mdi:car-tire-alert",
        value_attr="front_right_tire_pressure",
        unit_attr="front_right_tire_pressure_unit",
    ),
    LexusAUSensorDescription(
        key="rear_left_tire_pressure",
        translation_key="rear_left_tire_pressure",
        device_class=SensorDeviceClass.PRESSURE,
        icon="mdi:car-tire-alert",
        value_attr="rear_left_tire_pressure",
        unit_attr="rear_left_tire_pressure_unit",
    ),
    LexusAUSensorDescription(
        key="rear_right_tire_pressure",
        translation_key="rear_right_tire_pressure",
        device_class=SensorDeviceClass.PRESSURE,
        icon="mdi:car-tire-alert",
        value_attr="rear_right_tire_pressure",
        unit_attr="rear_right_tire_pressure_unit",
    ),
    LexusAUSensorDescription(
        key="spare_tire_pressure",
        translation_key="spare_tire_pressure",
        device_class=SensorDeviceClass.PRESSURE,
        icon="mdi:car-tire-alert",
        value_attr="spare_tire_pressure",
        unit_attr="spare_tire_pressure_unit",
    ),
    LexusAUSensorDescription(
        key="last_tire_pressure_update",
        translation_key="last_tire_pressure_update",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_attr="tire_pressure_updated_at",
    ),
    LexusAUSensorDescription(
        key="ev_battery_level",
        translation_key="ev_battery_level",
        icon="mdi:car-electric",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
        value_attr="battery_level",
        section_attr="charging",
    ),
    LexusAUSensorDescription(
        key="ev_range",
        translation_key="ev_range",
        icon="mdi:map-marker-distance",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        value_attr="ev_range",
        unit_attr="ev_range_unit",
        section_attr="charging",
    ),
    LexusAUSensorDescription(
        key="ev_range_with_ac",
        translation_key="ev_range_with_ac",
        icon="mdi:map-marker-distance",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        value_attr="ev_range_with_ac",
        unit_attr="ev_range_unit",
        section_attr="charging",
    ),
    LexusAUSensorDescription(
        key="total_range",
        translation_key="total_range",
        icon="mdi:map-marker-distance",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        value_attr="total_range",
        unit_attr="total_range_unit",
        section_attr="charging",
    ),
    LexusAUSensorDescription(
        key="remaining_charge_time",
        translation_key="remaining_charge_time",
        icon="mdi:ev-station",
        native_unit_of_measurement="min",
        state_class=SensorStateClass.MEASUREMENT,
        value_attr="remaining_charge_time",
        section_attr="charging",
    ),
    LexusAUSensorDescription(
        key="plug_status_code",
        translation_key="plug_status_code",
        icon="mdi:ev-plug-type2",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_attr="plug_status_code",
        section_attr="charging",
    ),
    LexusAUSensorDescription(
        key="connector_status_code",
        translation_key="connector_status_code",
        icon="mdi:ev-plug-type2",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_attr="connector_status_code",
        section_attr="charging",
    ),
    LexusAUSensorDescription(
        key="charge_type_code",
        translation_key="charge_type_code",
        icon="mdi:ev-station",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_attr="charge_type_code",
        section_attr="charging",
    ),
    LexusAUSensorDescription(
        key="climate_target_temperature",
        translation_key="climate_target_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        icon="mdi:thermometer",
        state_class=SensorStateClass.MEASUREMENT,
        value_attr="temperature",
        section_attr="climate_settings",
        attributes_attr="extra_state_attributes",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Lexus AU status sensors."""
    coordinator: LexusAUCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        LexusAUSensor(coordinator, description) for description in SENSORS
    )


class LexusAUSensor(LexusAUEntity, SensorEntity):
    """A sensor derived from the current Lexus AU status snapshot."""

    entity_description: LexusAUSensorDescription

    def __init__(
        self,
        coordinator: LexusAUCoordinator,
        description: LexusAUSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        """Return the current sensor value."""
        section = getattr(
            self.coordinator.data,
            self.entity_description.section_attr,
        )
        if section is None:
            return None
        return getattr(section, self.entity_description.value_attr)

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return a dynamic unit when the payload provides one."""
        if self.entity_description.unit_attr is None:
            if self.entity_description.section_attr == "climate_settings":
                climate_settings = self.coordinator.data.climate_settings
                if climate_settings is not None:
                    if climate_settings.temperature_unit == "C":
                        return UnitOfTemperature.CELSIUS
                    if climate_settings.temperature_unit == "F":
                        return UnitOfTemperature.FAHRENHEIT
            return super().native_unit_of_measurement
        section = getattr(
            self.coordinator.data,
            self.entity_description.section_attr,
        )
        return (
            None
            if section is None
            else getattr(section, self.entity_description.unit_attr)
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional read-only endpoint data when configured."""
        if self.entity_description.attributes_attr is None:
            return None
        section = getattr(
            self.coordinator.data,
            self.entity_description.section_attr,
        )
        if section is None:
            return None
        return getattr(section, self.entity_description.attributes_attr)
