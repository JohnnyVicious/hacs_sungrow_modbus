"""Tests for alarm code mapping functionality."""
import pytest

from custom_components.sungrow_modbus.data.alarm_codes import (
    ALARM_CODES,
    RUNNING_STATE_CODES,
    SYSTEM_STATE_CODES,
    PID_STATE_CODES,
    get_alarm_description,
    get_running_state,
    get_system_state,
    get_pid_state,
    is_fault_code,
)


class TestAlarmCodes:
    """Test alarm code lookups."""

    def test_get_alarm_description_known_code(self):
        """Test lookup of known alarm code."""
        assert get_alarm_description(2) == "Grid over-voltage"
        assert get_alarm_description(401) == "Grid frequency too high"
        assert get_alarm_description(4157) == "Bypass overload fault"

    def test_get_alarm_description_no_alarm(self):
        """Test that code 0 returns No alarm."""
        assert get_alarm_description(0) == "No alarm"

    def test_get_alarm_description_unknown_code(self):
        """Test that unknown codes return appropriate message."""
        result = get_alarm_description(9999)
        assert "Unknown alarm" in result
        assert "9999" in result

    def test_alarm_codes_completeness(self):
        """Verify alarm codes dictionary has entries."""
        assert len(ALARM_CODES) > 100  # Should have 150+ codes


class TestRunningStateCodes:
    """Test running state code lookups."""

    def test_get_running_state_known_code(self):
        """Test lookup of known running state."""
        assert get_running_state(0) == "Run"
        assert get_running_state(0x8000) == "Stop"
        assert get_running_state(0x5500) == "Fault"

    def test_get_running_state_numeric_work_state(self):
        """Test numeric work_state_2 values."""
        assert get_running_state(1) == "Stop"
        assert get_running_state(9) == "Fault"
        assert get_running_state(10) == "Alarm Run"

    def test_get_running_state_unknown(self):
        """Test unknown running state."""
        result = get_running_state(0xFFFF)
        assert "Unknown state" in result


class TestSystemStateCodes:
    """Test system state code lookups."""

    def test_get_system_state_known_code(self):
        """Test lookup of known system state."""
        assert get_system_state(0x0040) == "Running"
        assert get_system_state(0x0002) == "Stop"
        assert get_system_state(0x1000) == "Off-grid Run"

    def test_get_system_state_unknown(self):
        """Test unknown system state returns hex format."""
        result = get_system_state(0x9999)
        assert "Unknown state" in result
        assert "0x9999" in result.lower()


class TestPidStateCodes:
    """Test PID state code lookups."""

    def test_get_pid_state_normal(self):
        """Test that 0 returns Normal."""
        assert get_pid_state(0) == "Normal"

    def test_get_pid_state_known(self):
        """Test known PID states."""
        assert get_pid_state(2) == "PID Recover Operation"
        assert get_pid_state(4) == "Anti-PID Operation"
        assert get_pid_state(8) == "PID Abnormity"

    def test_get_pid_state_unknown(self):
        """Test unknown PID state."""
        result = get_pid_state(99)
        assert "Unknown PID state" in result


class TestIsFaultCode:
    """Test fault code detection."""

    def test_zero_is_not_fault(self):
        """Test that code 0 is not a fault."""
        assert is_fault_code(0) is False

    def test_fault_series_codes(self):
        """Test codes in fault series (2xx, 3xx, 6xx, 8xx)."""
        assert is_fault_code(200) is True  # Bus hardware over-voltage
        assert is_fault_code(300) is True  # INV over-temperature
        assert is_fault_code(600) is True  # BDC charging over-current
        assert is_fault_code(800) is True  # BDC permanent fault

    def test_codes_with_fault_in_description(self):
        """Test codes that have 'fault' in description."""
        assert is_fault_code(38) is True  # Relay fault (grid side)
        assert is_fault_code(44) is True  # Inverter self-test fault

    def test_warning_codes(self):
        """Test warning series codes (9xx) are not faults."""
        assert is_fault_code(900) is False  # BDC temperature sensor warning
        assert is_fault_code(932) is False  # Battery over-voltage warning


class TestValueMappingIntegration:
    """Test value mapping in sensor base class."""

    @pytest.fixture
    def mock_hass(self, hass):
        """Return mock hass instance."""
        return hass

    @pytest.fixture
    def mock_controller(self, mock_hass):
        """Create a mock controller for testing."""
        from unittest.mock import MagicMock

        controller = MagicMock()
        controller.inverter_config = MagicMock()
        controller.inverter_config.model = "SH10RT"
        controller.inverter_config.features = set()
        controller.inverter_config.wattage_chosen = 10000
        controller.controller_key = "test_192.168.1.100_502_1"
        controller.device_serial_number = "TEST123"
        return controller

    def test_sensor_with_alarm_mapping(self, mock_hass, mock_controller):
        """Test sensor converts alarm code to description."""
        from custom_components.sungrow_modbus.sensors.sungrow_base_sensor import SungrowBaseSensor

        sensor = SungrowBaseSensor(
            hass=mock_hass,
            controller=mock_controller,
            unique_id="test_alarm",
            name="Test Alarm",
            registrars=[5045],
            write_register=None,
            multiplier=1,
            value_mapping="alarm"
        )

        # Test conversion
        result = sensor.convert_value([401])
        assert result == "Grid frequency too high"
        assert sensor.raw_value == 401

    def test_sensor_with_system_state_mapping(self, mock_hass, mock_controller):
        """Test sensor converts system state code to description."""
        from custom_components.sungrow_modbus.sensors.sungrow_base_sensor import SungrowBaseSensor

        sensor = SungrowBaseSensor(
            hass=mock_hass,
            controller=mock_controller,
            unique_id="test_system_state",
            name="System State",
            registrars=[12999],
            write_register=None,
            multiplier=1,
            value_mapping="system_state"
        )

        result = sensor.convert_value([0x0040])
        assert result == "Running"
        assert sensor.raw_value == 0x0040

    def test_sensor_with_running_state_mapping(self, mock_hass, mock_controller):
        """Test sensor converts running state code to description."""
        from custom_components.sungrow_modbus.sensors.sungrow_base_sensor import SungrowBaseSensor

        sensor = SungrowBaseSensor(
            hass=mock_hass,
            controller=mock_controller,
            unique_id="test_running_state",
            name="Running State",
            registrars=[13000],
            write_register=None,
            multiplier=1,
            value_mapping="running_state"
        )

        result = sensor.convert_value([0x8000])
        assert result == "Stop"
        assert sensor.raw_value == 0x8000

    def test_sensor_with_custom_dict_mapping(self, mock_hass, mock_controller):
        """Test sensor with custom dictionary mapping."""
        from custom_components.sungrow_modbus.sensors.sungrow_base_sensor import SungrowBaseSensor

        custom_mapping = {
            0: "Off",
            1: "On",
            2: "Standby"
        }

        sensor = SungrowBaseSensor(
            hass=mock_hass,
            controller=mock_controller,
            unique_id="test_custom",
            name="Custom Sensor",
            registrars=[10000],
            write_register=None,
            multiplier=1,
            value_mapping=custom_mapping
        )

        assert sensor.convert_value([0]) == "Off"
        assert sensor.convert_value([1]) == "On"
        assert sensor.convert_value([2]) == "Standby"
        # Unknown value
        result = sensor.convert_value([99])
        assert "Unknown" in result

    def test_sensor_without_mapping(self, mock_hass, mock_controller):
        """Test sensor without value mapping returns numeric value."""
        from custom_components.sungrow_modbus.sensors.sungrow_base_sensor import SungrowBaseSensor

        sensor = SungrowBaseSensor(
            hass=mock_hass,
            controller=mock_controller,
            unique_id="test_no_mapping",
            name="No Mapping",
            registrars=[5000],
            write_register=None,
            multiplier=1,
            value_mapping=None
        )

        result = sensor.convert_value([1234])
        assert result == 1234
        assert sensor.has_value_mapping is False

    def test_sensor_has_value_mapping_property(self, mock_hass, mock_controller):
        """Test has_value_mapping property."""
        from custom_components.sungrow_modbus.sensors.sungrow_base_sensor import SungrowBaseSensor

        sensor_with = SungrowBaseSensor(
            hass=mock_hass,
            controller=mock_controller,
            unique_id="test_with",
            name="With Mapping",
            registrars=[5045],
            write_register=None,
            multiplier=1,
            value_mapping="alarm"
        )

        sensor_without = SungrowBaseSensor(
            hass=mock_hass,
            controller=mock_controller,
            unique_id="test_without",
            name="Without Mapping",
            registrars=[5000],
            write_register=None,
            multiplier=1,
            value_mapping=None
        )

        assert sensor_with.has_value_mapping is True
        assert sensor_without.has_value_mapping is False


class TestSensorDefinitionsWithMapping:
    """Test that sensor definitions include value_mapping correctly."""

    def test_hybrid_sensors_have_value_mapping(self):
        """Test that state sensors in hybrid_sensors have value_mapping."""
        from custom_components.sungrow_modbus.sensor_data.hybrid_sensors import hybrid_sensors

        # Find System State sensor
        system_state_found = False
        running_state_found = False
        fault_code_found = False

        for group in hybrid_sensors:
            for entity in group.get("entities", []):
                if entity.get("unique") == "sungrow_modbus_system_state":
                    assert entity.get("value_mapping") == "system_state"
                    system_state_found = True
                elif entity.get("unique") == "sungrow_modbus_running_state":
                    assert entity.get("value_mapping") == "running_state"
                    running_state_found = True
                elif entity.get("unique") == "sungrow_modbus_fault_code_1":
                    assert entity.get("value_mapping") == "alarm"
                    fault_code_found = True

        assert system_state_found, "System State sensor not found"
        assert running_state_found, "Running State sensor not found"
        assert fault_code_found, "Fault Code sensor not found"
