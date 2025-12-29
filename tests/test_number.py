from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.sungrow_modbus.sensors.sungrow_base_sensor import SungrowBaseSensor
from custom_components.sungrow_modbus.sensors.sungrow_number_sensor import SungrowNumberEntity


@pytest.fixture
def mock_controller():
    controller = MagicMock()
    controller.async_write_holding_register = AsyncMock()
    return controller


@pytest.fixture
def mock_base_sensor(mock_controller):
    sensor = MagicMock(spec=SungrowBaseSensor)
    sensor.controller = mock_controller
    sensor.name = "Test Number"
    sensor.registrars = [100]
    sensor.write_register = 100
    sensor.device_class = "battery"
    sensor.unit_of_measurement = "%"
    sensor.state_class = "measurement"
    sensor.multiplier = 1
    sensor.min_value = 0
    sensor.max_value = 100
    sensor.step = 1
    sensor.step = 1
    sensor.enabled = True
    sensor.hidden = False
    sensor.unique_id = "test_unique_id"
    sensor.default = 50
    return sensor


@pytest.mark.asyncio
async def test_sungrow_number_entity(hass, mock_base_sensor, mock_controller):
    """Test SungrowNumberEntity initialization and value setting."""

    # SungrowNumberEntity takes (hass, sensor: SungrowBaseSensor)
    print(f"DEBUG: Input Hass={hass}")
    mock_controller.async_write_holding_register = AsyncMock(return_value=MagicMock())
    entity = SungrowNumberEntity(hass, mock_base_sensor)

    # Check attributes
    assert entity.name == "Test Number"
    assert entity.native_min_value == 0
    assert entity.native_max_value == 100
    assert entity.native_step == 1
    assert entity.native_unit_of_measurement == "%"

    # Test setting value (now async)
    entity.async_write_ha_state = MagicMock()
    await entity.async_set_native_value(60)
    mock_controller.async_write_holding_register.assert_called_with(100, 60)


@pytest.mark.asyncio
async def test_sungrow_number_entity_updates(hass, mock_controller):
    # Mock base sensor
    sensor = MagicMock(spec=SungrowBaseSensor)
    sensor.controller = mock_controller
    sensor.name = "Test Number"
    sensor.registrars = [100, 101]
    sensor.write_register = None
    sensor.multiplier = 10
    sensor.convert_value = MagicMock(return_value=50.0)
    sensor.min_value = 0
    sensor.max_value = 100
    sensor.step = 1
    sensor.enabled = True
    sensor.hidden = False
    sensor.unique_id = "test_unique_id"
    sensor.default = 50
    sensor.device_class = "battery"
    sensor.unit_of_measurement = "%"
    sensor.state_class = "measurement"

    mock_controller.async_write_holding_register = AsyncMock(return_value=MagicMock())
    entity = SungrowNumberEntity(hass, sensor)
    assert entity._hass is not None

    # Test async_set_native_value with multi-register (no write_register set)
    entity._write_register = None  # Ensure no write register
    entity.async_write_ha_state = MagicMock()
    await entity.async_set_native_value(55)
    # write_register is None, so no write should occur
    assert not mock_controller.async_write_holding_register.called
