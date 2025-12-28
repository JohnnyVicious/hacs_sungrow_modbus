"""Tests for time entity platform."""

from datetime import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.sungrow_modbus.const import CONTROLLER, DOMAIN, REGISTER, SLAVE, TIME_ENTITIES, VALUE, VALUES
from custom_components.sungrow_modbus.data.enums import InverterFeature, InverterType, PollSpeed
from custom_components.sungrow_modbus.time import SungrowTimeEntity, async_setup_entry


def create_mock_controller(host="10.0.0.1", slave=1, inverter_type=InverterType.HYBRID, features=None):
    """Create a mock controller."""
    if features is None:
        features = {InverterFeature.BATTERY}

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
    controller.async_write_holding_registers = AsyncMock()
    return controller


class TestTimeEntityPlatformSetup:
    """Test time platform async_setup_entry."""

    @pytest.mark.asyncio
    async def test_hybrid_with_battery_creates_load_timing_entities(self):
        """Test HYBRID inverter with BATTERY feature creates load timing entities."""
        controller = create_mock_controller(inverter_type=InverterType.HYBRID, features={InverterFeature.BATTERY})

        hass = MagicMock()
        hass.data = {DOMAIN: {CONTROLLER: {"10.0.0.1:502_1": controller}}}

        config_entry = MagicMock()
        config_entry.data = {"host": "10.0.0.1", "port": 502, "slave": 1}
        config_entry.options = {}

        captured_entities = []

        def capture_add_devices(entities, update_immediately):
            captured_entities.extend(entities)

        await async_setup_entry(hass, config_entry, capture_add_devices)

        # HYBRID with BATTERY should create 6 load timing entities:
        # - Load Timing Period 1 Start/End (2)
        # - Load Timing Period 2 Start/End (2)
        # - Load Power Optimized Period Start/End (2)
        assert len(captured_entities) == 6
        assert TIME_ENTITIES in hass.data[DOMAIN]

        # Verify entity names
        entity_names = [e._attr_name for e in captured_entities]
        assert "Load Timing Period 1 Start" in entity_names
        assert "Load Timing Period 1 End" in entity_names
        assert "Load Timing Period 2 Start" in entity_names
        assert "Load Timing Period 2 End" in entity_names
        assert "Load Power Optimized Period Start" in entity_names
        assert "Load Power Optimized Period End" in entity_names

    @pytest.mark.asyncio
    async def test_hybrid_without_battery_creates_no_time_entities(self):
        """Test HYBRID inverter without BATTERY feature creates no time entities."""
        controller = create_mock_controller(
            inverter_type=InverterType.HYBRID,
            features=set(),  # No BATTERY feature
        )

        hass = MagicMock()
        hass.data = {DOMAIN: {CONTROLLER: {"10.0.0.1:502_1": controller}}}

        config_entry = MagicMock()
        config_entry.data = {"host": "10.0.0.1", "port": 502, "slave": 1}
        config_entry.options = {}

        captured_entities = []

        def capture_add_devices(entities, update_immediately):
            captured_entities.extend(entities)

        await async_setup_entry(hass, config_entry, capture_add_devices)

        # HYBRID without BATTERY should have no time entities
        assert len(captured_entities) == 0

    @pytest.mark.asyncio
    async def test_string_inverter_creates_no_time_entities(self):
        """Test STRING inverter creates no time entities."""
        controller = create_mock_controller(
            inverter_type=InverterType.STRING,
            features={InverterFeature.BATTERY},  # Even with battery, STRING has no load timing
        )

        hass = MagicMock()
        hass.data = {DOMAIN: {CONTROLLER: {"10.0.0.1:502_1": controller}}}

        config_entry = MagicMock()
        config_entry.data = {"host": "10.0.0.1", "port": 502, "slave": 1}
        config_entry.options = {}

        captured_entities = []

        def capture_add_devices(entities, update_immediately):
            captured_entities.extend(entities)

        await async_setup_entry(hass, config_entry, capture_add_devices)

        # STRING should have no time entities
        assert len(captured_entities) == 0

    @pytest.mark.asyncio
    async def test_load_timing_registers_are_correct(self):
        """Test that load timing entities use correct Sungrow registers."""
        controller = create_mock_controller(inverter_type=InverterType.HYBRID, features={InverterFeature.BATTERY})

        hass = MagicMock()
        hass.data = {DOMAIN: {CONTROLLER: {"10.0.0.1:502_1": controller}}}

        config_entry = MagicMock()
        config_entry.data = {"host": "10.0.0.1", "port": 502, "slave": 1}
        config_entry.options = {}

        captured_entities = []

        def capture_add_devices(entities, update_immediately):
            captured_entities.extend(entities)

        await async_setup_entry(hass, config_entry, capture_add_devices)

        # Verify correct Sungrow registers are used
        registers = {e._attr_name: e._register for e in captured_entities}
        assert registers["Load Timing Period 1 Start"] == 13003
        assert registers["Load Timing Period 1 End"] == 13005
        assert registers["Load Timing Period 2 Start"] == 13007
        assert registers["Load Timing Period 2 End"] == 13009
        assert registers["Load Power Optimized Period Start"] == 13012
        assert registers["Load Power Optimized Period End"] == 13014


class TestSungrowTimeEntity:
    """Test SungrowTimeEntity behavior."""

    def test_entity_initialization(self):
        """Test time entity is properly initialized."""
        hass = MagicMock()
        controller = create_mock_controller()

        entity_def = {"name": "Load Timing Period 1 Start", "register": 13003, "enabled": True}

        entity = SungrowTimeEntity(hass, controller, entity_def)

        assert entity._register == 13003
        assert entity._attr_name == "Load Timing Period 1 Start"
        assert entity._attr_available is True
        assert "SN123456" in entity._attr_unique_id

    def test_entity_unique_id_with_serial(self):
        """Test unique ID uses serial number when available."""
        hass = MagicMock()
        controller = create_mock_controller()
        controller.device_serial_number = "ABC123"

        entity_def = {"name": "Test", "register": 13003, "enabled": True}
        entity = SungrowTimeEntity(hass, controller, entity_def)

        assert "ABC123" in entity._attr_unique_id

    def test_entity_unique_id_without_serial(self):
        """Test unique ID uses host when serial not available."""
        hass = MagicMock()
        controller = create_mock_controller()
        controller.device_serial_number = None

        entity_def = {"name": "Test", "register": 13003, "enabled": True}
        entity = SungrowTimeEntity(hass, controller, entity_def)

        assert "10.0.0.1" in entity._attr_unique_id

    @pytest.mark.asyncio
    async def test_entity_set_value(self):
        """Test setting time value writes to controller."""
        hass = MagicMock()
        controller = create_mock_controller()

        entity_def = {"name": "Test", "register": 13003, "enabled": True}
        entity = SungrowTimeEntity(hass, controller, entity_def)
        entity.async_write_ha_state = MagicMock()  # Mock to avoid hass dependency

        new_time = time(hour=14, minute=30)
        await entity.async_set_value(new_time)

        controller.async_write_holding_registers.assert_called_once_with(13003, [14, 30])
        assert entity._attr_native_value == new_time

    @pytest.mark.asyncio
    async def test_entity_handle_modbus_update_valid_time(self):
        """Test entity updates with valid time values from cache."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {}}}
        controller = create_mock_controller()

        entity_def = {"name": "Test", "register": 13003, "enabled": True}
        entity = SungrowTimeEntity(hass, controller, entity_def)
        entity.schedule_update_ha_state = MagicMock()

        # Simulate cache values for hour and minute
        hass.data[DOMAIN][VALUES]["13003"] = 14  # hour
        hass.data[DOMAIN][VALUES]["13004"] = 30  # minute

        event = MagicMock()
        event.data = {REGISTER: 13003, VALUE: 14, CONTROLLER: "10.0.0.1", SLAVE: 1}

        with patch("custom_components.sungrow_modbus.time.cache_get") as mock_cache:
            # cache_get takes 3 args: hass, register, controller_key
            mock_cache.side_effect = lambda h, r, k: {13003: 14, 13004: 30}.get(r)
            entity.handle_modbus_update(event)

        assert entity._attr_native_value == time(hour=14, minute=30)
        assert entity._attr_available is True

    @pytest.mark.asyncio
    async def test_entity_handle_modbus_update_invalid_hour(self):
        """Test entity becomes unavailable with invalid hour."""
        hass = MagicMock()
        controller = create_mock_controller()

        entity_def = {"name": "Test", "register": 13003, "enabled": True}
        entity = SungrowTimeEntity(hass, controller, entity_def)
        entity.schedule_update_ha_state = MagicMock()

        event = MagicMock()
        event.data = {
            REGISTER: 13003,
            VALUE: 25,  # Invalid hour (> 23)
            CONTROLLER: "10.0.0.1",
            SLAVE: 1,
        }

        with patch("custom_components.sungrow_modbus.time.cache_get") as mock_cache:
            mock_cache.side_effect = lambda h, r, k: {13003: 25, 13004: 30}.get(r)
            entity.handle_modbus_update(event)

        assert entity._attr_available is False

    @pytest.mark.asyncio
    async def test_entity_handle_modbus_update_invalid_minute(self):
        """Test entity becomes unavailable with invalid minute."""
        hass = MagicMock()
        controller = create_mock_controller()

        entity_def = {"name": "Test", "register": 13003, "enabled": True}
        entity = SungrowTimeEntity(hass, controller, entity_def)
        entity.schedule_update_ha_state = MagicMock()

        event = MagicMock()
        event.data = {REGISTER: 13003, VALUE: 14, CONTROLLER: "10.0.0.1", SLAVE: 1}

        with patch("custom_components.sungrow_modbus.time.cache_get") as mock_cache:
            mock_cache.side_effect = lambda h, r, k: {13003: 14, 13004: 70}.get(r)  # 70 is invalid minute
            entity.handle_modbus_update(event)

        assert entity._attr_available is False

    @pytest.mark.asyncio
    async def test_entity_handle_modbus_update_missing_minute(self):
        """Test entity becomes unavailable when minute not in cache."""
        hass = MagicMock()
        controller = create_mock_controller()

        entity_def = {"name": "Test", "register": 13003, "enabled": True}
        entity = SungrowTimeEntity(hass, controller, entity_def)
        entity.schedule_update_ha_state = MagicMock()

        event = MagicMock()
        event.data = {REGISTER: 13003, VALUE: 14, CONTROLLER: "10.0.0.1", SLAVE: 1}

        with patch("custom_components.sungrow_modbus.time.cache_get") as mock_cache:
            mock_cache.side_effect = lambda h, r, k: {13003: 14}.get(r)  # minute not in cache
            entity.handle_modbus_update(event)

        assert entity._attr_available is False

    @pytest.mark.asyncio
    async def test_entity_handle_modbus_update_wrong_controller(self):
        """Test entity ignores updates from wrong controller."""
        hass = MagicMock()
        controller = create_mock_controller(host="10.0.0.1", slave=1)

        entity_def = {"name": "Test", "register": 13003, "enabled": True}
        entity = SungrowTimeEntity(hass, controller, entity_def)
        entity._attr_native_value = time(hour=10, minute=0)  # Existing value

        event = MagicMock()
        event.data = {
            REGISTER: 13003,
            VALUE: 14,
            CONTROLLER: "10.0.0.2",  # Different host
            SLAVE: 1,
        }

        entity.handle_modbus_update(event)

        # Value should remain unchanged
        assert entity._attr_native_value == time(hour=10, minute=0)

    @pytest.mark.asyncio
    async def test_entity_handle_modbus_update_wrong_register(self):
        """Test entity ignores updates for unrelated registers."""
        hass = MagicMock()
        controller = create_mock_controller()

        entity_def = {"name": "Test", "register": 13003, "enabled": True}
        entity = SungrowTimeEntity(hass, controller, entity_def)
        entity._attr_native_value = time(hour=10, minute=0)

        event = MagicMock()
        event.data = {
            REGISTER: 13999,  # Different register
            VALUE: 14,
            CONTROLLER: "10.0.0.1",
            SLAVE: 1,
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

        entity_def = {"name": "Test", "register": 13003, "enabled": True}
        entity = SungrowTimeEntity(hass, controller, entity_def)

        with patch.object(entity, "async_get_last_state", new_callable=AsyncMock) as mock_restore:
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

        entity_def = {"name": "Test", "register": 13003, "enabled": True}
        entity = SungrowTimeEntity(hass, controller, entity_def)

        with patch.object(entity, "async_get_last_state", new_callable=AsyncMock) as mock_restore:
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

        entity_def = {"name": "Test", "register": 13003, "enabled": True}
        entity = SungrowTimeEntity(hass, controller, entity_def)

        # RestoreEntity uses async_get_last_state which returns a State object
        mock_state = MagicMock()
        mock_state.state = "08:30:00"  # Time is stored as string in State

        with patch.object(entity, "async_get_last_state", new_callable=AsyncMock) as mock_restore:
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

        entity_def = {"name": "Test", "register": 13003, "enabled": True}
        entity = SungrowTimeEntity(hass, controller, entity_def)
        entity.async_write_ha_state = MagicMock()

        await entity.async_set_value(time(hour=0, minute=0))

        controller.async_write_holding_registers.assert_called_once_with(13003, [0, 0])

    @pytest.mark.asyncio
    async def test_end_of_day_time(self):
        """Test setting end of day (23:59)."""
        hass = MagicMock()
        controller = create_mock_controller()

        entity_def = {"name": "Test", "register": 13003, "enabled": True}
        entity = SungrowTimeEntity(hass, controller, entity_def)
        entity.async_write_ha_state = MagicMock()

        await entity.async_set_value(time(hour=23, minute=59))

        controller.async_write_holding_registers.assert_called_once_with(13003, [23, 59])
