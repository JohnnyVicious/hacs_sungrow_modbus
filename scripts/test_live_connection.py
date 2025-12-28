#!/usr/bin/env python3
"""
Standalone script to test live Modbus connection to Sungrow inverter.

This script performs READ-ONLY operations to validate register addresses.

Usage:
    python scripts/test_live_connection.py
    python scripts/test_live_connection.py --ip 192.168.1.100
    python scripts/test_live_connection.py --scan  # Scan all defined registers

Configuration:
    Set SUNGROW_IP environment variable or create a .env file:
        SUNGROW_IP=192.168.1.100
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load .env file if present
try:
    from dotenv import load_dotenv

    load_dotenv(project_root / ".env")
except ImportError:
    pass  # python-dotenv not installed, rely on environment variables

from pymodbus.client import AsyncModbusTcpClient  # noqa: E402


async def test_connection(ip: str, port: int, slave_id: int):
    """Test basic connectivity."""
    print(f"\n{'=' * 60}")
    print(f"Testing connection to {ip}:{port} (slave {slave_id})")
    print(f"{'=' * 60}")

    client = AsyncModbusTcpClient(host=ip, port=port, timeout=10)

    try:
        connected = await client.connect()
        if not connected:
            print(f"FAILED: Could not connect to {ip}:{port}")
            return None
        print("SUCCESS: Connected to inverter")
        return client
    except Exception as e:
        print(f"ERROR: {e}")
        return None


RUNNING_STATE_MAPPING = {
    0x0000: "Stop",
    0x0002: "Checking",
    0x0004: "Normal",
    0x0008: "Fault",
    0x0010: "Upgrades",
    0x000A: "Self-charging",
    0x000C: "De-rating Running",
    0x0014: "Dispatch Running",
    0x8000: "Standby",
    0x1300: "Initial Standby",
    0x1400: "Shutdown",
    0x1200: "Emergency Stop",
    0x1500: "Alarm Running",
    0x9100: "Dispatch Run",
}


async def read_device_info(client: AsyncModbusTcpClient, slave_id: int):
    """Read device identification registers."""
    print(f"\n{'=' * 60}")
    print("Device Information")
    print(f"{'=' * 60}")

    # Serial Number (registers 4989-4998, 10 registers = 20 chars)
    result = await client.read_input_registers(address=4989, count=10, device_id=slave_id)
    if not result.isError():
        serial = ""
        for reg in result.registers:
            high = (reg >> 8) & 0xFF
            low = reg & 0xFF
            if high > 0:
                serial += chr(high)
            if low > 0:
                serial += chr(low)
        print(f"  Serial Number:    {serial.strip()}")
    else:
        print(f"  Serial Number:    ERROR - {result}")

    # Device Type Code (register 4999)
    result = await client.read_input_registers(address=4999, count=1, device_id=slave_id)
    if not result.isError():
        device_type = result.registers[0]
        print(f"  Device Type:      {device_type} (0x{device_type:04X})")
    else:
        print(f"  Device Type:      ERROR - {result}")

    # Nominal Power (register 5000), unit: 0.1kW
    result = await client.read_input_registers(address=5000, count=1, device_id=slave_id)
    if not result.isError():
        power_kw = result.registers[0] * 0.1
        print(f"  Nominal Power:    {power_kw} kW")
    else:
        print(f"  Nominal Power:    ERROR - {result}")

    # Running State (register 13000 for hybrid inverters)
    result = await client.read_input_registers(address=13000, count=1, device_id=slave_id)
    if not result.isError():
        state_code = result.registers[0]
        state_name = RUNNING_STATE_MAPPING.get(state_code, f"Unknown (0x{state_code:04X})")
        print(f"  Running State:    {state_name}")
    else:
        print("  Running State:    Not available")


async def read_pv_data(client: AsyncModbusTcpClient, slave_id: int):
    """Read PV/solar data."""
    print(f"\n{'=' * 60}")
    print("PV/Solar Data")
    print(f"{'=' * 60}")

    # Daily PV Generation - try register 13001 first (hybrid inverters), fallback to 5002
    result = await client.read_input_registers(address=13001, count=1, device_id=slave_id)
    if not result.isError():
        daily_kwh = result.registers[0] * 0.1
        print(f"  Daily Generation: {daily_kwh} kWh (reg 13001)")
    else:
        # Fallback to register 5002 for string inverters
        result = await client.read_input_registers(address=5002, count=1, device_id=slave_id)
        if not result.isError():
            daily_kwh = result.registers[0] * 0.1
            print(f"  Daily Generation: {daily_kwh} kWh (reg 5002)")
        else:
            print(f"  Daily Generation: ERROR - {result}")

    # Total PV Generation - try 13002 first (hybrid single reg), then U32 variants
    result = await client.read_input_registers(address=13002, count=1, device_id=slave_id)
    if not result.isError():
        total_kwh = result.registers[0] * 0.1
        print(f"  Total Generation: {total_kwh} kWh (reg 13002)")
    else:
        result = await client.read_input_registers(address=5003, count=2, device_id=slave_id)
        if not result.isError():
            total = (result.registers[0] << 16) | result.registers[1]
            total_kwh = total * 0.1
            print(f"  Total Generation: {total_kwh} kWh (reg 5003-5004)")
        else:
            print(f"  Total Generation: ERROR - {result}")

    # MPPT1 Voltage & Current (registers 5010-5011)
    result = await client.read_input_registers(address=5010, count=2, device_id=slave_id)
    if not result.isError():
        voltage = result.registers[0] * 0.1
        current = result.registers[1] * 0.1
        power = voltage * current
        print(f"  MPPT1:            {voltage}V, {current}A ({power:.1f}W)")
    else:
        print(f"  MPPT1:            ERROR - {result}")

    # MPPT2 Voltage & Current (registers 5012-5013)
    result = await client.read_input_registers(address=5012, count=2, device_id=slave_id)
    if not result.isError():
        voltage = result.registers[0] * 0.1
        current = result.registers[1] * 0.1
        power = voltage * current
        print(f"  MPPT2:            {voltage}V, {current}A ({power:.1f}W)")
    else:
        print(f"  MPPT2:            ERROR - {result}")


async def read_grid_data(client: AsyncModbusTcpClient, slave_id: int):
    """Read grid/AC data."""
    print(f"\n{'=' * 60}")
    print("Grid/AC Data")
    print(f"{'=' * 60}")

    # Grid Frequency (register 5035), unit: 0.1Hz
    result = await client.read_input_registers(address=5035, count=1, device_id=slave_id)
    if not result.isError():
        freq = result.registers[0] / 10
        print(f"  Grid Frequency:   {freq:.1f} Hz")
    else:
        print(f"  Grid Frequency:   ERROR - {result}")

    # Internal Temperature (register 5007), unit: 0.1C, signed
    result = await client.read_input_registers(address=5007, count=1, device_id=slave_id)
    if not result.isError():
        temp_raw = result.registers[0]
        if temp_raw > 32767:
            temp_raw -= 65536
        temp = temp_raw * 0.1
        print(f"  Temperature:      {temp} C")
    else:
        print(f"  Temperature:      ERROR - {result}")

    # Total Active Power (register 5030), unit: 1W, signed
    result = await client.read_input_registers(address=5030, count=2, device_id=slave_id)
    if not result.isError():
        power_raw = (result.registers[0] << 16) | result.registers[1]
        if power_raw > 0x7FFFFFFF:
            power_raw -= 0x100000000
        print(f"  Total Power:      {power_raw} W")
    else:
        print(f"  Total Power:      ERROR - {result}")


async def read_battery_data(client: AsyncModbusTcpClient, slave_id: int):
    """Read battery data."""
    print(f"\n{'=' * 60}")
    print("Battery Data")
    print(f"{'=' * 60}")

    # Battery Voltage (register 5082), unit: 0.1V
    result = await client.read_input_registers(address=5082, count=1, device_id=slave_id)
    if not result.isError():
        voltage = result.registers[0] * 0.1
        print(f"  Battery Voltage:  {voltage} V")
    else:
        print("  Battery Voltage:  Not available")

    # Battery Current (register 5083), unit: 0.1A, signed
    result = await client.read_input_registers(address=5083, count=1, device_id=slave_id)
    if not result.isError():
        current_raw = result.registers[0]
        if current_raw > 32767:
            current_raw -= 65536
        current = current_raw * 0.1
        print(f"  Battery Current:  {current} A")
    else:
        print("  Battery Current:  Not available")

    # Battery Power (register 5084), unit: 1W, signed
    result = await client.read_input_registers(address=5084, count=2, device_id=slave_id)
    if not result.isError():
        power_raw = (result.registers[0] << 16) | result.registers[1]
        if power_raw > 0x7FFFFFFF:
            power_raw -= 0x100000000
        print(f"  Battery Power:    {power_raw} W")
    else:
        print("  Battery Power:    Not available")

    # Battery SOC (register 13022), unit: 0.1%
    result = await client.read_input_registers(address=13022, count=1, device_id=slave_id)
    if not result.isError():
        soc = result.registers[0] / 10
        print(f"  Battery SOC:      {soc:.1f}%")
    else:
        print("  Battery SOC:      Not available")

    # Battery SOH (register 13023), unit: 0.1%
    result = await client.read_input_registers(address=13023, count=1, device_id=slave_id)
    if not result.isError():
        soh = result.registers[0] / 10
        print(f"  Battery SOH:      {soh:.1f}%")
    else:
        print("  Battery SOH:      Not available")


async def read_ems_settings(client: AsyncModbusTcpClient, slave_id: int):
    """Read EMS/configuration settings (holding registers)."""
    print(f"\n{'=' * 60}")
    print("EMS Settings (Holding Registers - READ ONLY)")
    print(f"{'=' * 60}")

    # EMS Mode (register 13049)
    result = await client.read_holding_registers(address=13049, count=1, device_id=slave_id)
    if not result.isError():
        mode = result.registers[0]
        mode_names = {0: "Self-consumption", 1: "Forced mode", 2: "Backup", 3: "Feed-in priority"}
        print(f"  EMS Mode:         {mode_names.get(mode, f'Unknown ({mode})')}")
    else:
        print("  EMS Mode:         Not available")

    # Max SOC (register 13057), unit: 0.1%
    result = await client.read_holding_registers(address=13057, count=1, device_id=slave_id)
    if not result.isError():
        max_soc = result.registers[0] * 0.1
        print(f"  Max SOC:          {max_soc}%")
    else:
        print("  Max SOC:          Not available")

    # Min SOC (register 13058), unit: 0.1%
    result = await client.read_holding_registers(address=13058, count=1, device_id=slave_id)
    if not result.isError():
        min_soc = result.registers[0] * 0.1
        print(f"  Min SOC:          {min_soc}%")
    else:
        print("  Min SOC:          Not available")


async def scan_register_range(
    client: AsyncModbusTcpClient, slave_id: int, start: int, end: int, reg_type: str = "input"
):
    """Scan a range of registers and print values."""
    print(f"\n{'=' * 60}")
    print(f"Scanning {reg_type} registers {start}-{end}")
    print(f"{'=' * 60}")

    for addr in range(start, end + 1):
        try:
            if reg_type == "input":
                result = await client.read_input_registers(address=addr, count=1, device_id=slave_id)
            else:
                result = await client.read_holding_registers(address=addr, count=1, device_id=slave_id)

            if not result.isError():
                val = result.registers[0]
                # Also show signed interpretation
                signed = val if val <= 32767 else val - 65536
                print(f"  {addr}: {val} (0x{val:04X}, signed: {signed})")
            else:
                print(f"  {addr}: Error - {result}")
        except Exception as e:
            print(f"  {addr}: Exception - {e}")


async def main():
    # Get default IP from environment variable
    default_ip = os.environ.get("SUNGROW_IP") or None

    parser = argparse.ArgumentParser(
        description="Test Sungrow inverter Modbus connection",
        epilog="Set SUNGROW_IP environment variable or use --ip flag",
    )
    parser.add_argument(
        "--ip", default=default_ip, required=default_ip is None, help="Inverter IP address (or set SUNGROW_IP env var)"
    )
    parser.add_argument("--port", type=int, default=502, help="Modbus port")
    parser.add_argument("--slave", type=int, default=1, help="Modbus slave ID")
    parser.add_argument("--scan", action="store_true", help="Scan register ranges")
    parser.add_argument("--scan-start", type=int, default=4989, help="Scan start register")
    parser.add_argument("--scan-end", type=int, default=5050, help="Scan end register")
    parser.add_argument("--scan-type", choices=["input", "holding"], default="input", help="Register type to scan")
    args = parser.parse_args()

    client = await test_connection(args.ip, args.port, args.slave)
    if not client:
        return 1

    try:
        if args.scan:
            await scan_register_range(client, args.slave, args.scan_start, args.scan_end, args.scan_type)
        else:
            await read_device_info(client, args.slave)
            await read_pv_data(client, args.slave)
            await read_grid_data(client, args.slave)
            await read_battery_data(client, args.slave)
            await read_ems_settings(client, args.slave)

        print(f"\n{'=' * 60}")
        print("TEST COMPLETED SUCCESSFULLY")
        print(f"{'=' * 60}\n")
        return 0

    except Exception as e:
        print(f"\nERROR: {e}")
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
