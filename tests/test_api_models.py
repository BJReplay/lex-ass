"""Tests for parsed Lexus AU endpoint responses."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


_MODELS_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "lexus_au"
    / "api"
    / "models.py"
)
_SPEC = importlib.util.spec_from_file_location("lexus_au_api_models", _MODELS_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load model module from {_MODELS_PATH}")
_MODELS = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODELS
_SPEC.loader.exec_module(_MODELS)


class TestElectricStatusModel(unittest.TestCase):
    """Verify charging fields and sentinel handling."""

    def test_parses_nested_charge_info(self) -> None:
        status = _MODELS.LexusAUChargingStatus.from_payload(
            {
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
                            "plugStatus": 12,
                            "connectorStatus": 2,
                            "chargeType": 15,
                        }
                    }
                }
            }
        )

        self.assertEqual(status.battery_level, 93)
        self.assertEqual(status.ev_range, 79.4)
        self.assertEqual(status.ev_range_with_ac, 76.2)
        self.assertEqual(status.ev_range_unit, "km")
        self.assertEqual(status.remaining_charge_time, 75)
        self.assertEqual(status.total_range, 597.2)
        self.assertEqual(status.total_range_unit, "km")
        self.assertEqual(status.plug_status_code, 12)
        self.assertEqual(status.connector_status_code, 2)
        self.assertEqual(status.charge_type_code, 15)

    def test_omits_sentinel_and_invalid_optional_values(self) -> None:
        status = _MODELS.LexusAUChargingStatus.from_payload(
            {
                "payload": {
                    "vehicleInfo": {
                        "chargeInfo": {
                            "remainingChargeTime": 65535,
                            "chargeRemainingAmount": True,
                            "plugStatus": "unknown",
                        }
                    }
                }
            }
        )

        self.assertIsNone(status.remaining_charge_time)
        self.assertIsNone(status.battery_level)
        self.assertIsNone(status.plug_status_code)
        self.assertIsNone(status.total_range)


class TestClimateSettingsModel(unittest.TestCase):
    """Verify nested climate capability parsing."""

    def test_parses_temperature_and_ac_operations(self) -> None:
        settings = _MODELS.LexusAUClimateSettings.from_payload(
            {
                "payload": {
                    "temperature": 21.5,
                    "temperatureUnit": "C",
                    "minTemp": 18,
                    "maxTemp": 29,
                    "tempInterval": 0.5,
                    "settingsOn": True,
                    "extendedRuntime": {"available": False, "enabled": False},
                    "acOperations": [
                        {
                            "categoryName": "defrost",
                            "categoryDisplayName": "Defrost",
                            "available": True,
                            "acParameters": [
                                {
                                    "name": "frontDefrost",
                                    "displayName": "Front Defrost",
                                    "available": True,
                                    "enabled": False,
                                }
                            ],
                        }
                    ],
                }
            }
        )

        self.assertEqual(settings.temperature, 21.5)
        self.assertEqual(settings.temperature_unit, "C")
        self.assertTrue(settings.settings_on)
        self.assertEqual(settings.operations[0].name, "defrost")
        self.assertEqual(settings.operations[0].operations[0].name, "frontDefrost")
        self.assertFalse(settings.operations[0].operations[0].enabled)
        self.assertEqual(
            settings.extra_state_attributes["ac_operations"][0]["operations"][0][
                "available"
            ],
            True,
        )

    def test_missing_and_malformed_fields_remain_unknown(self) -> None:
        settings = _MODELS.LexusAUClimateSettings.from_payload(
            {"payload": {"temperature": "21", "settingsOn": 1}}
        )

        self.assertIsNone(settings.temperature)
        self.assertIsNone(settings.settings_on)
        self.assertEqual(settings.operations, [])


if __name__ == "__main__":
    unittest.main()
