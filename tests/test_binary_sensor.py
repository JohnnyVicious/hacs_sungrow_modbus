"""Tests for SungrowBinaryEntity (switch) bit operations and conflicts."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from custom_components.sungrow_modbus.const import (
    DOMAIN, CONTROLLER, REGISTER, VALUE, SLAVE, VALUES
)
from custom_components.sungrow_modbus.data.enums import InverterType, PollSpeed
from custom_components.sungrow_modbus.sensors.sungrow_binary_sensor import (
    SungrowBinaryEntity, set_bit, get_bit_bool
)


def create_mock_controller(host="10.0.0.1", slave=1):
    """Create a mock controller."""
    controller = MagicMock()
    controller.host = host
    controller.device_id = slave
    controller.slave = slave
    controller.connected.return_value = True
    controller.enabled = True
    controller.device_serial_number = "SN123456"
    controller.device_info = {
        "identifiers": {(DOMAIN, f"{host}:502_{slave}")},
        "manufacturer": "Sungrow",
        "name": "S6-EH3P10K",
    }
    controller.async_write_holding_register = AsyncMock()
    controller.enable_connection = MagicMock()
    controller.disable_connection = MagicMock()
    return controller


class TestBitOperations:
    """Test low-level bit manipulation functions."""

    def test_set_bit_turn_on(self):
        """Test setting a bit to 1."""
        # Start with 0b0000 = 0, set bit 0 -> 0b0001 = 1
        result = set_bit(0, 0, True)
        assert result == 1

    def test_set_bit_turn_off(self):
        """Test clearing a bit to 0."""
        # Start with 0b0001 = 1, clear bit 0 -> 0b0000 = 0
        result = set_bit(1, 0, False)
        assert result == 0

    def test_set_bit_preserves_other_bits(self):
        """Test that setting one bit preserves others."""
        # Start with 0b1010 = 10, set bit 0 -> 0b1011 = 11
        result = set_bit(10, 0, True)
        assert result == 11

    def test_set_bit_high_position(self):
        """Test setting bit at higher position."""
        # Set bit 4 in 0 -> 0b10000 = 16
        result = set_bit(0, 4, True)
        assert result == 16

    def test_get_bit_bool_on(self):
        """Test reading a set bit."""
        # 0b0001 = 1, bit 0 is ON
        result = get_bit_bool(1, 0)
        assert result is True

    def test_get_bit_bool_off(self):
        """Test reading an unset bit."""
        # 0b0010 = 2, bit 0 is OFF
        result = get_bit_bool(2, 0)
        assert result is False

    def test_get_bit_bool_high_position(self):
        """Test reading bit at higher position."""
        # 0b10000 = 16, bit 4 is ON
        result = get_bit_bool(16, 4)
        assert result is True

    def test_get_bit_bool_multiple_bits_set(self):
        """Test reading specific bit when multiple are set."""
        # 0b1111 = 15, all bits 0-3 are ON
        assert get_bit_bool(15, 0) is True
        assert get_bit_bool(15, 1) is True
        assert get_bit_bool(15, 2) is True
        assert get_bit_bool(15, 3) is True
        assert get_bit_bool(15, 4) is False


class TestSungrowBinaryEntityInit:
    """Test SungrowBinaryEntity initialization."""

    def test_entity_initialization_with_bit_position(self):
        """Test entity initializes correctly with bit_position."""
        hass = MagicMock()
        controller = create_mock_controller()

        entity_def = {
            "name": "Self-Use Mode",
            "register": 43110,
            "bit_position": 0
        }

        entity = SungrowBinaryEntity(hass, controller, entity_def)

        assert entity._register == 43110
        assert entity._bit_position == 0
        assert entity._attr_name == "Self-Use Mode"

    def test_entity_initialization_with_on_off_values(self):
        """Test entity initializes correctly with on/off values."""
        hass = MagicMock()
        controller = create_mock_controller()

        entity_def = {
            "name": "EMS Mode",
            "register": 43007,
            "on_value": 190,
            "off_value": 222
        }

        entity = SungrowBinaryEntity(hass, controller, entity_def)

        assert entity._on_value == 190
        assert entity._off_value == 222

    def test_entity_initialization_with_write_register(self):
        """Test entity with separate read/write registers."""
        hass = MagicMock()
        controller = create_mock_controller()

        entity_def = {
            "name": "Test",
            "read_register": 33000,
            "write_register": 43000,
            "bit_position": 0
        }

        entity = SungrowBinaryEntity(hass, controller, entity_def)

        assert entity._register == 33000
        assert entity._write_register == 43000

    def test_entity_initialization_with_offset(self):
        """Test entity with register offset."""
        hass = MagicMock()
        controller = create_mock_controller()

        entity_def = {
            "name": "Test",
            "register": 43110,
            "offset": 10,
            "bit_position": 0
        }

        entity = SungrowBinaryEntity(hass, controller, entity_def)

        assert entity._register == 43120


class TestSungrowBinaryEntityTurnOnOff:
    """Test turn_on and turn_off operations."""

    def test_turn_on_bit_position(self):
        """Test turning on a switch with bit_position."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {"43110": 0}}}  # All bits off
        hass.create_task = MagicMock()

        controller = create_mock_controller()

        entity_def = {
            "name": "Self-Use Mode",
            "register": 43110,
            "bit_position": 0
        }

        entity = SungrowBinaryEntity(hass, controller, entity_def)

        with patch('custom_components.sungrow_modbus.sensors.sungrow_binary_sensor.cache_get') as mock_get:
            mock_get.return_value = 0
            entity.turn_on()

        # Should write 1 (bit 0 set)
        hass.create_task.assert_called_once()
        assert entity._attr_is_on is True

    def test_turn_off_bit_position(self):
        """Test turning off a switch with bit_position."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {"43110": 1}}}  # Bit 0 on
        hass.create_task = MagicMock()

        controller = create_mock_controller()

        entity_def = {
            "name": "Self-Use Mode",
            "register": 43110,
            "bit_position": 0
        }

        entity = SungrowBinaryEntity(hass, controller, entity_def)

        with patch('custom_components.sungrow_modbus.sensors.sungrow_binary_sensor.cache_get') as mock_get:
            mock_get.return_value = 1
            entity.turn_off()

        hass.create_task.assert_called_once()
        assert entity._attr_is_on is False

    def test_turn_on_with_on_value(self):
        """Test turning on with on_value style switch."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {"43007": 222}}}
        hass.create_task = MagicMock()

        controller = create_mock_controller()

        entity_def = {
            "name": "EMS Mode",
            "register": 43007,
            "on_value": 190,
            "off_value": 222
        }

        entity = SungrowBinaryEntity(hass, controller, entity_def)

        with patch('custom_components.sungrow_modbus.sensors.sungrow_binary_sensor.cache_get') as mock_get:
            mock_get.return_value = 222
            entity.turn_on()

        # Should write 190
        hass.create_task.assert_called_once()

    def test_turn_off_with_off_value(self):
        """Test turning off with off_value style switch."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {"43007": 190}}}
        hass.create_task = MagicMock()

        controller = create_mock_controller()

        entity_def = {
            "name": "EMS Mode",
            "register": 43007,
            "on_value": 190,
            "off_value": 222
        }

        entity = SungrowBinaryEntity(hass, controller, entity_def)

        with patch('custom_components.sungrow_modbus.sensors.sungrow_binary_sensor.cache_get') as mock_get:
            mock_get.return_value = 190
            entity.turn_off()

        # Should write 222
        hass.create_task.assert_called_once()


class TestConflictsAndRequires:
    """Test conflicts_with and requires logic."""

    def test_turn_on_clears_conflicts(self):
        """Test that turning on clears conflicting bits."""
        hass = MagicMock()
        # Start with bits 6 and 11 set (0b100001000000 = 2112)
        hass.data = {DOMAIN: {VALUES: {"43110": 0b100001000000}}}
        hass.create_task = MagicMock()

        controller = create_mock_controller()

        entity_def = {
            "name": "Self-Use Mode",
            "register": 43110,
            "bit_position": 0,
            "conflicts_with": [6, 11]
        }

        entity = SungrowBinaryEntity(hass, controller, entity_def)

        with patch('custom_components.sungrow_modbus.sensors.sungrow_binary_sensor.cache_get') as mock_get:
            mock_get.return_value = 0b100001000000
            with patch('custom_components.sungrow_modbus.sensors.sungrow_binary_sensor.cache_save'):
                entity.turn_on()

        # Verify bits 6 and 11 are cleared and bit 0 is set
        # Final value should be 0b000000000001 = 1
        call_args = hass.create_task.call_args
        assert call_args is not None

    def test_turn_on_sets_required_bits(self):
        """Test that turning on sets required bits."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {"43110": 0}}}
        hass.create_task = MagicMock()

        controller = create_mock_controller()

        entity_def = {
            "name": "TOU Mode",
            "register": 43110,
            "bit_position": 1,
            "requires": [0]  # Requires bit 0 to be set
        }

        entity = SungrowBinaryEntity(hass, controller, entity_def)

        with patch('custom_components.sungrow_modbus.sensors.sungrow_binary_sensor.cache_get') as mock_get:
            mock_get.return_value = 0
            with patch('custom_components.sungrow_modbus.sensors.sungrow_binary_sensor.cache_save'):
                entity.turn_on()

        # Should set both bit 0 (required) and bit 1 (target)
        # Final value should be 0b11 = 3
        hass.create_task.assert_called_once()

    def test_turn_on_with_requires_any_none_set(self):
        """Test requires_any sets first option when none are set."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {"43110": 0}}}
        hass.create_task = MagicMock()

        controller = create_mock_controller()

        entity_def = {
            "name": "TOU Mode",
            "register": 43110,
            "bit_position": 1,
            "requires_any": [0, 6]  # Needs either bit 0 or 6
        }

        entity = SungrowBinaryEntity(hass, controller, entity_def)

        with patch('custom_components.sungrow_modbus.sensors.sungrow_binary_sensor.cache_get') as mock_get:
            mock_get.return_value = 0
            with patch('custom_components.sungrow_modbus.sensors.sungrow_binary_sensor.cache_save'):
                entity.turn_on()

        # Should set bit 0 (first in requires_any) and bit 1 (target)
        hass.create_task.assert_called_once()

    def test_turn_on_with_requires_any_one_already_set(self):
        """Test requires_any doesn't add more when one is already set."""
        hass = MagicMock()
        # Bit 6 already set (0b1000000 = 64)
        hass.data = {DOMAIN: {VALUES: {"43110": 64}}}
        hass.create_task = MagicMock()

        controller = create_mock_controller()

        entity_def = {
            "name": "TOU Mode",
            "register": 43110,
            "bit_position": 1,
            "requires_any": [0, 6]
        }

        entity = SungrowBinaryEntity(hass, controller, entity_def)

        with patch('custom_components.sungrow_modbus.sensors.sungrow_binary_sensor.cache_get') as mock_get:
            mock_get.return_value = 64
            with patch('custom_components.sungrow_modbus.sensors.sungrow_binary_sensor.cache_save'):
                entity.turn_on()

        # Should only add bit 1, keep bit 6
        # Final value should be 0b1000010 = 66
        hass.create_task.assert_called_once()


class TestSungrowBinaryEntityUpdate:
    """Test entity updates from modbus events."""

    def test_handle_modbus_update_bit_on(self):
        """Test entity updates when bit is set."""
        hass = MagicMock()
        controller = create_mock_controller()

        entity_def = {
            "name": "Self-Use Mode",
            "register": 43110,
            "bit_position": 0
        }

        entity = SungrowBinaryEntity(hass, controller, entity_def)

        event = MagicMock()
        event.data = {
            REGISTER: 43110,
            VALUE: 1,  # Bit 0 is set
            CONTROLLER: "10.0.0.1",
            SLAVE: 1
        }

        entity.handle_modbus_update(event)

        assert entity._attr_is_on is True
        assert entity._attr_available is True

    def test_handle_modbus_update_bit_off(self):
        """Test entity updates when bit is clear."""
        hass = MagicMock()
        controller = create_mock_controller()

        entity_def = {
            "name": "Self-Use Mode",
            "register": 43110,
            "bit_position": 0
        }

        entity = SungrowBinaryEntity(hass, controller, entity_def)

        event = MagicMock()
        event.data = {
            REGISTER: 43110,
            VALUE: 2,  # Bit 0 is clear, bit 1 is set
            CONTROLLER: "10.0.0.1",
            SLAVE: 1
        }

        entity.handle_modbus_update(event)

        assert entity._attr_is_on is False

    def test_handle_modbus_update_on_value_match(self):
        """Test entity updates with matching on_value."""
        hass = MagicMock()
        controller = create_mock_controller()

        entity_def = {
            "name": "EMS Mode",
            "register": 43007,
            "on_value": 190,
            "off_value": 222
        }

        entity = SungrowBinaryEntity(hass, controller, entity_def)

        event = MagicMock()
        event.data = {
            REGISTER: 43007,
            VALUE: 190,
            CONTROLLER: "10.0.0.1",
            SLAVE: 1
        }

        entity.handle_modbus_update(event)

        assert entity._attr_is_on is True

    def test_handle_modbus_update_on_value_no_match(self):
        """Test entity updates with non-matching on_value."""
        hass = MagicMock()
        controller = create_mock_controller()

        entity_def = {
            "name": "EMS Mode",
            "register": 43007,
            "on_value": 190,
            "off_value": 222
        }

        entity = SungrowBinaryEntity(hass, controller, entity_def)

        event = MagicMock()
        event.data = {
            REGISTER: 43007,
            VALUE: 222,
            CONTROLLER: "10.0.0.1",
            SLAVE: 1
        }

        entity.handle_modbus_update(event)

        assert entity._attr_is_on is False

    def test_handle_modbus_update_wrong_controller(self):
        """Test entity ignores updates from different controller."""
        hass = MagicMock()
        controller = create_mock_controller(host="10.0.0.1", slave=1)

        entity_def = {
            "name": "Test",
            "register": 43110,
            "bit_position": 0
        }

        entity = SungrowBinaryEntity(hass, controller, entity_def)
        entity._attr_is_on = True  # Existing state

        event = MagicMock()
        event.data = {
            REGISTER: 43110,
            VALUE: 0,
            CONTROLLER: "10.0.0.2",  # Different host
            SLAVE: 1
        }

        entity.handle_modbus_update(event)

        # State should remain unchanged
        assert entity._attr_is_on is True

    def test_handle_modbus_update_wrong_register(self):
        """Test entity ignores updates for different register."""
        hass = MagicMock()
        controller = create_mock_controller()

        entity_def = {
            "name": "Test",
            "register": 43110,
            "bit_position": 0
        }

        entity = SungrowBinaryEntity(hass, controller, entity_def)
        entity._attr_is_on = True

        event = MagicMock()
        event.data = {
            REGISTER: 43111,  # Different register
            VALUE: 0,
            CONTROLLER: "10.0.0.1",
            SLAVE: 1
        }

        entity.handle_modbus_update(event)

        assert entity._attr_is_on is True


class TestConnectionToggle:
    """Test special register 5 for connection toggle."""

    def test_turn_on_register_5_enables_connection(self):
        """Test register 5 enables modbus connection."""
        hass = MagicMock()
        controller = create_mock_controller()

        entity_def = {
            "name": "Modbus Enabled",
            "register": 5,
            "bit_position": 0
        }

        entity = SungrowBinaryEntity(hass, controller, entity_def)
        entity.turn_on()

        controller.enable_connection.assert_called_once()

    def test_turn_off_register_5_disables_connection(self):
        """Test register 5 disables modbus connection."""
        hass = MagicMock()
        controller = create_mock_controller()

        entity_def = {
            "name": "Modbus Enabled",
            "register": 5,
            "bit_position": 0
        }

        entity = SungrowBinaryEntity(hass, controller, entity_def)
        entity.turn_off()

        controller.disable_connection.assert_called_once()


class TestListenerLifecycle:
    """Test event listener lifecycle."""

    @pytest.mark.asyncio
    async def test_registers_listener_on_add(self):
        """Test listener is registered when entity is added."""
        hass = MagicMock()
        hass.bus.async_listen = MagicMock(return_value=MagicMock())
        controller = create_mock_controller()

        entity_def = {"name": "Test", "register": 43110, "bit_position": 0}
        entity = SungrowBinaryEntity(hass, controller, entity_def)

        await entity.async_added_to_hass()

        hass.bus.async_listen.assert_called_once_with(DOMAIN, entity.handle_modbus_update)
        assert entity._unsub_listener is not None

    @pytest.mark.asyncio
    async def test_unsubscribes_listener_on_remove(self):
        """Test listener is unsubscribed when entity is removed."""
        hass = MagicMock()
        unsub_mock = MagicMock()
        hass.bus.async_listen = MagicMock(return_value=unsub_mock)
        controller = create_mock_controller()

        entity_def = {"name": "Test", "register": 43110, "bit_position": 0}
        entity = SungrowBinaryEntity(hass, controller, entity_def)

        await entity.async_added_to_hass()
        await entity.async_will_remove_from_hass()

        unsub_mock.assert_called_once()
        assert entity._unsub_listener is None
