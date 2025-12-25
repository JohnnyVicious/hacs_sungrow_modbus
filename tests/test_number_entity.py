"""Tests for number entity platform."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from custom_components.sungrow_modbus.const import (
    DOMAIN, CONTROLLER, VALUES, REGISTER, VALUE, SLAVE
)
from custom_components.sungrow_modbus.data.enums import InverterType, PollSpeed
from custom_components.sungrow_modbus.number import async_setup_entry
from custom_components.sungrow_modbus.sensors.sungrow_number_sensor import SungrowNumberEntity


def create_mock_controller(host="10.0.0.1", slave=1, inverter_type=InverterType.HYBRID):
    """Create a mock controller."""
    controller = MagicMock()
    controller.host = host
    controller.device_id = slave
    controller.slave = slave
    controller.connected.return_value = True
    controller.inverter_config = MagicMock()
    controller.inverter_config.type = inverter_type
    controller.model = "SH10RT"
    controller.device_serial_number = "SN123456"
    controller.device_info = {
        "identifiers": {(DOMAIN, f"{host}:502_{slave}")},
        "manufacturer": "Sungrow",
        "name": "SH10RT",
    }
    controller.poll_speed = {PollSpeed.FAST: 5, PollSpeed.NORMAL: 15, PollSpeed.SLOW: 30}
    controller.async_write_holding_register = AsyncMock()
    controller.sensor_groups = []
    return controller


def create_mock_base_sensor(
    name="Test Number",
    registers=None,
    write_register=None,
    min_value=0,
    max_value=100,
    step=1,
    multiplier=1,
    default=50,
    unit="W",
    editable=True,
    hidden=False,
    enabled=True,
    controller=None
):
    """Create a mock base sensor."""
    if registers is None:
        registers = [33000]
    if controller is None:
        controller = create_mock_controller()

    sensor = MagicMock()
    sensor.name = name
    sensor.registrars = registers
    sensor.write_register = write_register
    sensor.min_value = min_value
    sensor.max_value = max_value
    sensor.step = step
    sensor.multiplier = multiplier
    sensor.default = default
    sensor.unit_of_measurement = unit
    sensor.device_class = "power"
    sensor.state_class = "measurement"
    sensor.editable = editable
    sensor.hidden = hidden
    sensor.enabled = enabled
    sensor.controller = controller
    sensor.unique_id = f"{DOMAIN}_SN123456_{registers[0]}_number"
    sensor.convert_value = MagicMock(side_effect=lambda vals: vals[0] * multiplier)
    return sensor


class TestNumberPlatformSetup:
    """Test number platform async_setup_entry."""

    @pytest.mark.asyncio
    async def test_creates_number_entities_for_editable_sensors(self):
        """Test number platform creates entities for editable sensors."""
        controller = create_mock_controller()

        # Add mock sensor groups with editable sensors
        sensor1 = create_mock_base_sensor(name="Power Limit", registers=[33001], editable=True, controller=controller)
        sensor2 = create_mock_base_sensor(name="Voltage", registers=[33002], editable=False, controller=controller)
        sensor3 = create_mock_base_sensor(name="reserve", registers=[33003], editable=True, controller=controller)

        sensor_group = MagicMock()
        sensor_group.sensors = [sensor1, sensor2, sensor3]
        controller.sensor_groups = [sensor_group]

        hass = MagicMock()
        hass.data = {
            DOMAIN: {
                CONTROLLER: {
                    "10.0.0.1:502_1": controller
                }
            }
        }

        config_entry = MagicMock()
        config_entry.data = {"host": "10.0.0.1", "port": 502, "slave": 1}
        config_entry.options = {}

        captured_entities = []

        def capture_add_devices(entities, update_immediately):
            captured_entities.extend(entities)

        await async_setup_entry(hass, config_entry, capture_add_devices)

        # Should only create entity for Power Limit (editable, not reserve)
        assert len(captured_entities) == 1
        assert captured_entities[0]._attr_name == "Power Limit"

    @pytest.mark.asyncio
    async def test_skips_non_editable_sensors(self):
        """Test number platform skips non-editable sensors."""
        controller = create_mock_controller()

        sensor = create_mock_base_sensor(name="Read Only", editable=False, controller=controller)

        sensor_group = MagicMock()
        sensor_group.sensors = [sensor]
        controller.sensor_groups = [sensor_group]

        hass = MagicMock()
        hass.data = {
            DOMAIN: {
                CONTROLLER: {
                    "10.0.0.1:502_1": controller
                }
            }
        }

        config_entry = MagicMock()
        config_entry.data = {"host": "10.0.0.1", "port": 502, "slave": 1}
        config_entry.options = {}

        captured_entities = []

        def capture_add_devices(entities, update_immediately):
            captured_entities.extend(entities)

        await async_setup_entry(hass, config_entry, capture_add_devices)

        assert len(captured_entities) == 0

    @pytest.mark.asyncio
    async def test_skips_reserve_sensors(self):
        """Test number platform skips sensors named 'reserve'."""
        controller = create_mock_controller()

        sensor = create_mock_base_sensor(name="reserve", editable=True, controller=controller)

        sensor_group = MagicMock()
        sensor_group.sensors = [sensor]
        controller.sensor_groups = [sensor_group]

        hass = MagicMock()
        hass.data = {
            DOMAIN: {
                CONTROLLER: {
                    "10.0.0.1:502_1": controller
                }
            }
        }

        config_entry = MagicMock()
        config_entry.data = {"host": "10.0.0.1", "port": 502, "slave": 1}
        config_entry.options = {}

        captured_entities = []

        def capture_add_devices(entities, update_immediately):
            captured_entities.extend(entities)

        await async_setup_entry(hass, config_entry, capture_add_devices)

        assert len(captured_entities) == 0


class TestSungrowNumberEntity:
    """Test SungrowNumberEntity behavior."""

    def test_entity_initialization(self):
        """Test number entity is properly initialized."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {}}}
        base_sensor = create_mock_base_sensor(
            name="Power Limit",
            registers=[33000],
            min_value=0,
            max_value=10000,
            step=100,
            default=5000,
            unit="W"
        )

        entity = SungrowNumberEntity(hass, base_sensor)

        assert entity._attr_name == "Power Limit"
        assert entity._attr_native_min_value == 0
        assert entity._attr_native_max_value == 10000
        assert entity._attr_native_step == 100
        assert entity._attr_native_value == 5000
        assert entity._attr_native_unit_of_measurement == "W"

    def test_entity_uses_write_register_when_specified(self):
        """Test entity uses write_register if different from read register."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {}}}
        base_sensor = create_mock_base_sensor(
            registers=[33000],
            write_register=43000  # Different write register
        )

        entity = SungrowNumberEntity(hass, base_sensor)

        assert entity._write_register == 43000

    def test_entity_uses_first_register_as_write_when_single(self):
        """Test entity uses first register for write when only one register."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {}}}
        base_sensor = create_mock_base_sensor(
            registers=[33000],
            write_register=None
        )

        entity = SungrowNumberEntity(hass, base_sensor)

        assert entity._write_register == 33000

    def test_set_native_value_writes_to_register(self):
        """Test set_native_value writes correct value to Modbus register."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {}}}
        hass.create_task = MagicMock()
        controller = create_mock_controller()
        base_sensor = create_mock_base_sensor(
            registers=[33000],
            multiplier=1,
            controller=controller
        )

        entity = SungrowNumberEntity(hass, base_sensor)
        entity.schedule_update_ha_state = MagicMock()
        entity._attr_native_value = 50

        entity.set_native_value(100)

        hass.create_task.assert_called_once()
        assert entity._attr_native_value == 100

    def test_set_native_value_applies_multiplier(self):
        """Test set_native_value divides by multiplier before writing."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {}}}
        hass.create_task = MagicMock()
        controller = create_mock_controller()
        base_sensor = create_mock_base_sensor(
            registers=[33000],
            multiplier=0.1,  # Values displayed as 10x register value
            controller=controller
        )

        entity = SungrowNumberEntity(hass, base_sensor)
        entity.schedule_update_ha_state = MagicMock()
        entity._attr_native_value = 50

        # Setting value 100.0, should write 1000 to register (100 / 0.1)
        entity.set_native_value(100.0)

        hass.create_task.assert_called_once()

    def test_set_native_value_no_write_when_unchanged(self):
        """Test set_native_value does nothing when value is unchanged."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {}}}
        hass.create_task = MagicMock()
        base_sensor = create_mock_base_sensor()

        entity = SungrowNumberEntity(hass, base_sensor)
        entity._attr_native_value = 100

        entity.set_native_value(100)  # Same value

        hass.create_task.assert_not_called()

    def test_set_native_value_no_write_when_no_write_register(self):
        """Test set_native_value does nothing when no write register."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {}}}
        hass.create_task = MagicMock()
        base_sensor = create_mock_base_sensor(
            registers=[33000, 33001],  # Multi-register without explicit write_register
            write_register=None
        )

        entity = SungrowNumberEntity(hass, base_sensor)
        entity._write_register = None  # Explicitly None
        entity._attr_native_value = 50

        entity.set_native_value(100)

        hass.create_task.assert_not_called()

    def test_handle_modbus_update_updates_value(self):
        """Test handle_modbus_update updates entity value on register change."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {}}}
        controller = create_mock_controller()
        base_sensor = create_mock_base_sensor(
            registers=[33000],
            multiplier=1,
            controller=controller
        )

        entity = SungrowNumberEntity(hass, base_sensor)
        entity.schedule_update_ha_state = MagicMock()

        # Simulate Modbus update event
        event = MagicMock()
        event.data = {
            REGISTER: 33000,
            VALUE: 150,
            CONTROLLER: "10.0.0.1",
            SLAVE: 1
        }

        entity.handle_modbus_update(event)

        assert entity._attr_native_value == 150
        entity.schedule_update_ha_state.assert_called_once()

    def test_handle_modbus_update_ignores_wrong_register(self):
        """Test handle_modbus_update ignores updates for other registers."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {}}}
        controller = create_mock_controller()
        base_sensor = create_mock_base_sensor(
            registers=[33000],
            controller=controller
        )

        entity = SungrowNumberEntity(hass, base_sensor)
        entity._attr_native_value = 100
        entity.schedule_update_ha_state = MagicMock()

        # Event for different register
        event = MagicMock()
        event.data = {
            REGISTER: 33999,  # Different register
            VALUE: 999,
            CONTROLLER: "10.0.0.1",
            SLAVE: 1
        }

        entity.handle_modbus_update(event)

        # Value should not change
        assert entity._attr_native_value == 100
        entity.schedule_update_ha_state.assert_not_called()

    def test_handle_modbus_update_ignores_wrong_controller(self):
        """Test handle_modbus_update ignores updates for other controllers."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {}}}
        controller = create_mock_controller(host="10.0.0.1", slave=1)
        base_sensor = create_mock_base_sensor(
            registers=[33000],
            controller=controller
        )

        entity = SungrowNumberEntity(hass, base_sensor)
        entity._attr_native_value = 100
        entity.schedule_update_ha_state = MagicMock()

        # Event for different controller
        event = MagicMock()
        event.data = {
            REGISTER: 33000,
            VALUE: 999,
            CONTROLLER: "10.0.0.2",  # Different host
            SLAVE: 1
        }

        entity.handle_modbus_update(event)

        # Value should not change
        assert entity._attr_native_value == 100
        entity.schedule_update_ha_state.assert_not_called()

    def test_handle_modbus_update_waits_for_all_registers(self):
        """Test handle_modbus_update waits for all registers before updating."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {}}}
        controller = create_mock_controller()
        base_sensor = create_mock_base_sensor(
            registers=[33000, 33001],  # Multi-register
            controller=controller
        )

        entity = SungrowNumberEntity(hass, base_sensor)
        entity.schedule_update_ha_state = MagicMock()

        # First register update
        event1 = MagicMock()
        event1.data = {
            REGISTER: 33000,
            VALUE: 100,
            CONTROLLER: "10.0.0.1",
            SLAVE: 1
        }

        entity.handle_modbus_update(event1)

        # Should not update yet - waiting for second register
        entity.schedule_update_ha_state.assert_not_called()

        # Second register update
        event2 = MagicMock()
        event2.data = {
            REGISTER: 33001,
            VALUE: 200,
            CONTROLLER: "10.0.0.1",
            SLAVE: 1
        }

        entity.handle_modbus_update(event2)

        # Now should update
        entity.schedule_update_ha_state.assert_called_once()

    def test_device_info_returns_controller_info(self):
        """Test device_info returns controller's device info."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {}}}
        controller = create_mock_controller()
        base_sensor = create_mock_base_sensor(controller=controller)

        entity = SungrowNumberEntity(hass, base_sensor)

        assert entity.device_info == controller.device_info

    def test_entity_hidden_sets_unavailable(self):
        """Test hidden sensor makes entity unavailable."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {}}}
        base_sensor = create_mock_base_sensor(hidden=True)

        entity = SungrowNumberEntity(hass, base_sensor)

        assert entity._attr_available is False

    def test_entity_enabled_default(self):
        """Test entity enabled default matches sensor enabled flag."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {}}}
        base_sensor = create_mock_base_sensor(enabled=False)

        entity = SungrowNumberEntity(hass, base_sensor)

        assert entity._attr_entity_registry_enabled_default is False


class TestNumberEntityLimits:
    """Test number entity min/max/step handling."""

    def test_min_max_step_from_sensor(self):
        """Test min/max/step values come from base sensor."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {}}}
        base_sensor = create_mock_base_sensor(
            min_value=-100,
            max_value=100,
            step=5
        )

        entity = SungrowNumberEntity(hass, base_sensor)

        assert entity._attr_native_min_value == -100
        assert entity._attr_native_max_value == 100
        assert entity._attr_native_step == 5

    def test_step_attribute_matches_native_step(self):
        """Test step and native_step attributes are consistent."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {}}}
        base_sensor = create_mock_base_sensor(step=0.5)

        entity = SungrowNumberEntity(hass, base_sensor)

        assert entity._attr_step == 0.5
        assert entity._attr_native_step == 0.5

    def test_set_value_rounds_to_step(self):
        """Test set_native_value rounds value appropriately."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {}}}
        hass.create_task = MagicMock()
        controller = create_mock_controller()
        base_sensor = create_mock_base_sensor(
            multiplier=1,
            controller=controller
        )

        entity = SungrowNumberEntity(hass, base_sensor)
        entity.schedule_update_ha_state = MagicMock()
        entity._attr_native_value = 0

        # Value should be written as integer
        entity.set_native_value(50.7)

        hass.create_task.assert_called_once()
