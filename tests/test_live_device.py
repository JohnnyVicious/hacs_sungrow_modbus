"""
Live device integration tests for Sungrow inverters.

These tests connect to a REAL inverter and perform READ-ONLY operations.
They are skipped by default and must be explicitly enabled.

Usage:
    # Run live tests against default device (192.168.11.6)
    pytest tests/test_live_device.py -v --run-live -p no:socket

    # Run against a different device
    pytest tests/test_live_device.py -v --run-live -p no:socket --inverter-ip=192.168.1.100

    # Run against a different port
    pytest tests/test_live_device.py -v --run-live -p no:socket --inverter-port=1502
"""

import pytest
from pymodbus.client import AsyncModbusTcpClient

# Allow socket connections for this entire module
pytestmark = pytest.mark.enable_socket


@pytest.fixture
def inverter_ip(request):
    return request.config.getoption("--inverter-ip")


@pytest.fixture
def inverter_port(request):
    return request.config.getoption("--inverter-port")


@pytest.fixture
def slave_id(request):
    return request.config.getoption("--slave-id")


@pytest.fixture
def run_live(request):
    return request.config.getoption("--run-live")


@pytest.fixture
async def modbus_client(inverter_ip, inverter_port, run_live):
    """Create and connect a Modbus client for testing."""
    if not run_live:
        pytest.skip("Live tests disabled. Use --run-live to enable.")

    client = AsyncModbusTcpClient(
        host=inverter_ip,
        port=inverter_port,
        timeout=10
    )

    connected = await client.connect()
    if not connected:
        pytest.fail(f"Could not connect to inverter at {inverter_ip}:{inverter_port}")

    yield client

    client.close()


class TestLiveDeviceConnection:
    """Test basic connectivity to the inverter."""

    @pytest.mark.asyncio
    async def test_connection(self, modbus_client, inverter_ip, inverter_port):
        """Verify we can connect to the inverter."""
        assert modbus_client.connected, f"Failed to connect to {inverter_ip}:{inverter_port}"
        print(f"\n  Connected to inverter at {inverter_ip}:{inverter_port}")


class TestLiveDeviceInfo:
    """Read device information registers (Input Registers 4989-5000)."""

    @pytest.mark.asyncio
    async def test_read_serial_number(self, modbus_client, slave_id):
        """Read inverter serial number (registers 4989-4998, 10 registers = 20 chars)."""
        # Sungrow uses 0-based addressing in protocol, register 4989 = address 4988
        result = await modbus_client.read_input_registers(
            address=4989 - 1,  # 0-based
            count=10,
            slave=slave_id
        )

        assert not result.isError(), f"Failed to read serial number: {result}"

        # Convert registers to ASCII string
        serial = ""
        for reg in result.registers:
            high_byte = (reg >> 8) & 0xFF
            low_byte = reg & 0xFF
            if high_byte > 0:
                serial += chr(high_byte)
            if low_byte > 0:
                serial += chr(low_byte)

        print(f"\n  Serial Number: {serial.strip()}")
        assert len(serial.strip()) > 0, "Serial number should not be empty"

    @pytest.mark.asyncio
    async def test_read_device_type_code(self, modbus_client, slave_id):
        """Read device type code (register 4999)."""
        result = await modbus_client.read_input_registers(
            address=4999 - 1,
            count=1,
            slave=slave_id
        )

        assert not result.isError(), f"Failed to read device type: {result}"
        device_type = result.registers[0]
        print(f"\n  Device Type Code: {device_type} (0x{device_type:04X})")

    @pytest.mark.asyncio
    async def test_read_nominal_power(self, modbus_client, slave_id):
        """Read nominal output power (register 5000), unit: 0.1kW."""
        result = await modbus_client.read_input_registers(
            address=5000 - 1,
            count=1,
            slave=slave_id
        )

        assert not result.isError(), f"Failed to read nominal power: {result}"
        nominal_power_raw = result.registers[0]
        nominal_power_kw = nominal_power_raw * 0.1
        print(f"\n  Nominal Power: {nominal_power_kw} kW (raw: {nominal_power_raw})")

        # SH25T should report ~25kW
        assert nominal_power_kw > 0, "Nominal power should be positive"


class TestLivePVData:
    """Read PV/MPPT data (Input Registers 5010-5024)."""

    @pytest.mark.asyncio
    async def test_read_daily_pv_generation(self, modbus_client, slave_id):
        """Read daily PV generation (register 5002), unit: 0.1kWh."""
        result = await modbus_client.read_input_registers(
            address=5002 - 1,
            count=1,
            slave=slave_id
        )

        assert not result.isError(), f"Failed to read daily generation: {result}"
        daily_gen_kwh = result.registers[0] * 0.1
        print(f"\n  Daily PV Generation: {daily_gen_kwh} kWh")

    @pytest.mark.asyncio
    async def test_read_total_pv_generation(self, modbus_client, slave_id):
        """Read total PV generation (registers 5003-5004), unit: 0.1kWh, U32."""
        result = await modbus_client.read_input_registers(
            address=5003 - 1,
            count=2,
            slave=slave_id
        )

        assert not result.isError(), f"Failed to read total generation: {result}"
        # Combine two 16-bit registers into 32-bit value (high word first for Sungrow)
        total_raw = (result.registers[0] << 16) | result.registers[1]
        total_gen_kwh = total_raw * 0.1
        print(f"\n  Total PV Generation: {total_gen_kwh} kWh")

    @pytest.mark.asyncio
    async def test_read_mppt1_voltage_current(self, modbus_client, slave_id):
        """Read MPPT1 voltage (5010) and current (5011)."""
        result = await modbus_client.read_input_registers(
            address=5010 - 1,
            count=2,
            slave=slave_id
        )

        assert not result.isError(), f"Failed to read MPPT1 data: {result}"
        voltage = result.registers[0] * 0.1  # Unit: 0.1V
        current = result.registers[1] * 0.1  # Unit: 0.1A
        power = voltage * current
        print(f"\n  MPPT1: {voltage}V, {current}A, {power:.1f}W")


class TestLiveGridData:
    """Read grid/meter data."""

    @pytest.mark.asyncio
    async def test_read_grid_frequency(self, modbus_client, slave_id):
        """Read grid frequency (register 5035), unit: 0.1Hz."""
        result = await modbus_client.read_input_registers(
            address=5035 - 1,
            count=1,
            slave=slave_id
        )

        assert not result.isError(), f"Failed to read grid frequency: {result}"
        frequency = result.registers[0] * 0.1
        print(f"\n  Grid Frequency: {frequency} Hz")
        # Should be around 50Hz or 60Hz depending on region
        assert 45 < frequency < 65, f"Grid frequency {frequency}Hz seems unreasonable"

    @pytest.mark.asyncio
    async def test_read_internal_temperature(self, modbus_client, slave_id):
        """Read internal temperature (register 5007), unit: 0.1C, signed."""
        result = await modbus_client.read_input_registers(
            address=5007 - 1,
            count=1,
            slave=slave_id
        )

        assert not result.isError(), f"Failed to read temperature: {result}"
        # Handle signed 16-bit value
        temp_raw = result.registers[0]
        if temp_raw > 32767:
            temp_raw -= 65536
        temperature = temp_raw * 0.1
        print(f"\n  Internal Temperature: {temperature} C")
        # Reasonable temperature range
        assert -40 < temperature < 100, f"Temperature {temperature}C seems unreasonable"


class TestLiveBatteryData:
    """Read battery data (for hybrid inverters with battery)."""

    @pytest.mark.asyncio
    async def test_read_battery_voltage(self, modbus_client, slave_id):
        """Read battery voltage (register 5082), unit: 0.1V."""
        result = await modbus_client.read_input_registers(
            address=5082 - 1,
            count=1,
            slave=slave_id
        )

        if result.isError():
            pytest.skip("Battery data not available (may not have battery connected)")

        voltage = result.registers[0] * 0.1
        print(f"\n  Battery Voltage: {voltage} V")

    @pytest.mark.asyncio
    async def test_read_battery_soc(self, modbus_client, slave_id):
        """Read battery state of charge (register 13022), unit: 0.1%."""
        result = await modbus_client.read_input_registers(
            address=13022 - 1,
            count=1,
            slave=slave_id
        )

        if result.isError():
            pytest.skip("Battery SOC not available")

        soc = result.registers[0] * 0.1
        print(f"\n  Battery SOC: {soc}%")
        assert 0 <= soc <= 100, f"SOC {soc}% should be between 0-100"


class TestLiveHoldingRegisters:
    """Read holding registers (configuration data) - still READ-ONLY."""

    @pytest.mark.asyncio
    async def test_read_ems_mode(self, modbus_client, slave_id):
        """Read EMS mode (holding register 13049)."""
        result = await modbus_client.read_holding_registers(
            address=13049 - 1,
            count=1,
            slave=slave_id
        )

        if result.isError():
            pytest.skip(f"EMS mode register not available: {result}")

        ems_mode = result.registers[0]
        mode_names = {
            0: "Self-consumption",
            1: "Forced charge/discharge",
            2: "Backup mode",
            3: "Feed-in priority"
        }
        mode_name = mode_names.get(ems_mode, f"Unknown ({ems_mode})")
        print(f"\n  EMS Mode: {mode_name}")

    @pytest.mark.asyncio
    async def test_read_max_soc(self, modbus_client, slave_id):
        """Read max SOC setting (holding register 13057), unit: 0.1%."""
        result = await modbus_client.read_holding_registers(
            address=13057 - 1,
            count=1,
            slave=slave_id
        )

        if result.isError():
            pytest.skip(f"Max SOC register not available: {result}")

        max_soc = result.registers[0] * 0.1
        print(f"\n  Max SOC Setting: {max_soc}%")


class TestLiveRegisterScan:
    """Scan register ranges to discover available data."""

    @pytest.mark.asyncio
    async def test_scan_device_info_range(self, modbus_client, slave_id):
        """Scan device info registers 4989-5008."""
        print("\n  Device Info Registers (4989-5008):")

        for addr in range(4989, 5009):
            try:
                result = await modbus_client.read_input_registers(
                    address=addr - 1,
                    count=1,
                    slave=slave_id
                )
                if not result.isError():
                    val = result.registers[0]
                    print(f"    {addr}: {val} (0x{val:04X})")
            except Exception as e:
                print(f"    {addr}: Error - {e}")

    @pytest.mark.asyncio
    async def test_scan_running_state_range(self, modbus_client, slave_id):
        """Scan running state registers 13000-13010."""
        print("\n  Running State Registers (13000-13010):")

        for addr in range(13000, 13011):
            try:
                result = await modbus_client.read_input_registers(
                    address=addr - 1,
                    count=1,
                    slave=slave_id
                )
                if not result.isError():
                    val = result.registers[0]
                    print(f"    {addr}: {val} (0x{val:04X})")
            except Exception as e:
                print(f"    {addr}: Error - {e}")
