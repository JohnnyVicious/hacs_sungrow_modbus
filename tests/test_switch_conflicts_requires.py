from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.sungrow_modbus.helpers import set_bit
from custom_components.sungrow_modbus.sensors.sungrow_binary_sensor import (
    SungrowBinaryEntity,
)


@pytest.fixture
def controller():
    mock = MagicMock()
    mock.connected.return_value = True
    mock.host = "inverter.local"
    mock.identification = "test-id"
    mock.model = "S6"
    mock.device_identification = "XYZ"
    mock.sw_version = "1.0"
    mock.async_write_holding_register = AsyncMock(return_value=MagicMock())
    return mock


@pytest.fixture
def mock_hass():
    hass = MagicMock()
    return hass


@pytest.mark.asyncio
async def test_conflicts_self_use_mode(mock_hass, controller):
    entity_def = {
        "register": 43110,
        "bit_position": 0,
        "conflicts_with": (6, 11),
        "name": "Self-Use Mode",
    }

    initial = set_bit(set_bit(0, 6, True), 11, True)

    with patch("custom_components.sungrow_modbus.sensors.sungrow_binary_sensor.cache_get", return_value=initial):
        entity = SungrowBinaryEntity(mock_hass, controller, entity_def)
        entity.async_write_ha_state = MagicMock()
        await entity.async_set_register_bit(True)

        expected = set_bit(set_bit(0, 6, False), 11, False)
        expected = set_bit(expected, 0, True)

        controller.async_write_holding_register.assert_called_once_with(43110, expected)


@pytest.mark.asyncio
async def test_requires_tou(mock_hass, controller):
    entity_def = {
        "register": 43110,
        "bit_position": 1,
        "requires": (0,),
        "name": "TOU (Self-Use)",
    }

    with patch("custom_components.sungrow_modbus.sensors.sungrow_binary_sensor.cache_get", return_value=0):
        entity = SungrowBinaryEntity(mock_hass, controller, entity_def)
        entity.async_write_ha_state = MagicMock()
        await entity.async_set_register_bit(True)

        expected = set_bit(set_bit(0, 0, True), 1, True)
        controller.async_write_holding_register.assert_called_once_with(43110, expected)


@pytest.mark.asyncio
async def test_conflicts_and_requires_combined(mock_hass, controller):
    entity_def = {
        "register": 43110,
        "bit_position": 4,
        "conflicts_with": (0, 6),
        "requires": (1,),
        "name": "Reserve Battery Mode",
    }

    initial = set_bit(set_bit(set_bit(0, 0, True), 6, True), 1, True)

    with patch("custom_components.sungrow_modbus.sensors.sungrow_binary_sensor.cache_get", return_value=initial):
        entity = SungrowBinaryEntity(mock_hass, controller, entity_def)
        entity.async_write_ha_state = MagicMock()
        await entity.async_set_register_bit(True)

        expected = set_bit(set_bit(0, 1, True), 4, True)
        controller.async_write_holding_register.assert_called_once_with(43110, expected)
