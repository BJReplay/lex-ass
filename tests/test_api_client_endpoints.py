"""Tests for authenticated Lexus AU OneCDN requests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
import unittest
from uuid import UUID

import homeassistant  # noqa: F401  # Initialize HA's httpx alias before importing it.
import httpx

from lexus_au.api.client import LexusAUClient
from lexus_au.api.models import (
    LexusAUChargingStatus,
    LexusAUClimateSettings,
    LexusAUToken,
)
from lexus_au.sensor import LexusAUSensor, SENSORS


class TestOneCDNEndpoints(unittest.IsolatedAsyncioTestCase):
    """Keep OneCDN request behavior covered without contacting the service."""

    async def asyncSetUp(self) -> None:
        self.requests: list[httpx.Request] = []

        async def handler(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            if request.url.path.endswith("/electric/status"):
                return httpx.Response(
                    200,
                    json={
                        "payload": {
                            "vehicleInfo": {
                                "chargeInfo": {
                                    "chargeRemainingAmount": 93,
                                    "evTravelableDistance": 79.4,
                                    "evDistanceAC": 76.2,
                                    "evDistanceUnit": "km",
                                    "remainingChargeTime": 75,
                                    "gasolineTravelableDistance": 521,
                                    "gasolineTravelableDistanceUnit": 1,
                                }
                            }
                        }
                    },
                )
            return httpx.Response(
                200,
                json={
                    "payload": {
                        "temperature": 21.5,
                        "temperatureUnit": "C",
                        "settingsOn": True,
                        "acOperations": [],
                    }
                },
            )

        self.client = LexusAUClient(
            username="test@example.invalid",
            password="not-a-real-password",
            vin="TESTVIN0000000001",
            device_id="test-device",
            api_key="test-api-key",
            x_api_key="test-x-api-key",
        )
        await self.client._http.aclose()
        self.client._http = httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        )
        self.client._token = LexusAUToken(
            access_token="test-token",
            id_token="test-id-token",
            refresh_token=None,
            subject="test-guid",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        self.client._vehicle_overview.raw = {"generation": "21MM"}

    async def asyncTearDown(self) -> None:
        await self.client.async_close()

    async def test_gets_both_payloads_from_captured_host_with_auth_headers(self) -> None:
        charging = await self.client.async_get_electric_status()
        climate = await self.client.async_get_climate_settings()

        self.assertEqual(len(self.requests), 2)
        self.assertEqual(
            str(self.requests[0].url),
            "https://onecdn.telematicsct.com.au/oneapi/v3/electric/status",
        )
        self.assertEqual(
            str(self.requests[1].url),
            "https://onecdn.telematicsct.com.au/v1/remote/route/climate-settings",
        )
        for request in self.requests:
            self.assertEqual(request.method, "GET")
            self.assertEqual(request.headers["Authorization"], "Bearer test-token")
            self.assertEqual(request.headers["X-Api-Key"], "test-x-api-key")
            self.assertEqual(request.headers["VIN"], "TESTVIN0000000001")
            self.assertEqual(
                request.headers.get_list("VIN"),
                ["TESTVIN0000000001"],
            )
            self.assertEqual(request.headers["GENERATION"], "21MM")
            self.assertEqual(request.headers["User-Agent"], "okhttp/5.3.2")
            UUID(request.headers["X-CorrelationId"])

        self.assertEqual(charging.battery_level, 93)
        self.assertEqual(charging.total_range, 597.2)
        self.assertEqual(climate.temperature, 21.5)


class TestNewSensorEntities(unittest.TestCase):
    """Verify Home Assistant sensors expose the new snapshot data."""

    def test_new_sensor_entities_read_snapshot_values(self) -> None:
        snapshot = SimpleNamespace(
            charging=LexusAUChargingStatus(
                battery_level=93,
                ev_range=79.4,
                ev_range_with_ac=76.2,
                ev_range_unit="km",
                fuel_range=521,
            ),
            climate_settings=LexusAUClimateSettings.from_payload(
                {
                    "payload": {
                        "temperature": 21.5,
                        "temperatureUnit": "C",
                        "settingsOn": True,
                        "acOperations": [],
                    }
                }
            ),
        )
        coordinator = SimpleNamespace(
            data=snapshot,
            entry=SimpleNamespace(entry_id="test-entry"),
        )
        descriptions = {description.key: description for description in SENSORS}

        battery = LexusAUSensor(coordinator, descriptions["ev_battery_level"])
        ev_range = LexusAUSensor(coordinator, descriptions["ev_range"])
        total_range = LexusAUSensor(coordinator, descriptions["total_range"])
        climate = LexusAUSensor(
            coordinator,
            descriptions["climate_target_temperature"],
        )

        self.assertEqual(battery.native_value, 93)
        self.assertEqual(ev_range.native_value, 79.4)
        self.assertEqual(ev_range.native_unit_of_measurement, "km")
        self.assertEqual(total_range.native_value, 597.2)
        self.assertEqual(total_range.native_unit_of_measurement, "km")
        self.assertEqual(climate.native_value, 21.5)
        self.assertEqual(climate.native_unit_of_measurement, "°C")
        self.assertTrue(climate.extra_state_attributes["settings_on"])
