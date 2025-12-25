"""Tests for time entity platform."""
import pytest
from datetime import time
from unittest.mock import MagicMock, AsyncMock, patch

from custom_components.sungrow_modbus.const import (
    DOMAIN, CONTROLLER, TIME_ENTITIES, REGISTER, VALUE, SLAVE, VALUES
)
from custom_components.sungrow_modbus.data.enums import InverterType, InverterFeature, PollSpeed
from custom_components.sungrow_modbus.time import async_setup_entry, SungrowTimeEntity


def create_mock_controller(host="10.0.0.1", slave=1, inverter_type=InverterType.HYBRID, features=None):
    """Create a mock controller."""
    if features is None:
        features = {InverterFeature.V2}

    controller = MagicMock()
    controller.host = host
    controller.device_id = slave
    controller.slave = slave
    controller.connected.return_value = True
    controller.inverter_config = MagicMock()
    controller.inverter_config.type = inverter_type
    controller.inverter_config.features = features
    controller.model = "S6-EH3P10K"
    controller.device_serial_number = "SN123456"
    controller.device_info = {
        "identifiers": {(DOMAIN, f"{host}:502_{slave}")},
        "manufacturer": "Sungrow",
        "name": "S6-EH3P10K",
    }
    controller.poll_speed = {PollSpeed.FAST: 5, PollSpeed.NORMAL: 15, PollSpeed.SLOW: 30}
    controller.async_write_holding_registers = AsyncMock()
    return controller


class TestTimeEntityPlatformSetup:
    """Test time platform async_setup_entry."""

    @pytest.mark.asyncio
    async def test_hybrid_creates_time_charging_slots(self):
        """Test HYBRID inverter creates time-charging slot entities."""
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

        # HYBRID should create 5 slots × 4 times each = 20 time-charging entities
        # Plus 6 Grid ToU slots × 4 times = 24 entities (if V2 feature)
        assert len(captured_entities) >= 20  # At minimum the time-charging slots
        assert TIME_ENTITIES in hass.data[DOMAIN]

        # Verify slot 1 entities exist
        slot1_names = [e._attr_name for e in captured_entities if "Slot 1" in e._attr_name]
        assert len(slot1_names) >= 4  # Charge start/end, discharge start/end

    @pytest.mark.asyncio
    async def test_hybrid_with_v2_creates_grid_tou_slots(self):
        """Test HYBRID with V2 feature creates Grid ToU time slots."""
        controller = create_mock_controller(
            inverter_type=InverterType.HYBRID,
            features={InverterFeature.V2}
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

        # Check for Grid ToU entities
        grid_tou_entities = [e for e in captured_entities if "Grid Time of Use" in e._attr_name]
        # 6 slots × 4 times = 24 Grid ToU entities
        assert len(grid_tou_entities) == 24

    @pytest.mark.asyncio
    async def test_string_inverter_creates_minimal_time_entities(self):
        """Test STRING inverter creates only V2 time entities if available."""
        controller = create_mock_controller(
            inverter_type=InverterType.STRING,
            features={InverterFeature.V2}
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

        # STRING should not have time-charging slots, only Grid ToU if V2
        time_charging = [e for e in captured_entities if "Time-Charging" in e._attr_name]
        assert len(time_charging) == 0

    @pytest.mark.asyncio
    async def test_string_without_v2_creates_no_time_entities(self):
        """Test STRING without V2 creates no time entities."""
        controller = create_mock_controller(
            inverter_type=InverterType.STRING,
            features=set()  # No V2
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

        assert len(captured_entities) == 0


class TestSungrowTimeEntity:
    """Test SungrowTimeEntity behavior."""

    def test_entity_initialization(self):
        """Test time entity is properly initialized."""
        hass = MagicMock()
        controller = create_mock_controller()

        entity_def = {
            "name": "Time-Charging Charge Start (Slot 1)",
            "register": 43143,
            "enabled": True
        }

        entity = SungrowTimeEntity(hass, controller, entity_def)

        assert entity._register == 43143
        assert entity._attr_name == "Time-Charging Charge Start (Slot 1)"
        assert entity._attr_available is True
        assert "SN123456" in entity._attr_unique_id

    def test_entity_unique_id_with_serial(self):
        """Test unique ID uses serial number when available."""
        hass = MagicMock()
        controller = create_mock_controller()
        controller.device_serial_number = "ABC123"

        entity_def = {"name": "Test", "register": 43143, "enabled": True}
        entity = SungrowTimeEntity(hass, controller, entity_def)

        assert "ABC123" in entity._attr_unique_id

    def test_entity_unique_id_without_serial(self):
        """Test unique ID uses host when serial not available."""
        hass = MagicMock()
        controller = create_mock_controller()
        controller.device_serial_number = None

        entity_def = {"name": "Test", "register": 43143, "enabled": True}
        entity = SungrowTimeEntity(hass, controller, entity_def)

        assert "10.0.0.1" in entity._attr_unique_id

    @pytest.mark.asyncio
    async def test_entity_set_value(self):
        """Test setting time value writes to controller."""
        hass = MagicMock()
        controller = create_mock_controller()

        entity_def = {"name": "Test", "register": 43143, "enabled": True}
        entity = SungrowTimeEntity(hass, controller, entity_def)
        entity.async_write_ha_state = MagicMock()  # Mock to avoid hass dependency

        new_time = time(hour=14, minute=30)
        await entity.async_set_value(new_time)

        controller.async_write_holding_registers.assert_called_once_with(43143, [14, 30])
        assert entity._attr_native_value == new_time

    @pytest.mark.asyncio
    async def test_entity_handle_modbus_update_valid_time(self):
        """Test entity updates with valid time values from cache."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {}}}
        controller = create_mock_controller()

        entity_def = {"name": "Test", "register": 43143, "enabled": True}
        entity = SungrowTimeEntity(hass, controller, entity_def)
        entity.schedule_update_ha_state = MagicMock()

        # Simulate cache values for hour and minute
        hass.data[DOMAIN][VALUES]["43143"] = 14  # hour
        hass.data[DOMAIN][VALUES]["43144"] = 30  # minute

        event = MagicMock()
        event.data = {
            REGISTER: 43143,
            VALUE: 14,
            CONTROLLER: "10.0.0.1",
            SLAVE: 1
        }

        with patch('custom_components.sungrow_modbus.time.cache_get') as mock_cache:
            mock_cache.side_effect = lambda h, r: {43143: 14, 43144: 30}.get(r)
            entity.handle_modbus_update(event)

        assert entity._attr_native_value == time(hour=14, minute=30)
        assert entity._attr_available is True

    @pytest.mark.asyncio
    async def test_entity_handle_modbus_update_invalid_hour(self):
        """Test entity becomes unavailable with invalid hour."""
        hass = MagicMock()
        controller = create_mock_controller()

        entity_def = {"name": "Test", "register": 43143, "enabled": True}
        entity = SungrowTimeEntity(hass, controller, entity_def)
        entity.schedule_update_ha_state = MagicMock()

        event = MagicMock()
        event.data = {
            REGISTER: 43143,
            VALUE: 25,  # Invalid hour (> 23)
            CONTROLLER: "10.0.0.1",
            SLAVE: 1
        }

        with patch('custom_components.sungrow_modbus.time.cache_get') as mock_cache:
            mock_cache.side_effect = lambda h, r: {43143: 25, 43144: 30}.get(r)
            entity.handle_modbus_update(event)

        assert entity._attr_available is False

    @pytest.mark.asyncio
    async def test_entity_handle_modbus_update_invalid_minute(self):
        """Test entity becomes unavailable with invalid minute."""
        hass = MagicMock()
        controller = create_mock_controller()

        entity_def = {"name": "Test", "register": 43143, "enabled": True}
        entity = SungrowTimeEntity(hass, controller, entity_def)
        entity.schedule_update_ha_state = MagicMock()

        event = MagicMock()
        event.data = {
            REGISTER: 43143,
            VALUE: 14,
            CONTROLLER: "10.0.0.1",
            SLAVE: 1
        }

        with patch('custom_components.sungrow_modbus.time.cache_get') as mock_cache:
            mock_cache.side_effect = lambda h, r: {43143: 14, 43144: 70}.get(r)  # 70 is invalid minute
            entity.handle_modbus_update(event)

        assert entity._attr_available is False

    @pytest.mark.asyncio
    async def test_entity_handle_modbus_update_missing_minute(self):
        """Test entity becomes unavailable when minute not in cache."""
        hass = MagicMock()
        controller = create_mock_controller()

        entity_def = {"name": "Test", "register": 43143, "enabled": True}
        entity = SungrowTimeEntity(hass, controller, entity_def)
        entity.schedule_update_ha_state = MagicMock()

        event = MagicMock()
        event.data = {
            REGISTER: 43143,
            VALUE: 14,
            CONTROLLER: "10.0.0.1",
            SLAVE: 1
        }

        with patch('custom_components.sungrow_modbus.time.cache_get') as mock_cache:
            mock_cache.side_effect = lambda h, r: {43143: 14}.get(r)  # minute not in cache
            entity.handle_modbus_update(event)

        assert entity._attr_available is False

    @pytest.mark.asyncio
    async def test_entity_handle_modbus_update_wrong_controller(self):
        """Test entity ignores updates from wrong controller."""
        hass = MagicMock()
        controller = create_mock_controller(host="10.0.0.1", slave=1)

        entity_def = {"name": "Test", "register": 43143, "enabled": True}
        entity = SungrowTimeEntity(hass, controller, entity_def)
        entity._attr_native_value = time(hour=10, minute=0)  # Existing value

        event = MagicMock()
        event.data = {
            REGISTER: 43143,
            VALUE: 14,
            CONTROLLER: "10.0.0.2",  # Different host
            SLAVE: 1
        }

        entity.handle_modbus_update(event)

        # Value should remain unchanged
        assert entity._attr_native_value == time(hour=10, minute=0)

    @pytest.mark.asyncio
    async def test_entity_handle_modbus_update_wrong_register(self):
        """Test entity ignores updates for unrelated registers."""
        hass = MagicMock()
        controller = create_mock_controller()

        entity_def = {"name": "Test", "register": 43143, "enabled": True}
        entity = SungrowTimeEntity(hass, controller, entity_def)
        entity._attr_native_value = time(hour=10, minute=0)

        event = MagicMock()
        event.data = {
            REGISTER: 43999,  # Different register
            VALUE: 14,
            CONTROLLER: "10.0.0.1",
            SLAVE: 1
        }

        entity.handle_modbus_update(event)

        # Value should remain unchanged
        assert entity._attr_native_value == time(hour=10, minute=0)

    @pytest.mark.asyncio
    async def test_entity_async_added_to_hass_registers_listener(self):
        """Test entity registers event listener when added to hass."""
        hass = MagicMock()
        hass.bus.async_listen = MagicMock(return_value=MagicMock())
        controller = create_mock_controller()

        entity_def = {"name": "Test", "register": 43143, "enabled": True}
        entity = SungrowTimeEntity(hass, controller, entity_def)

        with patch.object(entity, 'async_get_last_sensor_data', new_callable=AsyncMock) as mock_restore:
            mock_restore.return_value = None
            await entity.async_added_to_hass()

        hass.bus.async_listen.assert_called_once_with(DOMAIN, entity.handle_modbus_update)
        assert entity._unsub_listener is not None

    @pytest.mark.asyncio
    async def test_entity_async_will_remove_cleanup(self):
        """Test entity cleans up listener when removed."""
        hass = MagicMock()
        unsub_mock = MagicMock()
        hass.bus.async_listen = MagicMock(return_value=unsub_mock)
        controller = create_mock_controller()

        entity_def = {"name": "Test", "register": 43143, "enabled": True}
        entity = SungrowTimeEntity(hass, controller, entity_def)

        with patch.object(entity, 'async_get_last_sensor_data', new_callable=AsyncMock) as mock_restore:
            mock_restore.return_value = None
            await entity.async_added_to_hass()

        await entity.async_will_remove_from_hass()

        unsub_mock.assert_called_once()
        assert entity._unsub_listener is None

    @pytest.mark.asyncio
    async def test_entity_restores_state(self):
        """Test entity restores previous state on startup."""
        hass = MagicMock()
        hass.bus.async_listen = MagicMock(return_value=MagicMock())
        controller = create_mock_controller()

        entity_def = {"name": "Test", "register": 43143, "enabled": True}
        entity = SungrowTimeEntity(hass, controller, entity_def)

        mock_state = MagicMock()
        mock_state.native_value = time(hour=8, minute=30)

        with patch.object(entity, 'async_get_last_sensor_data', new_callable=AsyncMock) as mock_restore:
            mock_restore.return_value = mock_state
            await entity.async_added_to_hass()

        assert entity._attr_native_value == time(hour=8, minute=30)


class TestTimeEdgeCases:
    """Test edge cases for time entities."""

    @pytest.mark.asyncio
    async def test_midnight_time(self):
        """Test setting midnight (00:00)."""
        hass = MagicMock()
        controller = create_mock_controller()

        entity_def = {"name": "Test", "register": 43143, "enabled": True}
        entity = SungrowTimeEntity(hass, controller, entity_def)
        entity.async_write_ha_state = MagicMock()

        await entity.async_set_value(time(hour=0, minute=0))

        controller.async_write_holding_registers.assert_called_once_with(43143, [0, 0])

    @pytest.mark.asyncio
    async def test_end_of_day_time(self):
        """Test setting end of day (23:59)."""
        hass = MagicMock()
        controller = create_mock_controller()

        entity_def = {"name": "Test", "register": 43143, "enabled": True}
        entity = SungrowTimeEntity(hass, controller, entity_def)
        entity.async_write_ha_state = MagicMock()

        await entity.async_set_value(time(hour=23, minute=59))

        controller.async_write_holding_registers.assert_called_once_with(43143, [23, 59])
