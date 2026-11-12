"""Typed models and payload parsers for Lexus Australia."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any


@dataclass(slots=True)
class LexusAUToken:
    """Authentication token set for the Lexus Australia backend."""

    access_token: str
    id_token: str
    refresh_token: str | None
    subject: str
    expires_at: datetime

    @property
    def is_expired(self) -> bool:
        """Return true when the token should no longer be used."""
        return datetime.now(UTC) >= self.expires_at

    @property
    def should_refresh(self) -> bool:
        """Return true shortly before token expiry."""
        return datetime.now(UTC) >= self.expires_at - timedelta(seconds=60)


@dataclass(slots=True)
class LexusAUVehicleOverview:
    """High-level information about the configured vehicle."""

    vin: str
    nickname: str | None = None
    model_name: str | None = None
    model_year: str | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def display_name(self) -> str:
        """Return the best available user-facing name."""
        if self.nickname:
            return self.nickname
        if self.model_name:
            return self.model_name
        return self.vin

    @classmethod
    def from_guid_payload(
        cls, payload: dict[str, Any], expected_vin: str
    ) -> "LexusAUVehicleOverview":
        """Best-effort parse of the `/v2/vehicle/guid` payload."""
        for candidate in _collect_objects(payload):
            vin = _pick_first_string(candidate, ("vin", "VIN"))
            if not vin or vin.upper() != expected_vin.upper():
                continue
            return cls(
                vin=vin,
                nickname=_pick_first_string(candidate, ("nickName", "nickname", "alias")),
                model_name=_pick_first_string(
                    candidate,
                    ("modelName", "vehicleModel", "model", "gradeName"),
                ),
                model_year=_pick_first_string(candidate, ("modelYear", "year")),
                raw=candidate,
            )

        return cls(vin=expected_vin, raw=payload)


@dataclass(slots=True)
class LexusAUDoorState:
    """State of an individual door or opening."""

    closed: bool | None = None
    locked: bool | None = None


@dataclass(slots=True)
class LexusAUStatus:
    """Normalized vehicle status derived from AU remote status payloads."""

    fetched_at: datetime
    latitude: float | None = None
    longitude: float | None = None
    location_display_name: str | None = None
    location_updated_at: datetime | None = None
    fuel_level: float | None = None
    fuel_level_unit: str | None = None
    distance_to_empty: float | None = None
    distance_to_empty_unit: str | None = None
    odometer: float | None = None
    odometer_unit: str | None = None
    trip_a: float | None = None
    trip_a_unit: str | None = None
    trip_b: float | None = None
    trip_b_unit: str | None = None
    speed: float | None = None
    speed_unit: str | None = None
    front_left_tire_pressure: float | None = None
    front_left_tire_pressure_unit: str | None = None
    front_right_tire_pressure: float | None = None
    front_right_tire_pressure_unit: str | None = None
    rear_left_tire_pressure: float | None = None
    rear_left_tire_pressure_unit: str | None = None
    rear_right_tire_pressure: float | None = None
    rear_right_tire_pressure_unit: str | None = None
    spare_tire_pressure: float | None = None
    spare_tire_pressure_unit: str | None = None
    tire_pressure_updated_at: datetime | None = None
    last_vehicle_update: datetime | None = None
    caution_count: int | None = None
    engine_running: bool | None = None
    all_doors_locked: bool | None = None
    driver_door_locked: bool | None = None
    door_states: dict[str, LexusAUDoorState] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "LexusAUStatus":
        """Create a normalized status object from an AU API payload."""
        status_payload = _status_payload(payload)
        latitude, longitude = _extract_location(status_payload)
        location_display_name = _extract_location_display_name(status_payload)
        location_updated_at = _extract_timestamp(
            status_payload,
            ("locationAcquisitionDatetime", "lastTimestamp"),
        )
        fuel_level, fuel_unit = _extract_numeric(status_payload, ("fuelLevel", "fugage"))
        distance_to_empty, distance_unit = _extract_numeric(
            status_payload, ("distanceToEmpty", "range", "rage")
        )
        odometer, odometer_unit = _extract_numeric(status_payload, ("odometer", "odo"))
        trip_a, trip_a_unit = _extract_trip_distance(status_payload, "Trip A")
        trip_b, trip_b_unit = _extract_trip_distance(status_payload, "Trip B")
        speed, speed_unit = _extract_numeric(status_payload, ("speed", "vehicleSpeed"))
        front_left_tire_pressure, front_left_tire_pressure_unit = _extract_numeric(
            status_payload,
            ("flTirePressure", "frontLeftTirePressure", "frontLeftTyrePressure"),
        )
        front_right_tire_pressure, front_right_tire_pressure_unit = _extract_numeric(
            status_payload,
            ("frTirePressure", "frontRightTirePressure", "frontRightTyrePressure"),
        )
        rear_left_tire_pressure, rear_left_tire_pressure_unit = _extract_numeric(
            status_payload,
            ("rlTirePressure", "rearLeftTirePressure", "rearLeftTyrePressure"),
        )
        rear_right_tire_pressure, rear_right_tire_pressure_unit = _extract_numeric(
            status_payload,
            ("rrTirePressure", "rearRightTirePressure", "rearRightTyrePressure"),
        )
        spare_tire_pressure, spare_tire_pressure_unit = _extract_numeric(
            status_payload,
            ("spareTirePressure", "spareTyrePressure"),
        )
        tire_pressure_updated_at = _extract_timestamp(
            status_payload,
            ("tirePressureTimestamp", "tyrePressureTimestamp"),
        )
        last_vehicle_update = _extract_timestamp(
            status_payload,
            (
                "lastTimestamp",
                "timestamp",
                "occurrenceDate",
                "locationAcquisitionDatetime",
            ),
        )
        door_states = _extract_door_states(status_payload)
        all_doors_locked = _derive_all_doors_locked(door_states)
        driver_door_locked = _extract_driver_door_locked(door_states)

        return cls(
            fetched_at=datetime.now(UTC),
            latitude=latitude,
            longitude=longitude,
            location_display_name=location_display_name,
            location_updated_at=location_updated_at,
            fuel_level=fuel_level,
            fuel_level_unit=fuel_unit,
            distance_to_empty=distance_to_empty,
            distance_to_empty_unit=distance_unit,
            odometer=odometer,
            odometer_unit=odometer_unit,
            trip_a=trip_a,
            trip_a_unit=trip_a_unit,
            trip_b=trip_b,
            trip_b_unit=trip_b_unit,
            speed=speed,
            speed_unit=speed_unit,
            front_left_tire_pressure=front_left_tire_pressure,
            front_left_tire_pressure_unit=front_left_tire_pressure_unit,
            front_right_tire_pressure=front_right_tire_pressure,
            front_right_tire_pressure_unit=front_right_tire_pressure_unit,
            rear_left_tire_pressure=rear_left_tire_pressure,
            rear_left_tire_pressure_unit=rear_left_tire_pressure_unit,
            rear_right_tire_pressure=rear_right_tire_pressure,
            rear_right_tire_pressure_unit=rear_right_tire_pressure_unit,
            spare_tire_pressure=spare_tire_pressure,
            spare_tire_pressure_unit=spare_tire_pressure_unit,
            tire_pressure_updated_at=tire_pressure_updated_at,
            last_vehicle_update=last_vehicle_update,
            caution_count=_extract_int(status_payload, ("cautionOverallCount",)),
            engine_running=_extract_engine_state(status_payload),
            all_doors_locked=all_doors_locked,
            driver_door_locked=driver_door_locked,
            door_states=door_states,
            raw=status_payload,
        )


@dataclass(slots=True)
class LexusAUChargingStatus:
    """Charging and EV range values returned by the electric-status endpoint."""

    battery_level: float | None = None
    ev_range: float | None = None
    ev_range_with_ac: float | None = None
    ev_range_unit: str | None = None
    remaining_charge_time: int | None = None
    fuel_level: float | None = None
    fuel_range: float | None = None
    plug_status_code: int | None = None
    connector_status_code: int | None = None
    charge_type_code: int | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "LexusAUChargingStatus":
        """Parse charging details from the captured Lexus AU response."""
        body = _status_payload(payload)
        vehicle_info = body.get("vehicleInfo")
        charge_info = (
            vehicle_info.get("chargeInfo")
            if isinstance(vehicle_info, dict)
            else body.get("chargeInfo")
        )
        if not isinstance(charge_info, dict):
            return cls()

        remaining_charge_time = _optional_int(charge_info.get("remainingChargeTime"))
        if remaining_charge_time is not None and remaining_charge_time > 1440:
            remaining_charge_time = None

        return cls(
            battery_level=_optional_number(charge_info.get("chargeRemainingAmount")),
            ev_range=_optional_number(charge_info.get("evTravelableDistance")),
            ev_range_with_ac=_optional_number(charge_info.get("evDistanceAC")),
            ev_range_unit=_pick_first_string(charge_info, ("evDistanceUnit",)),
            remaining_charge_time=remaining_charge_time,
            fuel_level=_optional_number(charge_info.get("fuelGage")),
            fuel_range=_optional_number(charge_info.get("gasolineTravelableDistance")),
            plug_status_code=_optional_int(charge_info.get("plugStatus")),
            connector_status_code=_optional_int(charge_info.get("connectorStatus")),
            charge_type_code=_optional_int(charge_info.get("chargeType")),
        )

    @property
    def total_range(self) -> float | None:
        """Return gasoline range plus EV range with climate, when reported."""
        ev_range = self.ev_range_with_ac
        if ev_range is None and self.fuel_range is None:
            return None
        return (ev_range if ev_range is not None else 0) + (
            self.fuel_range if self.fuel_range is not None else 0
        )

    @property
    def total_range_unit(self) -> str | None:
        """Return the vehicle's selected distance unit for the combined range."""
        return self.ev_range_unit


@dataclass(slots=True)
class LexusAUClimateOperation:
    """Availability and current enabled state of one climate operation."""

    name: str
    display_name: str | None = None
    available: bool | None = None
    enabled: bool | None = None


@dataclass(slots=True)
class LexusAUClimateOperationCategory:
    """A group of climate operations such as defrost or seat heat."""

    name: str
    display_name: str | None = None
    available: bool | None = None
    operations: list[LexusAUClimateOperation] = field(default_factory=list)


@dataclass(slots=True)
class LexusAUClimateSettings:
    """Read-only temperature and operation settings from the climate endpoint."""

    temperature: float | None = None
    temperature_unit: str | None = None
    min_temperature: float | None = None
    max_temperature: float | None = None
    temperature_interval: float | None = None
    settings_on: bool | None = None
    extended_runtime_available: bool | None = None
    extended_runtime_enabled: bool | None = None
    operations: list[LexusAUClimateOperationCategory] = field(default_factory=list)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "LexusAUClimateSettings":
        """Parse climate settings and their available operations."""
        body = _status_payload(payload)
        extended_runtime = body.get("extendedRuntime")
        if not isinstance(extended_runtime, dict):
            extended_runtime = {}

        categories: list[LexusAUClimateOperationCategory] = []
        raw_categories = body.get("acOperations")
        if isinstance(raw_categories, list):
            for raw_category in raw_categories:
                if not isinstance(raw_category, dict):
                    continue
                category_name = raw_category.get("categoryName")
                if not isinstance(category_name, str):
                    continue

                operations: list[LexusAUClimateOperation] = []
                raw_operations = raw_category.get("acParameters")
                if isinstance(raw_operations, list):
                    for raw_operation in raw_operations:
                        if not isinstance(raw_operation, dict):
                            continue
                        operation_name = raw_operation.get("name")
                        if not isinstance(operation_name, str):
                            continue
                        operations.append(
                            LexusAUClimateOperation(
                                name=operation_name,
                                display_name=_optional_string(
                                    raw_operation.get("displayName")
                                ),
                                available=_optional_bool(
                                    raw_operation.get("available")
                                ),
                                enabled=_optional_bool(raw_operation.get("enabled")),
                            )
                        )

                categories.append(
                    LexusAUClimateOperationCategory(
                        name=category_name,
                        display_name=_optional_string(
                            raw_category.get("categoryDisplayName")
                        ),
                        available=_optional_bool(raw_category.get("available")),
                        operations=operations,
                    )
                )

        return cls(
            temperature=_optional_number(body.get("temperature")),
            temperature_unit=_optional_string(body.get("temperatureUnit")),
            min_temperature=_optional_number(body.get("minTemp")),
            max_temperature=_optional_number(body.get("maxTemp")),
            temperature_interval=_optional_number(body.get("tempInterval")),
            settings_on=_optional_bool(body.get("settingsOn")),
            extended_runtime_available=_optional_bool(
                extended_runtime.get("available")
            ),
            extended_runtime_enabled=_optional_bool(extended_runtime.get("enabled")),
            operations=categories,
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return serializable read-only climate capabilities for Home Assistant."""
        return {
            "settings_on": self.settings_on,
            "min_temperature": self.min_temperature,
            "max_temperature": self.max_temperature,
            "temperature_interval": self.temperature_interval,
            "extended_runtime_available": self.extended_runtime_available,
            "extended_runtime_enabled": self.extended_runtime_enabled,
            "ac_operations": [
                {
                    "name": category.name,
                    "display_name": category.display_name,
                    "available": category.available,
                    "operations": [
                        {
                            "name": operation.name,
                            "display_name": operation.display_name,
                            "available": operation.available,
                            "enabled": operation.enabled,
                        }
                        for operation in category.operations
                    ],
                }
                for category in self.operations
            ],
        }


@dataclass(slots=True)
class LexusAUSnapshot:
    """Coordinator payload for Home Assistant."""

    vehicle: LexusAUVehicleOverview
    status: LexusAUStatus
    charging: LexusAUChargingStatus | None = None
    climate_settings: LexusAUClimateSettings | None = None
    refresh_request: dict[str, Any] | None = None


def _status_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the nested AU status payload when present."""
    nested_payload = payload.get("payload")
    if isinstance(nested_payload, dict):
        return nested_payload
    return payload


def _collect_objects(value: Any) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []

    if isinstance(value, dict):
        objects.append(value)
        for nested in value.values():
            objects.extend(_collect_objects(nested))
        return objects

    if isinstance(value, list):
        for item in value:
            objects.extend(_collect_objects(item))

    return objects


def _pick_first_string(candidate: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = candidate.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _optional_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _optional_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _optional_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _parse_numeric(candidate: Any) -> tuple[float | None, str | None]:
    if candidate is None:
        return None, None

    if isinstance(candidate, (int, float)):
        return float(candidate), None

    if isinstance(candidate, dict):
        value = candidate.get("value")
        if isinstance(value, (int, float)):
            unit = candidate.get("unit") or candidate.get("uom")
            return float(value), unit

    return None, None


def _extract_numeric(
    payload: dict[str, Any], keys: tuple[str, ...]
) -> tuple[float | None, str | None]:
    for candidate in _collect_objects(payload):
        for key in keys:
            if key not in candidate:
                continue
            value, unit = _parse_numeric(candidate[key])
            if value is not None:
                return value, unit

    return None, None


def _extract_location(payload: dict[str, Any]) -> tuple[float | None, float | None]:
    for candidate in _collect_objects(payload):
        latitude = candidate.get("latitude")
        longitude = candidate.get("longitude")
        if isinstance(latitude, (int, float)) and isinstance(longitude, (int, float)):
            return float(latitude), float(longitude)

    return None, None


def _extract_location_display_name(payload: dict[str, Any]) -> str | None:
    for candidate in _collect_objects(payload):
        display_name = _pick_first_string(
            candidate,
            ("displayName", "display_name", "locationName", "location_name"),
        )
        if display_name:
            return display_name
    return None


def _extract_timestamp(
    payload: dict[str, Any], keys: tuple[str, ...]
) -> datetime | None:
    for candidate in _collect_objects(payload):
        for key in keys:
            raw_value = candidate.get(key)
            if not isinstance(raw_value, str):
                continue

            for normalized in (raw_value, raw_value.replace("Z", "+00:00")):
                try:
                    return datetime.fromisoformat(normalized)
                except ValueError:
                    continue

    return None


def _extract_int(payload: dict[str, Any], keys: tuple[str, ...]) -> int | None:
    for candidate in _collect_objects(payload):
        for key in keys:
            raw_value = candidate.get(key)
            if isinstance(raw_value, bool):
                continue
            if isinstance(raw_value, int):
                return raw_value
            if isinstance(raw_value, str):
                try:
                    return int(raw_value)
                except ValueError:
                    continue
    return None


def _extract_engine_state(payload: dict[str, Any]) -> bool | None:
    for candidate in _collect_objects(payload):
        if "running" in candidate and isinstance(candidate["running"], bool):
            return candidate["running"]

        if "value" in candidate:
            continue

        status = candidate.get("status")
        if status in ("1", 1, True):
            return True
        if status in ("0", 0, False, "2"):
            return False

    return None


def _extract_trip_distance(
    payload: dict[str, Any],
    section_name: str,
) -> tuple[float | None, str | None]:
    raw_vehicle_status = payload.get("vehicleStatus")
    if not isinstance(raw_vehicle_status, list):
        return None, None

    for category in raw_vehicle_status:
        if not isinstance(category, dict) or category.get("category") != "Trip Details":
            continue

        sections = category.get("sections")
        if not isinstance(sections, list):
            continue

        for section in sections:
            if not isinstance(section, dict) or section.get("section") != section_name:
                continue

            values = section.get("values")
            if not isinstance(values, list) or not values:
                return None, None

            first_value = values[0].get("value") if isinstance(values[0], dict) else None
            if isinstance(first_value, (int, float)):
                return float(first_value), None
            if isinstance(first_value, str):
                return _parse_number_with_optional_unit(first_value)

    return None, None


def _parse_number_with_optional_unit(value: str) -> tuple[float | None, str | None]:
    parts = value.strip().split(maxsplit=1)
    if not parts:
        return None, None

    try:
        number = float(parts[0].replace(",", ""))
    except ValueError:
        return None, None

    unit = parts[1] if len(parts) > 1 else None
    return number, unit


_CATEGORY_SECTION_TO_KEY = {
    ("Driver Side", "Door"): "driver_side_door",
    ("Driver Side", "Window"): "driver_side_window",
    ("Passenger Side", "Door"): "passenger_side_door",
    ("Passenger Side", "Window"): "passenger_side_window",
    ("Driver Side", "Rear Door"): "rear_driver_side_door",
    ("Driver Side", "Rear Window"): "rear_driver_side_window",
    ("Passenger Side", "Rear Door"): "rear_passenger_side_door",
    ("Passenger Side", "Rear Window"): "rear_passenger_side_window",
    ("Other", "Hatch"): "hatch",
    ("Other", "Trunk"): "trunk",
    ("Other", "Bonnet"): "bonnet",
    ("Other", "Hood"): "bonnet",
    ("Other", "Moonroof"): "moonroof",
}


def _extract_door_states(payload: dict[str, Any]) -> dict[str, LexusAUDoorState]:
    door_states: dict[str, LexusAUDoorState] = {}
    raw_vehicle_status = payload.get("vehicleStatus")
    if not isinstance(raw_vehicle_status, list):
        return door_states

    for category in raw_vehicle_status:
        if not isinstance(category, dict):
            continue

        category_label = category.get("category")
        sections = category.get("sections")
        if not isinstance(category_label, str) or not isinstance(sections, list):
            continue

        for section in sections:
            if not isinstance(section, dict):
                continue

            section_label = section.get("section")
            if not isinstance(section_label, str):
                continue

            mapped_key = _CATEGORY_SECTION_TO_KEY.get((category_label, section_label))
            if mapped_key is None:
                continue

            values = section.get("values")
            if not isinstance(values, list) or not values:
                continue

            closed = None
            locked = None

            first_value = values[0].get("value") if isinstance(values[0], dict) else None
            if isinstance(first_value, str):
                normalized = first_value.lower()
                if normalized == "closed":
                    closed = True
                elif normalized in {"open", "opened"}:
                    closed = False

            if len(values) > 1 and isinstance(values[1], dict):
                second_value = values[1].get("value")
                if isinstance(second_value, str):
                    normalized = second_value.lower()
                    if normalized == "locked":
                        locked = True
                    elif normalized == "unlocked":
                        locked = False

            if closed is not None or locked is not None:
                door_states[mapped_key] = LexusAUDoorState(closed=closed, locked=locked)

    return door_states


def _derive_all_doors_locked(
    door_states: dict[str, LexusAUDoorState]
) -> bool | None:
    lock_values = [state.locked for state in door_states.values() if state.locked is not None]
    if not lock_values:
        return None
    return all(lock_values)


def _extract_driver_door_locked(
    door_states: dict[str, LexusAUDoorState]
) -> bool | None:
    driver_state = door_states.get("driver_side_door")
    if driver_state is None:
        return None
    return driver_state.locked
