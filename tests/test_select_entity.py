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

        # HYBRID should create select entities (RC Force, Work Mode, Battery Model)
        assert len(captured_entities) >= 2  # At minimum RC Force and Work Mode

    @pytest.mark.asyncio
    async def test_hybrid_with_hv_battery_creates_hv_battery_model_options(self):
        """Test HYBRID with HV battery creates HV battery model select."""
        controller = create_mock_controller(
            inverter_type=InverterType.HYBRID,
            features={InverterFeature.HV_BATTERY}
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

        # Find battery model entity
        battery_entities = [e for e in captured_entities if "Battery Model" in e._attr_name]
        assert len(battery_entities) == 1

        # HV battery should have HV options like PYLON_HV
        battery_options = battery_entities[0]._attr_options
        assert "PYLON_HV" in battery_options

    @pytest.mark.asyncio
    async def test_hybrid_without_hv_battery_creates_lv_battery_model_options(self):
        """Test HYBRID without HV creates LV battery model select."""
        controller = create_mock_controller(
            inverter_type=InverterType.HYBRID,
            features=set()  # No HV_BATTERY
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

        # Find battery model entity
        battery_entities = [e for e in captured_entities if "Battery Model" in e._attr_name]
        assert len(battery_entities) == 1

        # LV battery should have LV options like PYLON_LV
        battery_options = battery_entities[0]._attr_options
        assert "PYLON_LV" in battery_options

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

        # STRING should have no select entities (no battery, no RC force)
        assert len(captured_entities) == 0


class TestSungrowSelectEntity:
    """Test SungrowSelectEntity behavior."""

    def test_entity_initialization_with_on_value(self):
        """Test select entity initialization with on_value options."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {}}}
        controller = create_mock_controller()

        entity_def = {
            "register": 43135,
            "name": "RC Force Charge/Discharge",
            "entities": [
                {"name": "None", "on_value": 0},
                {"name": "Force Charge", "on_value": 1},
                {"name": "Force Discharge", "on_value": 2},
            ]
        }

        entity = SungrowSelectEntity(hass, controller, entity_def)

        assert entity._attr_name == "RC Force Charge/Discharge"
        assert entity._register == 43135
        assert len(entity._attr_options) == 3
        assert "None" in entity._attr_options
        assert "Force Charge" in entity._attr_options

    def test_entity_initialization_with_bit_position(self):
        """Test select entity initialization with bit_position options."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {}}}
        controller = create_mock_controller()

        entity_def = {
            "register": 43110,
            "name": "Work Mode",
            "entities": [
                {"bit_position": 0, "name": "Self-Use", "conflicts_with": [0, 6, 11]},
                {"bit_position": 6, "name": "Feed-in Priority", "conflicts_with": [0, 6, 11]},
            ]
        }

        entity = SungrowSelectEntity(hass, controller, entity_def)

        assert entity._attr_name == "Work Mode"
        assert len(entity._attr_options) == 2
        assert "Self-Use" in entity._attr_options
        assert "Feed-in Priority" in entity._attr_options

    def test_current_option_with_on_value(self):
        """Test current_option returns correct option based on register value."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {"43135": 1}}}  # Value 1 = Force Charge
        controller = create_mock_controller()

        entity_def = {
            "register": 43135,
            "name": "RC Force",
            "entities": [
                {"name": "None", "on_value": 0},
                {"name": "Force Charge", "on_value": 1},
                {"name": "Force Discharge", "on_value": 2},
            ]
        }

        entity = SungrowSelectEntity(hass, controller, entity_def)

        assert entity.current_option == "Force Charge"

    def test_current_option_with_bit_position(self):
        """Test current_option returns correct option based on bit position."""
        hass = MagicMock()
        # Bit 6 set = Feed-in Priority (0b1000000 = 64)
        hass.data = {DOMAIN: {VALUES: {"43110": 64}}}
        controller = create_mock_controller()

        entity_def = {
            "register": 43110,
            "name": "Work Mode",
            "entities": [
                {"bit_position": 0, "name": "Self-Use", "conflicts_with": [0, 6, 11]},
                {"bit_position": 6, "name": "Feed-in Priority", "conflicts_with": [0, 6, 11]},
            ]
        }

        entity = SungrowSelectEntity(hass, controller, entity_def)

        assert entity.current_option == "Feed-in Priority"

    def test_current_option_with_requires(self):
        """Test current_option respects requires condition."""
        hass = MagicMock()
        # Bit 0 and bit 1 both set = Self-Use + TOU (0b11 = 3)
        hass.data = {DOMAIN: {VALUES: {"43110": 3}}}
        controller = create_mock_controller()

        entity_def = {
            "register": 43110,
            "name": "Work Mode",
            "entities": [
                {"bit_position": 0, "name": "Self-Use", "conflicts_with": [0, 6, 11]},
                {"bit_position": 0, "name": "Self-Use + TOU", "conflicts_with": [0, 6, 11], "requires": [1]},
            ]
        }

        entity = SungrowSelectEntity(hass, controller, entity_def)

        # Should return Self-Use + TOU because both bit 0 and bit 1 are set
        assert entity.current_option == "Self-Use + TOU"

    def test_current_option_no_cache_returns_none(self):
        """Test current_option returns None when no cache value."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {}}}  # No cached value
        controller = create_mock_controller()

        entity_def = {
            "register": 43135,
            "name": "RC Force",
            "entities": [
                {"name": "None", "on_value": 0},
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
            "register": 43135,
            "name": "RC Force",
            "entities": [
                {"name": "None", "on_value": 0},
                {"name": "Force Charge", "on_value": 1},
            ]
        }

        entity = SungrowSelectEntity(hass, controller, entity_def)
        entity.async_write_ha_state = MagicMock()

        await entity.async_select_option("Force Charge")

        controller.async_write_holding_register.assert_called_once_with(43135, 1)

    def test_set_register_bit_clears_conflicts(self):
        """Test set_register_bit clears conflict bits."""
        hass = MagicMock()
        # Start with bit 6 set (Feed-in Priority)
        hass.data = {DOMAIN: {VALUES: {"43110": 64}}}
        hass.create_task = MagicMock()
        controller = create_mock_controller()

        entity_def = {
            "register": 43110,
            "name": "Work Mode",
            "entities": [
                {"bit_position": 0, "name": "Self-Use", "conflicts_with": [0, 6, 11]},
                {"bit_position": 6, "name": "Feed-in Priority", "conflicts_with": [0, 6, 11]},
            ]
        }

        entity = SungrowSelectEntity(hass, controller, entity_def)

        # Select Self-Use (bit 0), should clear bit 6
        entity.set_register_bit(None, 0, [0, 6, 11], None)

        # Verify write was triggered
        hass.create_task.assert_called_once()

    def test_set_register_bit_sets_requires(self):
        """Test set_register_bit sets required bits."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {"43110": 0}}}
        hass.create_task = MagicMock()
        controller = create_mock_controller()

        entity_def = {
            "register": 43110,
            "name": "Work Mode",
            "entities": [
                {"bit_position": 0, "name": "Self-Use + TOU", "conflicts_with": [0, 6, 11], "requires": [1]},
            ]
        }

        entity = SungrowSelectEntity(hass, controller, entity_def)

        # Select Self-Use + TOU, should set both bit 0 and bit 1
        entity.set_register_bit(None, 0, [0, 6, 11], [1])

        hass.create_task.assert_called_once()

    def test_device_info_returns_controller_info(self):
        """Test device_info returns controller's device info."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {}}}
        controller = create_mock_controller()

        entity_def = {
            "register": 43135,
            "name": "RC Force",
            "entities": []
        }

        entity = SungrowSelectEntity(hass, controller, entity_def)

        assert entity.device_info == controller.device_info
