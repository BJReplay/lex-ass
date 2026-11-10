"""Additional vehicle, trip, service, and electric sensors."""

from __future__ import annotations

from datetime import date
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE
from homeassistant.helpers.entity import EntityCategory

from .coordinator import LexusAUCoordinator
from .entity import LexusAUEntity

_DESCRIPTIONS = (
    SensorEntityDescription(
        key="battery_level",
        translation_key="battery_level",
        icon="mdi:car-electric",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
    ),
    SensorEntityDescription(
        key="phev_usable_battery_level",
        translation_key="phev_usable_battery_level",
        icon="mdi:car-electric",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
    ),
    SensorEntityDescription(
        key="electric_range",
        translation_key="electric_range",
        icon="mdi:map-marker-distance",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="electric_range_with_ac",
        translation_key="electric_range_with_ac",
        icon="mdi:map-marker-distance",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="charging_status",
        translation_key="charging_status",
        icon="mdi:ev-station",
        device_class=SensorDeviceClass.ENUM,
        options=["charge_complete", "charging", "none", "plugged"],
    ),
    SensorEntityDescription(
        key="remaining_charge_time",
        translation_key="remaining_charge_time",
        icon="mdi:battery-clock",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="min",
    ),
    SensorEntityDescription(
        key="last_service",
        translation_key="last_service",
        icon="mdi:wrench-clock",
        device_class=SensorDeviceClass.DATE,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="service_history_count",
        translation_key="service_history_count",
        icon="mdi:file-document-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="notification_count",
        translation_key="notification_count",
        icon="mdi:message-alert-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="warning_lights",
        translation_key="warning_lights",
        icon="mdi:car-tire-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="cabin_temperature",
        translation_key="cabin_temperature",
        icon="mdi:thermometer",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="°C",
    ),
    SensorEntityDescription(
        key="recent_trips",
        translation_key="recent_trips",
        icon="mdi:map-marker-path",
    ),
    SensorEntityDescription(
        key="last_trip_score",
        translation_key="last_trip_score",
        icon="mdi:steering",
    ),
    SensorEntityDescription(
        key="average_speed_week",
        translation_key="average_speed_week",
        icon="mdi:speedometer",
        device_class=SensorDeviceClass.SPEED,
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


def _number(value: Any) -> float | int | None:
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _range_value(data: dict[str, Any], key: str) -> float | int | None:
    value = data.get(key)
    return _number(value.get("value")) if isinstance(value, dict) else None


def _service_records(coordinator: LexusAUCoordinator) -> list[dict[str, Any]]:
    return coordinator.data.service_history


def _service_date(record: dict[str, Any]) -> date | None:
    raw = record.get("serviceDate")
    if not isinstance(raw, str):
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def _latest_service(coordinator: LexusAUCoordinator) -> dict[str, Any] | None:
    dated = [
        (service_date, record)
        for record in _service_records(coordinator)
        if (service_date := _service_date(record)) is not None
    ]
    return max(dated, key=lambda item: item[0])[1] if dated else None


def _warnings(coordinator: LexusAUCoordinator) -> list[Any]:
    health = coordinator.data.vehicle_health or {}
    value = health.get("warning") or health.get("warningLights") or []
    return value if isinstance(value, list) else []


def _trip_card(trip: dict[str, Any]) -> dict[str, Any] | None:
    raw_summary = trip.get("summary")
    summary: dict[str, Any] = (
        raw_summary if isinstance(raw_summary, dict) else {}
    )
    start_lat, start_lon = summary.get("startLat"), summary.get("startLon")
    end_lat, end_lon = summary.get("endLat"), summary.get("endLon")
    if not summary or None in (start_lat, start_lon, end_lat, end_lon):
        return None
    stats = {
        key: summary[source]
        for key, source in (
            ("distance_m", "length"),
            ("duration_s", "duration"),
            ("average_speed_kmh", "averageSpeed"),
            ("fuel_consumption_ml", "fuelConsumption"),
            ("night_trip", "nightTrip"),
        )
        if summary.get(source) is not None
    }
    raw_route = trip.get("route")
    route = raw_route if isinstance(raw_route, list) else []
    route_points = [
        {
            key: point[key]
            for key in ("lat", "lon", "overspeed", "highway", "mode", "isEv")
            if point.get(key) is not None
        }
        for point in route
        if isinstance(point, dict)
        and point.get("lat") is not None
        and point.get("lon") is not None
    ]
    result: dict[str, Any] = {
        "id": trip.get("id"),
        "source": "lexus_au",
        "activity_type": "drive",
        "start_ts": summary.get("startTs"),
        "end_ts": summary.get("endTs"),
        "start": {"lat": start_lat, "lon": start_lon},
        "end": {"lat": end_lat, "lon": end_lon},
        "stats": stats,
        "route": route_points,
    }
    if trip.get("scores"):
        result["scores"] = trip["scores"]
    if trip.get("behaviours"):
        result["behaviours"] = trip["behaviours"]
    return result


class LexusAUExtraSensor(LexusAUEntity, SensorEntity):
    """Sensor backed by optional endpoint data in the coordinator snapshot."""

    entity_description: SensorEntityDescription

    def __init__(self, coordinator: LexusAUCoordinator, key: str) -> None:
        """Initialize an extra sensor by its description key."""
        super().__init__(coordinator, key)
        self.entity_description = next(item for item in _DESCRIPTIONS if item.key == key)

    @property
    def native_value(self) -> Any:
        """Return the normalized value for this extra sensor."""
        key = self.entity_description.key
        electric = self.coordinator.data.electric_status or {}
        if key in {"battery_level", "phev_usable_battery_level"}:
            source = "batteryLevel" if key == "battery_level" else "phevUsableBatteryLevel"
            return _number(electric.get(source))
        if key in {"electric_range", "electric_range_with_ac"}:
            source = "evRange" if key == "electric_range" else "evRangeWithAc"
            return _range_value(electric, source)
        if key == "charging_status":
            status = electric.get("chargingStatus")
            if not isinstance(status, str):
                return None
            normalized = status.lower().replace("-", "_").replace(" ", "_")
            return {"chargecomplete": "charge_complete"}.get(normalized, normalized)
        if key == "remaining_charge_time":
            value = _number(electric.get("remainingChargeTime"))
            if value is not None and value > 1440 and electric.get("chargingStatus") != "charging":
                return None
            return value
        if key == "last_service":
            latest = _latest_service(self.coordinator)
            return _service_date(latest) if latest else None
        if key == "service_history_count":
            return len(_service_records(self.coordinator))
        if key == "notification_count":
            return len(self.coordinator.data.notifications)
        if key == "warning_lights":
            return len(_warnings(self.coordinator))
        if key == "cabin_temperature":
            climate = self.coordinator.data.climate_status or {}
            return _range_value(climate, "currentTemperature")
        if key == "recent_trips":
            return sum(
                _trip_card(trip) is not None
                for trip in self.coordinator.data.recent_trips
            )
        if key == "last_trip_score":
            if not self.coordinator.data.recent_trips:
                return None
            scores = self.coordinator.data.recent_trips[0].get("scores") or {}
            return _number(scores.get("global"))
        if key == "average_speed_week":
            return _number((self.coordinator.data.trip_summary or {}).get("averageSpeed"))
        return None

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Use the unit reported by the API for range sensors."""
        if self.entity_description.key in {"electric_range", "electric_range_with_ac"}:
            source = "evRange" if self.entity_description.key == "electric_range" else "evRangeWithAc"
            value = (self.coordinator.data.electric_status or {}).get(source)
            unit = value.get("unit") if isinstance(value, dict) else None
            return unit if isinstance(unit, str) else None
        if self.entity_description.key == "cabin_temperature":
            temperature = (self.coordinator.data.climate_status or {}).get(
                "currentTemperature"
            )
            unit = temperature.get("unit") if isinstance(temperature, dict) else None
            if isinstance(unit, str) and unit.upper().startswith("F"):
                return "°F"
        if self.entity_description.key == "average_speed_week":
            summary = self.coordinator.data.trip_summary or {}
            return summary.get("averageSpeedUnit") or "km/h"
        return self.entity_description.native_unit_of_measurement

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return useful details for history and diagnostic sensors."""
        key = self.entity_description.key
        if key == "last_service":
            latest = _latest_service(self.coordinator)
            if latest is None:
                return None
            return {
                "odometer": latest.get("mileage"),
                "unit": latest.get("unit"),
                "service_category": latest.get("serviceCategory"),
                "service_provider": latest.get("serviceProvider"),
                "service_count": len(_service_records(self.coordinator)),
            }
        if key == "service_history_count":
            return {"services": _service_records(self.coordinator)}
        if key == "notification_count":
            vin = self.coordinator.client.vin
            masked_vin = f"...{vin[-6:]}"
            recent = []
            for item in self.coordinator.data.notifications[:5]:
                message = item.get("message")
                if isinstance(message, str):
                    message = message.replace(vin, masked_vin)
                recent.append(
                    {
                        "date": item.get("notificationDate") or item.get("date"),
                        "category": item.get("category"),
                        "type": item.get("type"),
                        "message": message,
                        "read": item.get("isRead", item.get("readTimestamp") is not None),
                    }
                )
            return {"latest": recent}
        if key == "warning_lights":
            return {"warnings": _warnings(self.coordinator)}
        if key == "recent_trips":
            trips = [
                card
                for trip in self.coordinator.data.recent_trips
                if (card := _trip_card(trip)) is not None
            ]
            return {"trips": trips}
        if key == "last_trip_score" and self.coordinator.data.recent_trips:
            trip = self.coordinator.data.recent_trips[0]
            return {
                "start_ts": (trip.get("summary") or {}).get("startTs"),
                "end_ts": (trip.get("summary") or {}).get("endTs"),
                "stats": (trip.get("summary") or {}),
                "scores": trip.get("scores"),
            }
        return None


EXTRA_SENSOR_KEYS = tuple(item.key for item in _DESCRIPTIONS)
