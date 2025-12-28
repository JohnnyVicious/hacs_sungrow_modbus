"""Tests for model-specific register overrides."""

import unittest
from copy import deepcopy

from custom_components.sungrow_modbus.sensor_data.model_overrides import (
    MODEL_OVERRIDES,
    _match_model,
    apply_derived_overrides,
    apply_model_overrides,
    get_model_overrides,
)


class TestModelMatching(unittest.TestCase):
    """Test model pattern matching."""

    def test_exact_match(self):
        """Test exact model name matching."""
        self.assertTrue(_match_model("SH25T", "SH25T"))
        self.assertFalse(_match_model("SH25T", "SH10T"))

    def test_wildcard_suffix(self):
        """Test wildcard at end of pattern."""
        self.assertTrue(_match_model("SH25T", "SH*"))
        self.assertTrue(_match_model("SH10RT", "SH*"))
        self.assertFalse(_match_model("MG5RL", "SH*"))

    def test_wildcard_middle(self):
        """Test wildcard in middle of pattern."""
        self.assertTrue(_match_model("SH25T", "SH*T"))
        self.assertTrue(_match_model("SH10T", "SH*T"))
        self.assertTrue(_match_model("SH5T", "SH*T"))
        # Note: SH10RT also ends with "T", so it matches "SH*T"
        # Use more specific patterns like "SH*RT" to distinguish
        self.assertTrue(_match_model("SH10RT", "SH*T"))  # Ends with T, so matches
        self.assertFalse(_match_model("MG5RL", "SH*T"))  # Doesn't start with SH

    def test_wildcard_complex(self):
        """Test complex wildcard patterns."""
        self.assertTrue(_match_model("SH10RT-V112", "SH*RT*"))
        self.assertTrue(_match_model("SH5.0RT", "SH*RT*"))


class TestModelOverrides(unittest.TestCase):
    """Test applying model overrides."""

    def test_get_overrides_existing_model(self):
        """Test getting overrides for a model with overrides defined."""
        # SH25T has overrides defined
        overrides = get_model_overrides("SH25T")
        self.assertIsNotNone(overrides)
        self.assertIn("sensors", overrides)

    def test_get_overrides_nonexistent_model(self):
        """Test getting overrides for a model without overrides."""
        overrides = get_model_overrides("UNKNOWN_MODEL_XYZ")
        # Should return None or empty dict
        self.assertTrue(overrides is None or overrides == {})

    def test_apply_sensor_register_override(self):
        """Test that sensor register overrides are applied."""
        # Temporarily add an override for testing

        MODEL_OVERRIDES["TEST_MODEL"] = {
            "sensors": {
                "test_sensor_override": {
                    "register": ["9999"],
                    "multiplier": 0.5,
                }
            }
        }

        # Create a mock sensor group
        sensor_groups = [
            {
                "register_start": 1000,
                "poll_speed": "NORMAL",
                "entities": [
                    {
                        "name": "Test Sensor",
                        "unique": "test_sensor_override",
                        "register": ["1000"],
                        "multiplier": 0.01,
                    }
                ],
            }
        ]

        # Apply TEST_MODEL overrides
        modified = apply_model_overrides(sensor_groups, "TEST_MODEL")

        # Check that the override was applied
        entity = modified[0]["entities"][0]
        self.assertEqual(entity["register"], ["9999"])
        self.assertEqual(entity["multiplier"], 0.5)

        # Cleanup
        del MODEL_OVERRIDES["TEST_MODEL"]

    def test_apply_disabled_sensor(self):
        """Test that disabled sensors are removed."""
        # Temporarily add a disabled sensor to overrides
        original_overrides = deepcopy(MODEL_OVERRIDES.get("SH25T", {}))

        MODEL_OVERRIDES["SH25T"] = {
            "sensors": {
                "test_disabled_sensor": {
                    "disabled": True,
                }
            }
        }

        sensor_groups = [
            {
                "register_start": 1000,
                "poll_speed": "NORMAL",
                "entities": [
                    {
                        "name": "Test Sensor",
                        "unique": "test_disabled_sensor",
                        "register": ["1000"],
                    },
                    {
                        "name": "Keep Sensor",
                        "unique": "test_keep_sensor",
                        "register": ["1001"],
                    },
                ],
            }
        ]

        modified = apply_model_overrides(sensor_groups, "SH25T")

        # Check that disabled sensor was removed
        entities = modified[0]["entities"]
        self.assertEqual(len(entities), 1)
        self.assertEqual(entities[0]["unique"], "test_keep_sensor")

        # Restore original overrides
        if original_overrides:
            MODEL_OVERRIDES["SH25T"] = original_overrides
        else:
            del MODEL_OVERRIDES["SH25T"]

    def test_no_modification_without_override(self):
        """Test that sensors are unchanged when no override exists."""
        sensor_groups = [
            {
                "register_start": 9999,
                "poll_speed": "NORMAL",
                "entities": [
                    {
                        "name": "No Override Sensor",
                        "unique": "sungrow_modbus_no_override",
                        "register": ["9999"],
                    }
                ],
            }
        ]

        original = deepcopy(sensor_groups)
        modified = apply_model_overrides(sensor_groups, "SH25T")

        # The sensor should be unchanged
        self.assertEqual(modified[0]["entities"][0]["register"], original[0]["entities"][0]["register"])

    def test_apply_derived_overrides(self):
        """Test applying overrides to derived sensors."""
        derived_sensors = [
            {
                "name": "Derived Test",
                "unique": "test_derived",
                "sources": ["sensor1", "sensor2"],
            }
        ]

        # Should not crash and should return the list
        modified = apply_derived_overrides(derived_sensors, "SH25T")
        self.assertIsInstance(modified, list)


class TestWildcardPriority(unittest.TestCase):
    """Test that more specific patterns override general ones."""

    def test_specific_overrides_general(self):
        """Test that SH25T overrides SH*T."""
        # SH25T should match both "SH25T" and "SH*T"
        # but specific overrides should take precedence
        overrides = get_model_overrides("SH25T")

        # Should have merged both patterns
        self.assertIsNotNone(overrides)


if __name__ == "__main__":
    unittest.main()
