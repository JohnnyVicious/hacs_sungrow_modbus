"""Tests for battery sensor entities."""

import pytest
from unittest.mock import MagicMock, AsyncMock

from homeassistant.const import EntityCategory

from custom_components.sungrow_modbus.sensors.sungrow_battery_sensor import (
    SungrowBatterySensor,
    SungrowBatteryDiagnosticSensor,
    create_battery_sensors,
)
from custom_components.sungrow_modbus.battery_controller import (
    BatteryController,
    BatteryStack,
)
from custom_components.sungrow_modbus.sensor_data.battery_sensors import (
    battery_stack_sensors,
    battery_stack_diagnostic_sensors,
    get_battery_sensor_unique_id,
    get_battery_sensor_name,
)
from custom_components.sungrow_modbus.const import DOMAIN, MANUFACTURER


class TestBatterySensorHelpers:
    """Test helper functions for battery sensors."""

    def test_get_battery_sensor_unique_id(self):
        """Test unique ID generation."""
        sensor_def = {"unique": "battery_stack_voltage", "name": "Battery Stack Voltage"}
        result = get_battery_sensor_unique_id(sensor_def, 0, "INV123456")
        assert result == "sungrow_modbus_INV123456_battery_0_battery_stack_voltage"

    def test_get_battery_sensor_unique_id_stack_1(self):
        """Test unique ID generation for stack 1."""
        sensor_def = {"unique": "battery_stack_soc", "name": "Battery Stack SOC"}
        result = get_battery_sensor_unique_id(sensor_def, 1, "INV789")
        assert result == "sungrow_modbus_INV789_battery_1_battery_stack_soc"

    def test_get_battery_sensor_name(self):
        """Test sensor name generation."""
        sensor_def = {"name": "Battery Stack Voltage"}
        result = get_battery_sensor_name(sensor_def, 0)
        assert result == "Battery Stack 1 Voltage"

    def test_get_battery_sensor_name_stack_2(self):
        """Test sensor name generation for stack 2."""
        sensor_def = {"name": "Battery Stack SOC"}
        result = get_battery_sensor_name(sensor_def, 1)
        assert result == "Battery Stack 2 SOC"


class TestSungrowBatterySensor:
    """Test SungrowBatterySensor entity."""

    @pytest.fixture
    def mock_hass(self, hass):
        """Return mock hass instance."""
        return hass

    @pytest.fixture
    def mock_battery_controller(self):
        """Create a mock battery controller."""
        controller = MagicMock(spec=BatteryController)
        controller.stack_index = 0
        controller.slave_id = 200
        controller.inverter = MagicMock()
        controller.inverter.serial_number = "INV123456"
        controller.battery = BatteryStack(stack_index=0, slave_id=200)
        controller.battery.available = True
        controller.battery.serial_number = "BAT001"
        controller.battery.firmware_version = "1.0.0"
        controller.device_info = {
            "identifiers": {(DOMAIN, "INV123456_battery_0")},
            "name": "Sungrow Battery Stack 1",
            "manufacturer": MANUFACTURER,
            "model": "SBR Battery",
        }
        return controller

    def test_sensor_init(self, mock_hass, mock_battery_controller):
        """Test sensor initialization."""
        sensor_def = {
            "name": "Battery Stack Voltage",
            "unique": "battery_stack_voltage",
            "register": 10740,
            "multiplier": 0.1,
        }
        sensor = SungrowBatterySensor(mock_hass, mock_battery_controller, sensor_def)

        assert sensor._attr_name == "Battery Stack 1 Voltage"
        assert "battery_0_battery_stack_voltage" in sensor._attr_unique_id
        assert sensor._register == 10740
        assert sensor._multiplier == 0.1
        assert sensor._attr_available is True

    def test_sensor_device_info(self, mock_hass, mock_battery_controller):
        """Test sensor returns correct device info."""
        sensor_def = {"name": "Battery Stack SOC", "unique": "battery_stack_soc"}
        sensor = SungrowBatterySensor(mock_hass, mock_battery_controller, sensor_def)

        info = sensor.device_info
        assert (DOMAIN, "INV123456_battery_0") in info["identifiers"]

    def test_update_from_battery_data_voltage(self, mock_hass, mock_battery_controller):
        """Test updating sensor from battery data - voltage."""
        sensor_def = {"name": "Battery Stack Voltage", "unique": "battery_stack_voltage"}
        sensor = SungrowBatterySensor(mock_hass, mock_battery_controller, sensor_def)

        data = {"voltage": 51.2, "current": -5.0, "soc": 85.5}
        sensor.update_from_battery_data(data)

        assert sensor._attr_native_value == 51.2

    def test_update_from_battery_data_soc(self, mock_hass, mock_battery_controller):
        """Test updating sensor from battery data - SOC."""
        sensor_def = {"name": "Battery Stack SOC", "unique": "battery_stack_soc"}
        sensor = SungrowBatterySensor(mock_hass, mock_battery_controller, sensor_def)

        data = {"voltage": 51.2, "current": -5.0, "soc": 85.5}
        sensor.update_from_battery_data(data)

        assert sensor._attr_native_value == 85.5

    def test_update_from_battery_data_current(self, mock_hass, mock_battery_controller):
        """Test updating sensor from battery data - current."""
        sensor_def = {"name": "Battery Stack Current", "unique": "battery_stack_current"}
        sensor = SungrowBatterySensor(mock_hass, mock_battery_controller, sensor_def)

        data = {"voltage": 51.2, "current": -5.0, "soc": 85.5}
        sensor.update_from_battery_data(data)

        assert sensor._attr_native_value == -5.0

    def test_update_from_empty_data(self, mock_hass, mock_battery_controller):
        """Test updating sensor with empty data does nothing."""
        sensor_def = {"name": "Battery Stack Voltage", "unique": "battery_stack_voltage"}
        sensor = SungrowBatterySensor(mock_hass, mock_battery_controller, sensor_def)
        sensor._attr_native_value = 50.0

        sensor.update_from_battery_data({})

        assert sensor._attr_native_value == 50.0  # Unchanged


class TestSungrowBatteryDiagnosticSensor:
    """Test SungrowBatteryDiagnosticSensor entity."""

    @pytest.fixture
    def mock_hass(self, hass):
        """Return mock hass instance."""
        return hass

    @pytest.fixture
    def mock_battery_controller(self):
        """Create a mock battery controller."""
        controller = MagicMock(spec=BatteryController)
        controller.stack_index = 0
        controller.slave_id = 200
        controller.inverter = MagicMock()
        controller.inverter.serial_number = "INV123456"
        controller.battery = BatteryStack(stack_index=0, slave_id=200)
        controller.battery.available = True
        controller.battery.serial_number = "BAT001"
        controller.battery.firmware_version = "1.0.0"
        controller.device_info = {
            "identifiers": {(DOMAIN, "INV123456_battery_0")},
            "name": "Sungrow Battery Stack 1",
        }
        return controller

    def test_diagnostic_sensor_serial(self, mock_hass, mock_battery_controller):
        """Test diagnostic sensor for serial number."""
        sensor_def = {"name": "Battery Stack Serial Number", "unique": "battery_stack_serial"}
        sensor = SungrowBatteryDiagnosticSensor(mock_hass, mock_battery_controller, sensor_def)

        assert sensor._attr_native_value == "BAT001"
        assert sensor._attr_entity_category == EntityCategory.DIAGNOSTIC

    def test_diagnostic_sensor_firmware(self, mock_hass, mock_battery_controller):
        """Test diagnostic sensor for firmware."""
        sensor_def = {"name": "Battery Stack Firmware", "unique": "battery_stack_firmware"}
        sensor = SungrowBatteryDiagnosticSensor(mock_hass, mock_battery_controller, sensor_def)

        assert sensor._attr_native_value == "1.0.0"


class TestCreateBatterySensors:
    """Test create_battery_sensors function."""

    @pytest.fixture
    def mock_hass(self, hass):
        """Return mock hass instance."""
        return hass

    def test_create_sensors_single_battery(self, mock_hass):
        """Test creating sensors for a single battery stack."""
        controller = MagicMock(spec=BatteryController)
        controller.stack_index = 0
        controller.slave_id = 200
        controller.inverter = MagicMock()
        controller.inverter.serial_number = "INV123456"
        controller.battery = BatteryStack(stack_index=0, slave_id=200)
        controller.battery.available = True
        controller.battery.serial_number = "BAT001"
        controller.battery.firmware_version = "1.0.0"
        controller.device_info = {"identifiers": {(DOMAIN, "INV123456_battery_0")}}

        status_sensors, diagnostic_sensors = create_battery_sensors(mock_hass, [controller])

        # Should have sensors for all battery_stack_sensors definitions
        assert len(status_sensors) == len(battery_stack_sensors)
        # Should have sensors for all diagnostic sensor definitions
        assert len(diagnostic_sensors) == len(battery_stack_diagnostic_sensors)

    def test_create_sensors_two_batteries(self, mock_hass):
        """Test creating sensors for two battery stacks."""
        controllers = []
        for i in range(2):
            controller = MagicMock(spec=BatteryController)
            controller.stack_index = i
            controller.slave_id = 200 + i
            controller.inverter = MagicMock()
            controller.inverter.serial_number = "INV123456"
            controller.battery = BatteryStack(stack_index=i, slave_id=200 + i)
            controller.battery.available = True
            controller.battery.serial_number = f"BAT00{i+1}"
            controller.battery.firmware_version = "1.0.0"
            controller.device_info = {"identifiers": {(DOMAIN, f"INV123456_battery_{i}")}}
            controllers.append(controller)

        status_sensors, diagnostic_sensors = create_battery_sensors(mock_hass, controllers)

        # Should have double the sensors (one set per battery)
        assert len(status_sensors) == len(battery_stack_sensors) * 2
        assert len(diagnostic_sensors) == len(battery_stack_diagnostic_sensors) * 2

    def test_create_sensors_empty_list(self, mock_hass):
        """Test creating sensors with no battery controllers."""
        status_sensors, diagnostic_sensors = create_battery_sensors(mock_hass, [])

        assert len(status_sensors) == 0
        assert len(diagnostic_sensors) == 0


class TestBatterySensorDefinitions:
    """Test battery sensor definitions are complete."""

    def test_all_status_sensors_have_required_fields(self):
        """Test all status sensors have required fields."""
        for sensor in battery_stack_sensors:
            assert "name" in sensor, f"Sensor missing name: {sensor}"
            assert "unique" in sensor, f"Sensor missing unique: {sensor}"
            assert "register" in sensor, f"Sensor missing register: {sensor}"

    def test_all_diagnostic_sensors_have_required_fields(self):
        """Test all diagnostic sensors have required fields."""
        for sensor in battery_stack_diagnostic_sensors:
            assert "name" in sensor, f"Sensor missing name: {sensor}"
            assert "unique" in sensor, f"Sensor missing unique: {sensor}"
            assert "register" in sensor, f"Sensor missing register: {sensor}"

    def test_expected_status_sensors_exist(self):
        """Test expected status sensors are defined."""
        unique_ids = [s.get("unique") for s in battery_stack_sensors]

        assert "battery_stack_voltage" in unique_ids
        assert "battery_stack_current" in unique_ids
        assert "battery_stack_temperature" in unique_ids
        assert "battery_stack_soc" in unique_ids
        assert "battery_stack_soh" in unique_ids
        assert "battery_stack_total_charge" in unique_ids
        assert "battery_stack_total_discharge" in unique_ids
        assert "battery_stack_max_cell_voltage" in unique_ids
        assert "battery_stack_min_cell_voltage" in unique_ids

    def test_expected_diagnostic_sensors_exist(self):
        """Test expected diagnostic sensors are defined."""
        unique_ids = [s.get("unique") for s in battery_stack_diagnostic_sensors]

        assert "battery_stack_serial" in unique_ids
        assert "battery_stack_firmware" in unique_ids
