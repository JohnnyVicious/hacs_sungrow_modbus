from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sungrow_modbus.const import CONN_TYPE_TCP, DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


def mock_pymodbus_client(serial_number="A2432904560", device_type_code=0x0E06, nominal_power=100):
    """Create a mock pymodbus client that returns device info."""
    mock_client = AsyncMock()
    mock_client.connect = AsyncMock(return_value=True)
    mock_client.close = MagicMock()

    # Mock read_input_registers to return different values based on address
    async def mock_read_input_registers(address, count, device_id=1):
        result = MagicMock()
        result.isError = MagicMock(return_value=False)

        if address == 4989:  # Serial number (10 registers)
            # Convert serial to register values (2 chars per register, big-endian)
            registers = []
            padded_serial = serial_number.ljust(20, "\x00")
            for i in range(0, 20, 2):
                high = ord(padded_serial[i])
                low = ord(padded_serial[i + 1]) if i + 1 < len(padded_serial) else 0
                registers.append((high << 8) | low)
            result.registers = registers
        elif address == 4999:  # Device type code
            result.registers = [device_type_code]
        elif address == 5000:  # Nominal power
            result.registers = [nominal_power]
        else:
            result.registers = [0]

        return result

    mock_client.read_input_registers = mock_read_input_registers
    return mock_client


@pytest.mark.asyncio
async def test_flow_user_success(hass: HomeAssistant):
    """Test user initialized flow with success - auto-detects serial and model."""
    mock_client = mock_pymodbus_client(
        serial_number="A2432904560",
        device_type_code=0x0E06,  # SH10RT
        nominal_power=100,  # 10kW
    )

    with (
        patch(
            "pymodbus.client.AsyncModbusTcpClient",
            return_value=mock_client,
        ),
        patch(
            "custom_components.sungrow_modbus.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        # Step 1: Select connection type
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "user"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"connection_type": CONN_TYPE_TCP}
        )

        # Step 2: Enter connection details (minimal: host, port, slave)
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "connection"

        config_input = {
            "host": "192.168.1.100",
            "port": 502,
            "slave": 1,
        }

        result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input=config_input)

        # Should create entry with auto-detected serial and model
        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert "A2432904560" in result["title"]
        assert "SH10RT" in result["title"]

        # Verify data includes auto-detected values
        assert result["data"]["inverter_serial"] == "A2432904560"
        assert result["data"]["model"] == "SH10RT"
        assert result["data"]["host"] == "192.168.1.100"
        assert result["data"]["port"] == 502
        assert result["data"]["connection_type"] == CONN_TYPE_TCP

        mock_setup_entry.assert_called_once()


@pytest.mark.asyncio
async def test_flow_user_connection_error(hass: HomeAssistant):
    """Test user initialized flow with connection error."""
    mock_client = AsyncMock()
    mock_client.connect = AsyncMock(return_value=False)

    with patch(
        "pymodbus.client.AsyncModbusTcpClient",
        return_value=mock_client,
    ):
        # Step 1: Select connection type
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"connection_type": CONN_TYPE_TCP}
        )

        # Step 2: Enter connection details (bad connection)
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "connection"

        config_input = {
            "host": "192.168.1.100",
            "port": 502,
            "slave": 1,
        }

        result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input=config_input)

        # Should show error and stay on form
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["errors"] == {"base": "cannot_connect"}


@pytest.mark.asyncio
async def test_flow_user_duplicate_serial(hass: HomeAssistant):
    """Test user initialized flow with duplicate serial number."""
    # Add existing entry with same serial
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="A2432904560",  # Same serial as will be detected
        data={"host": "192.168.1.50", "slave": 1, "connection_type": CONN_TYPE_TCP, "inverter_serial": "A2432904560"},
    )
    entry.add_to_hass(hass)

    mock_client = mock_pymodbus_client(serial_number="A2432904560")

    with patch(
        "pymodbus.client.AsyncModbusTcpClient",
        return_value=mock_client,
    ):
        # Step 1: Select connection type
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"connection_type": CONN_TYPE_TCP}
        )

        # Step 2: Enter connection details (different IP but same inverter serial)
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "connection"

        config_input = {
            "host": "192.168.1.100",  # Different IP
            "port": 502,
            "slave": 1,
        }

        result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input=config_input)

        # Should abort because same serial number is already configured
        assert result["type"] == data_entry_flow.FlowResultType.ABORT
        assert result["reason"] == "already_configured"


@pytest.mark.asyncio
async def test_flow_unknown_model_uses_default(hass: HomeAssistant):
    """Test that unknown device type code falls back to default model."""
    mock_client = mock_pymodbus_client(
        serial_number="B1234567890",
        device_type_code=0xFFFF,  # Unknown device type
        nominal_power=50,
    )

    with (
        patch(
            "pymodbus.client.AsyncModbusTcpClient",
            return_value=mock_client,
        ),
        patch(
            "custom_components.sungrow_modbus.async_setup_entry",
            return_value=True,
        ),
    ):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"connection_type": CONN_TYPE_TCP}
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"host": "192.168.1.100", "port": 502, "slave": 1}
        )

        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        # For unknown device types, falls back to first inverter in SUNGROW_INVERTERS
        # Check title contains Unknown (which includes hex code) and model is the fallback
        assert "Unknown" in result["title"]
        assert result["data"]["model"] == "SG2.0RS-S"  # First inverter in list as fallback
