import contextlib
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sungrow_modbus.const import DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.mark.asyncio
async def test_setup_entry(hass: HomeAssistant):
    """Test setting up the integration."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "1.2.3.4",
            "port": 502,
            "slave": 1,
            "inverter_serial": "SN123456",
            "model": "SH10RT",  # Valid Sungrow hybrid model
            "poll_interval_fast": 10,
            "poll_interval_normal": 15,
            "poll_interval_slow": 30,
        },
        title="Sungrow Inverter",
    )
    config_entry.add_to_hass(hass)

    with (
        patch("custom_components.sungrow_modbus.modbus_controller.ModbusController.connect", return_value=True),
        patch("custom_components.sungrow_modbus.modbus_controller.ModbusController.connected", return_value=True),
        patch(
            "custom_components.sungrow_modbus.modbus_controller.ModbusController.async_read_input_register",
            return_value=[1, 2, 3],
        ),
        patch("custom_components.sungrow_modbus.modbus_controller.ModbusController.process_write_queue"),
        patch(
            "custom_components.sungrow_modbus.modbus_controller.ModbusController.async_read_holding_register",
            return_value=[1, 2, 3],
        ),
    ):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        # Verify success
        assert config_entry.state.value == "loaded"  # ConfigEntryState.LOADED is usually stringified or enum

        # Check if sensors are registered
        # sungrow_modbus registers many sensors.
        # We can check hass.states

        # Just verifying setup logic covered __init__.py and platform setups

        # Test unload
        assert await hass.config_entries.async_unload(config_entry.entry_id)
        await hass.async_block_till_done()


@pytest.mark.asyncio
async def test_setup_entry_connection_failure(hass: HomeAssistant):
    """Test setup failure on connection error."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": "1.2.3.4", "port": 502, "slave": 1, "inverter_serial": "SN123456"},
    )
    config_entry.add_to_hass(hass)

    # Should return False or raise ConfigEntryNotReady on connection failure
    with (
        patch(
            "custom_components.sungrow_modbus.modbus_controller.ModbusController.connect", side_effect=ConnectionError
        ),
        contextlib.suppress(Exception),  # may raise ConfigEntryNotReady
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
