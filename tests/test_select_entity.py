"""Tests for select entity platform."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from custom_components.sungrow_modbus.const import DOMAIN, CONTROLLER, VALUES
from custom_components.sungrow_modbus.data.enums import InverterType, InverterFeature, PollSpeed
from custom_components.sungrow_modbus.select import async_setup_entry
from custom_components.sungrow_modbus.sensors.sungrow_select_entity import (
    SungrowSelectEntity, get_bit_bool, set_bit
)


def create_mock_controller(host="10.0.0.1", slave=1, inverter_type=InverterType.HYBRID, features=None):
    """Create a mock controller."""
    if features is None:
        features = set()

    controller = MagicMock()
    controller.host = host
    controller.device_id = slave
    controller.slave = slave
    controller.connected.return_value = True
    controller.controller_key = f"{host}:502_{slave}"
    controller.inverter_config = MagicMock()
    controller.inverter_config.type = inverter_type
    controller.inverter_config.features = features
    controller.model = "SH10RT"
    controller.device_serial_number = "SN123456"
    controller.device_info = {
        "identifiers": {(DOMAIN, f"{host}:502_{slave}")},
        "manufacturer": "Sungrow",
        "name": "SH10RT",
    }
    controller.poll_speed = {PollSpeed.FAST: 5, PollSpeed.NORMAL: 15, PollSpeed.SLOW: 30}
    controller.async_write_holding_register = AsyncMock()
    return controller


class TestSelectBitOperations:
    """Test bit manipulation functions in select entity."""

    def test_get_bit_bool_bit_0_set(self):
        """Test get_bit_bool when bit 0 is set."""
        assert get_bit_bool(0b0001, 0) is True
        assert get_bit_bool(0b0001, 1) is False

    def test_get_bit_bool_bit_1_set(self):
        """Test get_bit_bool when bit 1 is set."""
        assert get_bit_bool(0b0010, 0) is False
        assert get_bit_bool(0b0010, 1) is True

    def test_get_bit_bool_multiple_bits(self):
        """Test get_bit_bool with multiple bits set."""
        value = 0b1011  # bits 0, 1, 3 set
        assert get_bit_bool(value, 0) is True
        assert get_bit_bool(value, 1) is True
        assert get_bit_bool(value, 2) is False
        assert get_bit_bool(value, 3) is True

    def test_get_bit_bool_high_bits(self):
        """Test get_bit_bool with high bit positions."""
        value = 1 << 11  # bit 11 set
        assert get_bit_bool(value, 11) is True
        assert get_bit_bool(value, 10) is False
        assert get_bit_bool(value, 12) is False

    def test_set_bit_set_to_true(self):
        """Test set_bit setting a bit to True."""
        result = set_bit(0b0000, 2, True)
        assert result == 0b0100

    def test_set_bit_set_to_false(self):
        """Test set_bit clearing a bit to False."""
        result = set_bit(0b1111, 2, False)
        assert result == 0b1011

    def test_set_bit_already_set(self):
        """Test set_bit when bit is already set."""
        result = set_bit(0b0100, 2, True)
        assert result == 0b0100

    def test_set_bit_already_clear(self):
        """Test set_bit when bit is already clear."""
        result = set_bit(0b0000, 2, False)
        assert result == 0b0000

    def test_set_bit_preserves_other_bits(self):
        """Test set_bit preserves other bits."""
        result = set_bit(0b1010, 0, True)
        assert result == 0b1011


class TestSelectPlatformSetup:
    """Test select platform async_setup_entry."""

    @pytest.mark.asyncio
    async def test_hybrid_creates_select_entities(self):
        """Test HYBRID inverter creates select entities."""
        controller = create_mock_controller(inverter_type=InverterType.HYBRID)

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

        # HYBRID should create EMS Mode and Battery Forced Charge/Discharge selects
        assert len(captured_entities) >= 2

    @pytest.mark.asyncio
    async def test_hybrid_creates_ems_mode_select(self):
        """Test HYBRID creates EMS Mode select with correct options."""
        controller = create_mock_controller(inverter_type=InverterType.HYBRID)

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

        # Find EMS Mode entity
        ems_entities = [e for e in captured_entities if "EMS Mode" in e._attr_name]
        assert len(ems_entities) == 1

        ems_options = ems_entities[0]._attr_options
        assert "Self-consumption" in ems_options
        assert "Forced mode" in ems_options
        assert "VPP" in ems_options

    @pytest.mark.asyncio
    async def test_hybrid_creates_battery_force_charge_select(self):
        """Test HYBRID creates Battery Forced Charge/Discharge select."""
        controller = create_mock_controller(inverter_type=InverterType.HYBRID)

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

        # Find Battery Forced Charge/Discharge entity
        battery_entities = [e for e in captured_entities if "Battery Forced" in e._attr_name]
        assert len(battery_entities) == 1

        battery_options = battery_entities[0]._attr_options
        assert "Stop" in battery_options
        assert "Force Charge" in battery_options
        assert "Force Discharge" in battery_options

    @pytest.mark.asyncio
    async def test_hybrid_with_battery_creates_load_adjustment_select(self):
        """Test HYBRID with battery feature creates Load Adjustment Mode select."""
        controller = create_mock_controller(
            inverter_type=InverterType.HYBRID,
            features={InverterFeature.BATTERY}
        )

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

        # Find Load Adjustment Mode entity
        load_entities = [e for e in captured_entities if "Load Adjustment" in e._attr_name]
        assert len(load_entities) == 1

        load_options = load_entities[0]._attr_options
        assert "Timing" in load_options
        assert "ON/OFF" in load_options
        assert "Disabled" in load_options

    @pytest.mark.asyncio
    async def test_string_inverter_creates_no_select_entities(self):
        """Test STRING inverter creates no select entities."""
        controller = create_mock_controller(inverter_type=InverterType.STRING)

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

        # STRING should have no select entities
        assert len(captured_entities) == 0


class TestSungrowSelectEntity:
    """Test SungrowSelectEntity behavior."""

    def test_entity_initialization_with_on_value(self):
        """Test select entity initialization with on_value options."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {}}}
        controller = create_mock_controller()

        # Using Sungrow register 13050 (Battery Forced Charge/Discharge)
        entity_def = {
            "register": 13050,
            "name": "Battery Forced Charge/Discharge",
            "entities": [
                {"name": "Stop", "on_value": 0xCC},
                {"name": "Force Charge", "on_value": 0xAA},
                {"name": "Force Discharge", "on_value": 0xBB},
            ]
        }

        entity = SungrowSelectEntity(hass, controller, entity_def)

        assert entity._attr_name == "Battery Forced Charge/Discharge"
        assert entity._register == 13050
        assert len(entity._attr_options) == 3
        assert "Stop" in entity._attr_options
        assert "Force Charge" in entity._attr_options

    def test_current_option_with_on_value(self):
        """Test current_option returns correct option based on register value."""
        hass = MagicMock()
        controller = create_mock_controller()

        # Using Sungrow register 13050 - value 0xAA (170) = Force Charge
        # Cache key format is {controller_key}:{register}
        hass.data = {DOMAIN: {VALUES: {f"{controller.controller_key}:13050": 0xAA}}}

        entity_def = {
            "register": 13050,
            "name": "Battery Forced Charge/Discharge",
            "entities": [
                {"name": "Stop", "on_value": 0xCC},
                {"name": "Force Charge", "on_value": 0xAA},
                {"name": "Force Discharge", "on_value": 0xBB},
            ]
        }

        entity = SungrowSelectEntity(hass, controller, entity_def)

        assert entity.current_option == "Force Charge"

    def test_current_option_ems_mode(self):
        """Test current_option for EMS Mode select."""
        hass = MagicMock()
        controller = create_mock_controller()

        # Using Sungrow register 13049 - value 4 = VPP
        # Cache key format is {controller_key}:{register}
        hass.data = {DOMAIN: {VALUES: {f"{controller.controller_key}:13049": 4}}}

        entity_def = {
            "register": 13049,
            "name": "EMS Mode",
            "entities": [
                {"name": "Self-consumption", "on_value": 0},
                {"name": "Forced mode", "on_value": 2},
                {"name": "External EMS", "on_value": 3},
                {"name": "VPP", "on_value": 4},
                {"name": "MicroGrid", "on_value": 8},
            ]
        }

        entity = SungrowSelectEntity(hass, controller, entity_def)

        assert entity.current_option == "VPP"

    def test_current_option_no_cache_returns_none(self):
        """Test current_option returns None when no cache value."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {}}}  # No cached value
        controller = create_mock_controller()

        entity_def = {
            "register": 13050,
            "name": "Battery Forced Charge/Discharge",
            "entities": [
                {"name": "Stop", "on_value": 0xCC},
            ]
        }

        entity = SungrowSelectEntity(hass, controller, entity_def)

        assert entity.current_option is None

    @pytest.mark.asyncio
    async def test_async_select_option_with_on_value(self):
        """Test selecting option writes correct on_value to register."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {}}}
        controller = create_mock_controller()

        entity_def = {
            "register": 13050,
            "name": "Battery Forced Charge/Discharge",
            "entities": [
                {"name": "Stop", "on_value": 0xCC},
                {"name": "Force Charge", "on_value": 0xAA},
            ]
        }

        entity = SungrowSelectEntity(hass, controller, entity_def)
        entity.async_write_ha_state = MagicMock()

        await entity.async_select_option("Force Charge")

        controller.async_write_holding_register.assert_called_once_with(13050, 0xAA)

    @pytest.mark.asyncio
    async def test_async_select_ems_mode(self):
        """Test selecting EMS mode writes correct value."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {}}}
        controller = create_mock_controller()

        entity_def = {
            "register": 13049,
            "name": "EMS Mode",
            "entities": [
                {"name": "Self-consumption", "on_value": 0},
                {"name": "Forced mode", "on_value": 2},
                {"name": "VPP", "on_value": 4},
            ]
        }

        entity = SungrowSelectEntity(hass, controller, entity_def)
        entity.async_write_ha_state = MagicMock()

        await entity.async_select_option("Forced mode")

        controller.async_write_holding_register.assert_called_once_with(13049, 2)

    def test_device_info_returns_controller_info(self):
        """Test device_info returns controller's device info."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {}}}
        controller = create_mock_controller()

        entity_def = {
            "register": 13050,
            "name": "Battery Forced Charge/Discharge",
            "entities": []
        }

        entity = SungrowSelectEntity(hass, controller, entity_def)

        assert entity.device_info == controller.device_info
