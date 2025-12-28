"""Tests for sensor platform setup and entity behavior."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.sungrow_modbus.const import (
    CONTROLLER,
    DOMAIN,
    REGISTER,
    SENSOR_DERIVED_ENTITIES,
    SENSOR_ENTITIES,
    SLAVE,
    VALUE,
    VALUES,
)
from custom_components.sungrow_modbus.data.enums import InverterType, PollSpeed
from custom_components.sungrow_modbus.sensor import async_setup_entry
from custom_components.sungrow_modbus.sensors.sungrow_base_sensor import SungrowBaseSensor
from custom_components.sungrow_modbus.sensors.sungrow_sensor import SungrowSensor


def create_mock_controller(host="10.0.0.1", port=502, slave=1, inverter_type=InverterType.HYBRID):
    """Create a mock controller with common defaults."""
    controller = MagicMock()
    controller.host = host
    controller.port = port
    controller.connection_id = f"{host}:{port}"
    controller.device_id = slave
    controller.slave = slave
    controller.connected.return_value = True
    controller.inverter_config = MagicMock()
    controller.inverter_config.type = inverter_type
    controller.model = "S6-EH3P10K"
    controller.device_identification = "XYZ123"
    controller.sw_version = "1.0.0"
    controller.poll_speed = {PollSpeed.FAST: 5, PollSpeed.NORMAL: 15, PollSpeed.SLOW: 30}
    controller.device_info = {
        "identifiers": {(DOMAIN, f"{host}:{502}_{slave}")},
        "manufacturer": "Sungrow",
        "name": "S6-EH3P10K",
    }
    controller.controller_key = f"{host}:502_{slave}"
    return controller


def create_mock_base_sensor(
    name="Test Sensor", registrars=None, multiplier=1, poll_speed=PollSpeed.NORMAL, controller=None
):
    """Create a mock base sensor."""
    if registrars is None:
        registrars = [33000]
    if controller is None:
        controller = create_mock_controller()

    sensor = MagicMock(spec=SungrowBaseSensor)
    sensor.name = name
    sensor.registrars = registrars
    sensor.multiplier = multiplier
    sensor.poll_speed = poll_speed
    sensor.controller = controller
    sensor.device_class = None
    sensor.state_class = None
    sensor.unit_of_measurement = None
    sensor.unique_id = f"sungrow_test_{registrars[0]}"
    sensor.hidden = False
    sensor.convert_value = MagicMock(side_effect=lambda vals: sum(vals) * multiplier)
    return sensor


class TestSensorPlatformSetup:
    """Test sensor platform async_setup_entry."""

    @pytest.mark.asyncio
    async def test_async_setup_entry_creates_sensor_entities(self):
        """Test that sensor entities are created from sensor groups."""
        controller = create_mock_controller()

        # Create mock sensor group with sensors
        mock_sensor1 = create_mock_base_sensor(name="Sensor 1", registrars=[33000], controller=controller)
        mock_sensor2 = create_mock_base_sensor(name="Sensor 2", registrars=[33001], controller=controller)
        mock_reserve = create_mock_base_sensor(name="reserve", registrars=[33002], controller=controller)

        mock_group = MagicMock()
        mock_group.sensors = [mock_sensor1, mock_sensor2, mock_reserve]

        controller.sensor_groups = [mock_group]
        controller.derived_sensors = []

        hass = MagicMock()
        hass.data = {DOMAIN: {CONTROLLER: {"10.0.0.1:502_1": controller}}}

        config_entry = MagicMock()
        config_entry.data = {"host": "10.0.0.1", "port": 502, "slave": 1}
        config_entry.options = {}

        captured_entities = []

        def capture_add_entities(entities, update_immediately):
            captured_entities.extend(entities)

        result = await async_setup_entry(hass, config_entry, capture_add_entities)

        assert result is True
        # Should have 2 sensors (reserve is filtered out)
        sensor_entities = [e for e in captured_entities if isinstance(e, SungrowSensor)]
        assert len(sensor_entities) == 2
        assert SENSOR_ENTITIES in hass.data[DOMAIN]
        assert VALUES in hass.data[DOMAIN]

    @pytest.mark.asyncio
    async def test_async_setup_entry_creates_derived_entities(self):
        """Test that derived sensor entities are created."""
        controller = create_mock_controller()
        controller.sensor_groups = []

        mock_derived = create_mock_base_sensor(name="Derived Sensor", registrars=[33100, 33101], controller=controller)
        controller.derived_sensors = [mock_derived]

        hass = MagicMock()
        hass.data = {DOMAIN: {CONTROLLER: {"10.0.0.1:502_1": controller}}}

        config_entry = MagicMock()
        config_entry.data = {"host": "10.0.0.1", "port": 502, "slave": 1}
        config_entry.options = {}

        captured_entities = []

        def capture_add_entities(entities, update_immediately):
            captured_entities.extend(entities)

        await async_setup_entry(hass, config_entry, capture_add_entities)

        assert SENSOR_DERIVED_ENTITIES in hass.data[DOMAIN]
        assert len(hass.data[DOMAIN][SENSOR_DERIVED_ENTITIES]) == 1


class TestSungrowSensor:
    """Test SungrowSensor entity behavior."""

    def test_sensor_initialization(self):
        """Test sensor is properly initialized."""
        hass = MagicMock()
        base_sensor = create_mock_base_sensor(name="Test Sensor", registrars=[33000], multiplier=0.1)

        sensor = SungrowSensor(hass, base_sensor)

        assert sensor._attr_name == "Test Sensor"
        assert sensor._register == [33000]
        assert sensor.is_added_to_hass is False

    def test_sensor_decimal_count(self):
        """Test decimal count calculation for different multipliers."""
        hass = MagicMock()
        base_sensor = create_mock_base_sensor(multiplier=0.1)
        base_sensor.device_class = "power"  # Need device_class for decimal_count
        sensor = SungrowSensor(hass, base_sensor)

        assert sensor.decimal_count(1) == 0
        assert sensor.decimal_count(0.1) == 1
        assert sensor.decimal_count(0.01) == 2
        assert sensor.decimal_count(0.001) == 3

    def test_sensor_decimal_count_no_device_class(self):
        """Test decimal count returns None when no device class."""
        hass = MagicMock()
        base_sensor = create_mock_base_sensor(multiplier=0.1)
        base_sensor.device_class = None
        sensor = SungrowSensor(hass, base_sensor)

        assert sensor.decimal_count(0.1) is None

    @pytest.mark.asyncio
    async def test_sensor_handle_modbus_update_single_register(self):
        """Test sensor updates correctly with single register."""
        hass = MagicMock()
        controller = create_mock_controller()
        base_sensor = create_mock_base_sensor(name="Power", registrars=[33000], multiplier=1, controller=controller)

        sensor = SungrowSensor(hass, base_sensor)
        sensor.is_added_to_hass = True
        sensor.schedule_update_ha_state = MagicMock()  # Mock this to avoid hass dependency

        # Create event with matching controller
        event = MagicMock()
        event.data = {REGISTER: 33000, VALUE: 1000, CONTROLLER: "10.0.0.1:502", SLAVE: 1}

        sensor.handle_modbus_update(event)

        assert sensor._attr_native_value == 1000
        assert sensor._attr_available is True

    @pytest.mark.asyncio
    async def test_sensor_handle_modbus_update_multi_register(self):
        """Test sensor waits for all registers before updating."""
        hass = MagicMock()
        controller = create_mock_controller()
        base_sensor = create_mock_base_sensor(
            name="Power", registrars=[33000, 33001], multiplier=1, controller=controller
        )

        sensor = SungrowSensor(hass, base_sensor)
        sensor.is_added_to_hass = True
        sensor.schedule_update_ha_state = MagicMock()

        # First register event - should wait
        event1 = MagicMock()
        event1.data = {REGISTER: 33000, VALUE: 100, CONTROLLER: "10.0.0.1:502", SLAVE: 1}

        sensor.handle_modbus_update(event1)
        assert sensor._attr_native_value is None  # Not yet updated

        # Second register event - should process both
        event2 = MagicMock()
        event2.data = {REGISTER: 33001, VALUE: 200, CONTROLLER: "10.0.0.1:502", SLAVE: 1}

        sensor.handle_modbus_update(event2)
        # convert_value was called with [100, 200], returns sum * multiplier = 300
        assert sensor._attr_native_value == 300

    @pytest.mark.asyncio
    async def test_sensor_handle_modbus_update_wrong_controller(self):
        """Test sensor ignores updates from different controller."""
        hass = MagicMock()
        controller = create_mock_controller(host="10.0.0.1", slave=1)
        base_sensor = create_mock_base_sensor(registrars=[33000], controller=controller)

        sensor = SungrowSensor(hass, base_sensor)
        sensor.is_added_to_hass = True
        sensor._attr_native_value = 500  # Existing value

        # Event from different controller
        event = MagicMock()
        event.data = {
            REGISTER: 33000,
            VALUE: 1000,
            CONTROLLER: "10.0.0.2:502",  # Different host
            SLAVE: 1,
        }

        sensor.handle_modbus_update(event)

        # Value should remain unchanged
        assert sensor._attr_native_value == 500

    @pytest.mark.asyncio
    async def test_sensor_handle_modbus_update_wrong_register(self):
        """Test sensor ignores updates for unrelated registers."""
        hass = MagicMock()
        controller = create_mock_controller()
        base_sensor = create_mock_base_sensor(registrars=[33000], controller=controller)

        sensor = SungrowSensor(hass, base_sensor)
        sensor.is_added_to_hass = True
        sensor._attr_native_value = 500

        event = MagicMock()
        event.data = {
            REGISTER: 33999,  # Different register
            VALUE: 1000,
            CONTROLLER: "10.0.0.1:502",
            SLAVE: 1,
        }

        sensor.handle_modbus_update(event)

        # Value should remain unchanged
        assert sensor._attr_native_value == 500

    @pytest.mark.asyncio
    async def test_sensor_watchdog_timeout(self):
        """Test sensor becomes unavailable after watchdog timeout."""
        hass = MagicMock()
        controller = create_mock_controller()
        base_sensor = create_mock_base_sensor(registrars=[33000], poll_speed=PollSpeed.NORMAL, controller=controller)

        sensor = SungrowSensor(hass, base_sensor)
        sensor.is_added_to_hass = True
        sensor._attr_available = True
        sensor.schedule_update_ha_state = MagicMock()

        # Set last update to 30 minutes ago (exceeds timeout of ~25 min for NORMAL)
        sensor._last_update = datetime.now(UTC).astimezone() - timedelta(minutes=30)

        await sensor.async_update()

        assert sensor._attr_available is False

    @pytest.mark.asyncio
    async def test_sensor_watchdog_no_timeout_once_poll(self):
        """Test ONCE poll speed sensors don't trigger watchdog."""
        hass = MagicMock()
        controller = create_mock_controller()
        base_sensor = create_mock_base_sensor(registrars=[33000], poll_speed=PollSpeed.ONCE, controller=controller)

        sensor = SungrowSensor(hass, base_sensor)
        sensor.is_added_to_hass = True
        sensor._attr_available = True

        # Set last update to very long ago
        sensor._last_update = datetime.now(UTC).astimezone() - timedelta(hours=24)

        await sensor.async_update()

        # ONCE poll speed should not trigger unavailable
        assert sensor._attr_available is True

    @pytest.mark.asyncio
    async def test_sensor_async_added_to_hass_registers_listener(self):
        """Test sensor registers event listener when added to hass."""
        hass = MagicMock()
        hass.bus.async_listen = MagicMock(return_value=MagicMock())
        controller = create_mock_controller()
        base_sensor = create_mock_base_sensor(controller=controller)

        sensor = SungrowSensor(hass, base_sensor)

        with patch.object(sensor, "async_get_last_sensor_data", new_callable=AsyncMock) as mock_restore:
            mock_restore.return_value = None
            await sensor.async_added_to_hass()

        assert sensor.is_added_to_hass is True
        hass.bus.async_listen.assert_called_once_with(DOMAIN, sensor.handle_modbus_update)
        assert sensor._unsub_listener is not None

    @pytest.mark.asyncio
    async def test_sensor_async_will_remove_from_hass_cleanup(self):
        """Test sensor cleans up listener when removed."""
        hass = MagicMock()
        unsub_mock = MagicMock()
        hass.bus.async_listen = MagicMock(return_value=unsub_mock)
        controller = create_mock_controller()
        base_sensor = create_mock_base_sensor(controller=controller)

        sensor = SungrowSensor(hass, base_sensor)

        with patch.object(sensor, "async_get_last_sensor_data", new_callable=AsyncMock) as mock_restore:
            mock_restore.return_value = None
            await sensor.async_added_to_hass()

        await sensor.async_will_remove_from_hass()

        unsub_mock.assert_called_once()
        assert sensor._unsub_listener is None

    @pytest.mark.asyncio
    async def test_sensor_restores_state(self):
        """Test sensor restores previous state on startup."""
        hass = MagicMock()
        controller = create_mock_controller()
        base_sensor = create_mock_base_sensor(controller=controller)

        sensor = SungrowSensor(hass, base_sensor)

        mock_state = MagicMock()
        mock_state.native_value = 42.5

        with patch.object(sensor, "async_get_last_sensor_data", new_callable=AsyncMock) as mock_restore:
            mock_restore.return_value = mock_state
            hass.bus.async_listen = MagicMock(return_value=MagicMock())
            await sensor.async_added_to_hass()

        assert sensor._attr_native_value == 42.5


class TestSensorMultiplier:
    """Test sensor value conversion with different multipliers."""

    def test_multiplier_whole_number(self):
        """Test multiplier of 1 (no conversion)."""
        hass = MagicMock()
        controller = create_mock_controller()
        base_sensor = create_mock_base_sensor(registrars=[33000], multiplier=1, controller=controller)
        base_sensor.convert_value = lambda vals: vals[0] * 1

        sensor = SungrowSensor(hass, base_sensor)
        sensor.is_added_to_hass = True
        sensor.schedule_update_ha_state = MagicMock()

        event = MagicMock()
        event.data = {REGISTER: 33000, VALUE: 123, CONTROLLER: "10.0.0.1:502", SLAVE: 1}

        sensor.handle_modbus_update(event)
        assert sensor._attr_native_value == 123

    def test_multiplier_decimal(self):
        """Test multiplier of 0.1."""
        hass = MagicMock()
        controller = create_mock_controller()
        base_sensor = create_mock_base_sensor(registrars=[33000], multiplier=0.1, controller=controller)
        base_sensor.convert_value = lambda vals: vals[0] * 0.1

        sensor = SungrowSensor(hass, base_sensor)
        sensor.is_added_to_hass = True
        sensor.schedule_update_ha_state = MagicMock()

        event = MagicMock()
        event.data = {REGISTER: 33000, VALUE: 123, CONTROLLER: "10.0.0.1:502", SLAVE: 1}

        sensor.handle_modbus_update(event)
        assert sensor._attr_native_value == 12.3

    def test_multiplier_large(self):
        """Test multiplier of 1000."""
        hass = MagicMock()
        controller = create_mock_controller()
        base_sensor = create_mock_base_sensor(registrars=[33000], multiplier=1000, controller=controller)
        base_sensor.convert_value = lambda vals: vals[0] * 1000

        sensor = SungrowSensor(hass, base_sensor)
        sensor.is_added_to_hass = True
        sensor.schedule_update_ha_state = MagicMock()

        event = MagicMock()
        event.data = {REGISTER: 33000, VALUE: 5, CONTROLLER: "10.0.0.1:502", SLAVE: 1}

        sensor.handle_modbus_update(event)
        assert sensor._attr_native_value == 5000
