"""Tests for string inverter sensor definitions."""

import unittest
from custom_components.sungrow_modbus.sensor_data.string_sensors import string_sensors, string_sensors_derived
from custom_components.sungrow_modbus.data.enums import PollSpeed, InverterFeature, Category
from homeassistant.components.sensor.const import SensorDeviceClass


def find_entity_by_unique(unique_id):
    """Find an entity by its unique id in sensor groups."""
    for group in string_sensors:
        for entity in group.get("entities", []):
            if entity.get("unique") == unique_id:
                return group, entity
    return None, None


def find_group_by_register_start(register_start):
    """Find a sensor group by its starting register."""
    for group in string_sensors:
        if group.get("register_start") == register_start:
            return group
    return None


class TestStringSensorDefinitions(unittest.TestCase):
    """Test string sensor definitions are complete and correct."""

    def test_string_sensors_not_empty(self):
        """Test that string sensors list is not empty."""
        self.assertGreater(len(string_sensors), 0, "string_sensors should not be empty")

    def test_expected_sensors_exist(self):
        """Test that all expected sensors are defined."""
        expected_uniques = [
            # Device info
            "sungrow_modbus_inverter_serial",
            "sungrow_modbus_device_type_code",
            "sungrow_modbus_nominal_active_power",
            # PV generation
            "sungrow_modbus_daily_pv_generation",
            "sungrow_modbus_total_pv_generation",
            "sungrow_modbus_inverter_temperature",
            # MPPT sensors
            "sungrow_modbus_mppt1_voltage",
            "sungrow_modbus_mppt1_current",
            "sungrow_modbus_mppt2_voltage",
            "sungrow_modbus_mppt2_current",
            "sungrow_modbus_total_dc_power",
            # AC output
            "sungrow_modbus_phase_a_voltage",
            "sungrow_modbus_phase_a_current",
            "sungrow_modbus_total_active_power",
            # Grid
            "sungrow_modbus_grid_frequency",
            # Status
            "sungrow_modbus_work_state",
            "sungrow_modbus_fault_code",
        ]

        for unique in expected_uniques:
            group, entity = find_entity_by_unique(unique)
            self.assertIsNotNone(entity, f"Expected sensor '{unique}' not found")


class TestStringSensorRegisters(unittest.TestCase):
    """Test string sensor register definitions are correct."""

    def test_ac_current_registers(self):
        """Test AC current uses string-specific registers (5022-5024)."""
        # Phase A Current
        group, entity = find_entity_by_unique("sungrow_modbus_phase_a_current")
        self.assertIsNotNone(entity)
        self.assertEqual(entity["register"], ["5022"])

        # Phase B Current (three-phase only)
        group, entity = find_entity_by_unique("sungrow_modbus_phase_b_current")
        self.assertIsNotNone(entity)
        self.assertEqual(entity["register"], ["5023"])

        # Phase C Current (three-phase only)
        group, entity = find_entity_by_unique("sungrow_modbus_phase_c_current")
        self.assertIsNotNone(entity)
        self.assertEqual(entity["register"], ["5024"])

    def test_total_active_power_register(self):
        """Test total active power uses string-specific registers (5031-5032)."""
        group, entity = find_entity_by_unique("sungrow_modbus_total_active_power")
        self.assertIsNotNone(entity)
        self.assertEqual(entity["register"], ["5031", "5032"])

    def test_grid_frequency_register(self):
        """Test grid frequency uses string-specific register (5036)."""
        group, entity = find_entity_by_unique("sungrow_modbus_grid_frequency")
        self.assertIsNotNone(entity)
        self.assertEqual(entity["register"], ["5036"])

    def test_work_state_register(self):
        """Test work state uses string-specific register (5038)."""
        group, entity = find_entity_by_unique("sungrow_modbus_work_state")
        self.assertIsNotNone(entity)
        self.assertEqual(entity["register"], ["5038"])

    def test_mppt3_registers(self):
        """Test MPPT3 sensors exist with correct registers."""
        # MPPT3 Voltage
        group, entity = find_entity_by_unique("sungrow_modbus_mppt3_voltage")
        self.assertIsNotNone(entity)
        self.assertEqual(entity["register"], ["5015"])

        # MPPT3 Current
        group, entity = find_entity_by_unique("sungrow_modbus_mppt3_current")
        self.assertIsNotNone(entity)
        self.assertEqual(entity["register"], ["5016"])


class TestStringSensorFeatureRequirements(unittest.TestCase):
    """Test feature requirements are correctly set."""

    def test_pv_sensors_require_pv_feature(self):
        """Test that PV sensors have PV feature requirement."""
        pv_sensor_uniques = [
            "sungrow_modbus_daily_pv_generation",
            "sungrow_modbus_total_pv_generation",
            "sungrow_modbus_mppt1_voltage",
            "sungrow_modbus_mppt1_current",
            "sungrow_modbus_mppt2_voltage",
            "sungrow_modbus_mppt2_current",
            "sungrow_modbus_total_dc_power",
            "sungrow_modbus_array_insulation_resistance",
        ]

        for unique in pv_sensor_uniques:
            group, entity = find_entity_by_unique(unique)
            self.assertIsNotNone(group, f"Sensor '{unique}' not found")
            feature_req = group.get("feature_requirement", [])
            self.assertIn(
                InverterFeature.PV, feature_req,
                f"Sensor '{unique}' should require PV feature"
            )

    def test_three_phase_sensors_require_three_phase(self):
        """Test that three-phase sensors have THREE_PHASE feature requirement."""
        three_phase_uniques = [
            "sungrow_modbus_phase_b_voltage",
            "sungrow_modbus_phase_c_voltage",
            "sungrow_modbus_phase_b_current",
            "sungrow_modbus_phase_c_current",
        ]

        for unique in three_phase_uniques:
            group, entity = find_entity_by_unique(unique)
            self.assertIsNotNone(group, f"Sensor '{unique}' not found")
            feature_req = group.get("feature_requirement", [])
            self.assertIn(
                InverterFeature.THREE_PHASE, feature_req,
                f"Sensor '{unique}' should require THREE_PHASE feature"
            )

    def test_mppt3_sensors_require_mppt3_feature(self):
        """Test that MPPT3 sensors have MPPT3 feature requirement."""
        mppt3_uniques = [
            "sungrow_modbus_mppt3_voltage",
            "sungrow_modbus_mppt3_current",
        ]

        for unique in mppt3_uniques:
            group, entity = find_entity_by_unique(unique)
            self.assertIsNotNone(group, f"Sensor '{unique}' not found")
            feature_req = group.get("feature_requirement", [])
            self.assertIn(
                InverterFeature.MPPT3, feature_req,
                f"Sensor '{unique}' should require MPPT3 feature"
            )

    def test_phase_a_sensors_no_three_phase_requirement(self):
        """Test that Phase A sensors don't require THREE_PHASE (available on all)."""
        phase_a_uniques = [
            "sungrow_modbus_phase_a_voltage",
            "sungrow_modbus_phase_a_current",
        ]

        for unique in phase_a_uniques:
            group, entity = find_entity_by_unique(unique)
            self.assertIsNotNone(group, f"Sensor '{unique}' not found")
            feature_req = group.get("feature_requirement", [])
            self.assertNotIn(
                InverterFeature.THREE_PHASE, feature_req,
                f"Sensor '{unique}' should NOT require THREE_PHASE feature"
            )


class TestStringSensorValueMappings(unittest.TestCase):
    """Test value mappings are correctly referenced."""

    def test_work_state_uses_running_state_mapping(self):
        """Test work state uses running_state value mapping."""
        group, entity = find_entity_by_unique("sungrow_modbus_work_state")
        self.assertIsNotNone(entity)
        self.assertEqual(entity.get("value_mapping"), "running_state")

    def test_fault_code_uses_alarm_mapping(self):
        """Test fault code uses alarm value mapping."""
        group, entity = find_entity_by_unique("sungrow_modbus_fault_code")
        self.assertIsNotNone(entity)
        self.assertEqual(entity.get("value_mapping"), "alarm")


class TestStringSensorPollSpeeds(unittest.TestCase):
    """Test poll speeds are correctly set."""

    def test_device_info_poll_once(self):
        """Test device info sensors poll once."""
        once_register_starts = [4989, 4999, 5000, 5049]
        for reg_start in once_register_starts:
            group = find_group_by_register_start(reg_start)
            self.assertIsNotNone(group, f"Group starting at {reg_start} not found")
            self.assertEqual(
                group.get("poll_speed"), PollSpeed.ONCE,
                f"Group at {reg_start} should poll ONCE"
            )

    def test_mppt_sensors_poll_fast(self):
        """Test MPPT sensors poll fast."""
        mppt_register_starts = [5011, 5015, 5017]
        for reg_start in mppt_register_starts:
            group = find_group_by_register_start(reg_start)
            self.assertIsNotNone(group, f"Group starting at {reg_start} not found")
            self.assertEqual(
                group.get("poll_speed"), PollSpeed.FAST,
                f"Group at {reg_start} should poll FAST"
            )

    def test_ac_output_sensors_poll_fast(self):
        """Test AC output sensors poll fast."""
        ac_register_starts = [5018, 5019, 5022, 5023, 5031, 5033]
        for reg_start in ac_register_starts:
            group = find_group_by_register_start(reg_start)
            self.assertIsNotNone(group, f"Group starting at {reg_start} not found")
            self.assertEqual(
                group.get("poll_speed"), PollSpeed.FAST,
                f"Group at {reg_start} should poll FAST"
            )

    def test_status_sensors_poll_normal(self):
        """Test status sensors poll at normal speed."""
        status_register_starts = [5036, 5038, 5045]
        for reg_start in status_register_starts:
            group = find_group_by_register_start(reg_start)
            self.assertIsNotNone(group, f"Group starting at {reg_start} not found")
            self.assertEqual(
                group.get("poll_speed"), PollSpeed.NORMAL,
                f"Group at {reg_start} should poll NORMAL"
            )

    def test_generation_summary_polls_slow(self):
        """Test generation summary polls slowly."""
        group = find_group_by_register_start(5002)
        self.assertIsNotNone(group)
        self.assertEqual(group.get("poll_speed"), PollSpeed.SLOW)


class TestStringSensorCategories(unittest.TestCase):
    """Test sensor categories are correctly assigned."""

    def test_pv_sensors_have_pv_category(self):
        """Test PV sensors have PV_INFORMATION category."""
        pv_uniques = [
            "sungrow_modbus_daily_pv_generation",
            "sungrow_modbus_total_pv_generation",
            "sungrow_modbus_mppt1_voltage",
            "sungrow_modbus_mppt2_voltage",
            "sungrow_modbus_total_dc_power",
        ]

        for unique in pv_uniques:
            group, entity = find_entity_by_unique(unique)
            self.assertIsNotNone(entity, f"Sensor '{unique}' not found")
            self.assertEqual(
                entity.get("category"), Category.PV_INFORMATION,
                f"Sensor '{unique}' should have PV_INFORMATION category"
            )

    def test_ac_sensors_have_ac_category(self):
        """Test AC sensors have AC_INFORMATION category."""
        ac_uniques = [
            "sungrow_modbus_phase_a_voltage",
            "sungrow_modbus_phase_a_current",
            "sungrow_modbus_total_active_power",
            "sungrow_modbus_reactive_power",
            "sungrow_modbus_power_factor",
        ]

        for unique in ac_uniques:
            group, entity = find_entity_by_unique(unique)
            self.assertIsNotNone(entity, f"Sensor '{unique}' not found")
            self.assertEqual(
                entity.get("category"), Category.AC_INFORMATION,
                f"Sensor '{unique}' should have AC_INFORMATION category"
            )

    def test_status_sensors_have_status_category(self):
        """Test status sensors have STATUS_INFORMATION category."""
        status_uniques = [
            "sungrow_modbus_work_state",
            "sungrow_modbus_fault_code",
        ]

        for unique in status_uniques:
            group, entity = find_entity_by_unique(unique)
            self.assertIsNotNone(entity, f"Sensor '{unique}' not found")
            self.assertEqual(
                entity.get("category"), Category.STATUS_INFORMATION,
                f"Sensor '{unique}' should have STATUS_INFORMATION category"
            )


class TestStringSensorDeviceClasses(unittest.TestCase):
    """Test device classes are correctly assigned."""

    def test_voltage_sensors_have_voltage_class(self):
        """Test voltage sensors have VOLTAGE device class."""
        voltage_uniques = [
            "sungrow_modbus_mppt1_voltage",
            "sungrow_modbus_mppt2_voltage",
            "sungrow_modbus_phase_a_voltage",
        ]

        for unique in voltage_uniques:
            group, entity = find_entity_by_unique(unique)
            self.assertIsNotNone(entity, f"Sensor '{unique}' not found")
            self.assertEqual(
                entity.get("device_class"), SensorDeviceClass.VOLTAGE,
                f"Sensor '{unique}' should have VOLTAGE device class"
            )

    def test_current_sensors_have_current_class(self):
        """Test current sensors have CURRENT device class."""
        current_uniques = [
            "sungrow_modbus_mppt1_current",
            "sungrow_modbus_mppt2_current",
            "sungrow_modbus_phase_a_current",
        ]

        for unique in current_uniques:
            group, entity = find_entity_by_unique(unique)
            self.assertIsNotNone(entity, f"Sensor '{unique}' not found")
            self.assertEqual(
                entity.get("device_class"), SensorDeviceClass.CURRENT,
                f"Sensor '{unique}' should have CURRENT device class"
            )

    def test_power_sensors_have_power_class(self):
        """Test power sensors have POWER device class."""
        power_uniques = [
            "sungrow_modbus_total_dc_power",
            "sungrow_modbus_total_active_power",
            "sungrow_modbus_nominal_active_power",
        ]

        for unique in power_uniques:
            group, entity = find_entity_by_unique(unique)
            self.assertIsNotNone(entity, f"Sensor '{unique}' not found")
            self.assertEqual(
                entity.get("device_class"), SensorDeviceClass.POWER,
                f"Sensor '{unique}' should have POWER device class"
            )

    def test_energy_sensors_have_energy_class(self):
        """Test energy sensors have ENERGY device class."""
        energy_uniques = [
            "sungrow_modbus_daily_pv_generation",
            "sungrow_modbus_total_pv_generation",
        ]

        for unique in energy_uniques:
            group, entity = find_entity_by_unique(unique)
            self.assertIsNotNone(entity, f"Sensor '{unique}' not found")
            self.assertEqual(
                entity.get("device_class"), SensorDeviceClass.ENERGY,
                f"Sensor '{unique}' should have ENERGY device class"
            )


class TestStringSensorSignedValues(unittest.TestCase):
    """Test signed flag is correctly set where needed."""

    def test_temperature_is_signed(self):
        """Test inverter temperature is signed (can be negative)."""
        group, entity = find_entity_by_unique("sungrow_modbus_inverter_temperature")
        self.assertIsNotNone(entity)
        self.assertTrue(entity.get("signed", False), "Temperature should be signed")

    def test_current_sensors_are_signed(self):
        """Test AC current sensors are signed."""
        current_uniques = [
            "sungrow_modbus_phase_a_current",
            "sungrow_modbus_phase_b_current",
            "sungrow_modbus_phase_c_current",
        ]

        for unique in current_uniques:
            group, entity = find_entity_by_unique(unique)
            self.assertIsNotNone(entity, f"Sensor '{unique}' not found")
            self.assertTrue(
                entity.get("signed", False),
                f"Sensor '{unique}' should be signed"
            )

    def test_reactive_power_is_signed(self):
        """Test reactive power is signed."""
        group, entity = find_entity_by_unique("sungrow_modbus_reactive_power")
        self.assertIsNotNone(entity)
        self.assertTrue(entity.get("signed", False), "Reactive power should be signed")

    def test_power_factor_is_signed(self):
        """Test power factor is signed."""
        group, entity = find_entity_by_unique("sungrow_modbus_power_factor")
        self.assertIsNotNone(entity)
        self.assertTrue(entity.get("signed", False), "Power factor should be signed")


class TestStringSensorDerived(unittest.TestCase):
    """Test derived sensors list."""

    def test_derived_sensors_is_list(self):
        """Test derived sensors is a list."""
        self.assertIsInstance(string_sensors_derived, list)


if __name__ == "__main__":
    unittest.main()
