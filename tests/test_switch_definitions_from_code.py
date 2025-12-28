from unittest.mock import MagicMock

import pytest

from custom_components.sungrow_modbus.const import CONTROLLER, DOMAIN
from custom_components.sungrow_modbus.data.enums import InverterFeature, InverterType
from custom_components.sungrow_modbus.switch import async_setup_entry


@pytest.mark.asyncio
async def test_switch_bit_position_requires_combinations_are_unique():
    controller = MagicMock()
    controller.host = "10.0.0.1"
    controller.device_id = 1
    controller.slave = 1
    controller.connected.return_value = True
    controller.inverter_config = MagicMock()
    controller.inverter_config.type = InverterType.HYBRID
    controller.inverter_config.features = {InverterFeature.BATTERY}
    controller.model = "SH10RT"
    controller.device_serial_number = "SN123456"
    controller.sw_version = "1.0"

    hass = MagicMock()
    hass.create_task = MagicMock()
    hass.data = {DOMAIN: {CONTROLLER: {"10.0.0.1:502_1": controller}}}

    config_entry = MagicMock()
    config_entry.data = {"host": "10.0.0.1", "port": 502, "slave": 1}
    config_entry.options = {}

    captured_entities = []

    def capture_add_devices(entities, update_immediately):
        captured_entities.extend(entities)

    await async_setup_entry(hass, config_entry, capture_add_devices)

    seen_keys = set()
    for entity in captured_entities:
        register = entity._register
        bit = entity._bit_position
        requires = tuple(sorted(entity._requires)) if entity._requires else ()
        if bit is None:
            continue
        key = (register, bit, requires)
        assert key not in seen_keys, (
            f"Duplicate (register, bit_position, requires): {key} in entity: {entity._attr_name}"
        )
        seen_keys.add(key)


@pytest.mark.asyncio
async def test_hybrid_switch_entities_created():
    """Test that HYBRID inverter creates expected switch entities."""
    controller = MagicMock()
    controller.host = "10.0.0.1"
    controller.device_id = 1
    controller.slave = 1
    controller.connected.return_value = True
    controller.inverter_config = MagicMock()
    controller.inverter_config.type = InverterType.HYBRID
    controller.inverter_config.features = {InverterFeature.BATTERY}
    controller.model = "SH10RT"
    controller.device_serial_number = "SN123456"
    controller.sw_version = "1.0"

    hass = MagicMock()
    hass.create_task = MagicMock()
    hass.data = {DOMAIN: {CONTROLLER: {"10.0.0.1:502_1": controller}}}

    config_entry = MagicMock()
    config_entry.data = {"host": "10.0.0.1", "port": 502, "slave": 1}
    config_entry.options = {}

    captured_entities = []

    def capture_add_devices(entities, update_immediately):
        captured_entities.extend(entities)

    await async_setup_entry(hass, config_entry, capture_add_devices)

    # Check we have the expected switches
    entity_names = [e._attr_name for e in captured_entities]
    assert "Sungrow Modbus Enabled" in entity_names
    assert "Inverter Power" in entity_names
    assert "Backup Mode" in entity_names
    assert "Export Power Limit Mode" in entity_names
    assert "Load Adjustment Switch" in entity_names


@pytest.mark.asyncio
async def test_string_inverter_switch_entities():
    """Test that STRING inverter creates expected switch entities."""
    controller = MagicMock()
    controller.host = "10.0.0.1"
    controller.device_id = 1
    controller.slave = 1
    controller.connected.return_value = True
    controller.inverter_config = MagicMock()
    controller.inverter_config.type = InverterType.STRING
    controller.inverter_config.features = set()
    controller.model = "SG10RT"
    controller.device_serial_number = "SN123456"
    controller.sw_version = "1.0"

    hass = MagicMock()
    hass.create_task = MagicMock()
    hass.data = {DOMAIN: {CONTROLLER: {"10.0.0.1:502_1": controller}}}

    config_entry = MagicMock()
    config_entry.data = {"host": "10.0.0.1", "port": 502, "slave": 1}
    config_entry.options = {}

    captured_entities = []

    def capture_add_devices(entities, update_immediately):
        captured_entities.extend(entities)

    await async_setup_entry(hass, config_entry, capture_add_devices)

    # Check we have the expected switches for string inverter
    entity_names = [e._attr_name for e in captured_entities]
    assert "Sungrow Modbus Enabled" in entity_names
    assert "Power Limitation Switch" in entity_names
    assert "Export Power Limitation" in entity_names
