"""Battery Controller for Sungrow multi-battery support.

Sungrow batteries communicate via separate Modbus slave addresses:
- Slave ID 200: Battery Stack 1
- Slave ID 201: Battery Stack 2
- Slave ID 202: Battery Stack 3
- Slave ID 203: Battery Stack 4

These registers are only accessible via the direct LAN port, not through WiNet-S.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

from .const import BATTERY_SLAVE_BASE, DOMAIN, MANUFACTURER, MAX_BATTERY_STACKS
from .modbus_controller import ModbusController

_LOGGER = logging.getLogger(__name__)


@dataclass
class BatteryModule:
    """Represents a single battery module within a stack."""

    index: int
    serial_number: str = ""
    cell_voltage_max: float = 0.0
    cell_voltage_min: float = 0.0
    temperature: float = 0.0


@dataclass
class BatteryStack:
    """Represents a battery stack connected to the inverter."""

    stack_index: int  # 0-3
    slave_id: int  # 200-203
    serial_number: str = ""
    firmware_version: str = ""
    voltage: float = 0.0
    current: float = 0.0
    temperature: float = 0.0
    soc: float = 0.0  # State of Charge (0.1% resolution)
    soh: float = 0.0  # State of Health
    total_charge_energy: float = 0.0
    total_discharge_energy: float = 0.0
    cell_voltage_max: float = 0.0
    cell_voltage_max_position: int = 0
    cell_voltage_min: float = 0.0
    cell_voltage_min_position: int = 0
    modules: list[BatteryModule] = field(default_factory=list)
    available: bool = False


class BatteryController:
    """Controller for managing battery stack communication.

    This controller uses the inverter's Modbus connection but with different
    slave IDs (200-203) to communicate directly with battery stacks.
    """

    # Battery register addresses (input registers on slave ID 200+)
    REGISTERS = {
        "serial_number": {"address": 10710, "count": 10, "type": "string"},
        "firmware_version": {"address": 10720, "count": 10, "type": "string"},
        "voltage": {"address": 10740, "count": 1, "type": "uint16", "scale": 0.1},
        "current": {"address": 10741, "count": 1, "type": "int16", "scale": 0.1},
        "temperature": {"address": 10742, "count": 1, "type": "uint16", "scale": 0.1},
        "soc": {"address": 10743, "count": 1, "type": "uint16", "scale": 0.1},
        "soh": {"address": 10744, "count": 1, "type": "uint16", "scale": 1},
        "total_charge": {"address": 10745, "count": 2, "type": "uint32", "scale": 0.1},
        "total_discharge": {"address": 10747, "count": 2, "type": "uint32", "scale": 0.1},
        "cell_voltage_max": {"address": 10756, "count": 1, "type": "uint16", "scale": 0.0001},
        "cell_voltage_max_pos": {"address": 10757, "count": 1, "type": "uint16", "scale": 1},
        "cell_voltage_min": {"address": 10758, "count": 1, "type": "uint16", "scale": 0.0001},
        "cell_voltage_min_pos": {"address": 10759, "count": 1, "type": "uint16", "scale": 1},
    }

    # Module serial number registers (9 registers per module, up to 8 modules)
    MODULE_SERIAL_BASE = 10821
    MODULE_SERIAL_COUNT = 9
    MAX_MODULES = 8

    def __init__(
        self,
        hass: HomeAssistant,
        inverter_controller: ModbusController,
        stack_index: int = 0,
    ):
        """Initialize the battery controller.

        Args:
            hass: Home Assistant instance
            inverter_controller: Parent inverter's Modbus controller
            stack_index: Battery stack index (0-3)
        """
        self.hass = hass
        self.inverter = inverter_controller
        self.stack_index = stack_index
        self.slave_id = BATTERY_SLAVE_BASE + stack_index
        self.battery = BatteryStack(stack_index=stack_index, slave_id=self.slave_id)
        self._available = False

    @property
    def connection_id(self) -> str:
        """Get connection identifier for this battery stack."""
        return f"{self.inverter.connection_id}_battery_{self.stack_index}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for this battery stack."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.inverter.serial_number}_battery_{self.stack_index}")},
            name=f"Sungrow Battery Stack {self.stack_index + 1}",
            manufacturer=MANUFACTURER,
            model="SBR Battery",
            sw_version=self.battery.firmware_version or "Unknown",
            serial_number=self.battery.serial_number or None,
            via_device=(DOMAIN, self.inverter.serial_number),
        )

    async def probe(self) -> bool:
        """Check if this battery stack is present.

        Attempts to read the battery serial number register.
        Returns True if the battery responds, False otherwise.
        """
        try:
            result = await self._read_registers(
                address=self.REGISTERS["voltage"]["address"],
                count=1,
            )
            if result is not None and len(result) > 0:
                self._available = True
                self.battery.available = True
                _LOGGER.info("Battery stack %d detected on slave ID %d", self.stack_index, self.slave_id)
                return True
        except Exception as e:
            _LOGGER.debug("Battery stack %d not found on slave ID %d: %s", self.stack_index, self.slave_id, e)

        self._available = False
        self.battery.available = False
        return False

    async def _read_registers(
        self,
        address: int,
        count: int,
    ) -> list[int] | None:
        """Read input registers from the battery stack.

        Uses the inverter's Modbus client but with this battery's slave ID.
        """
        async with self.inverter.poll_lock:
            if not self.inverter.client.connected:
                try:
                    await self.inverter.client.connect()
                except Exception as e:
                    _LOGGER.error("Failed to connect for battery read: %s", e)
                    return None

            try:
                result = await self.inverter.client.read_input_registers(
                    address=address,
                    count=count,
                    device_id=self.slave_id,
                )
                if result.isError():
                    _LOGGER.debug("Error reading battery registers %d-%d: %s", address, address + count, result)
                    return None
                return list(result.registers)
            except Exception as e:
                _LOGGER.error("Exception reading battery registers %d-%d: %s", address, address + count, e)
                return None

    async def read_status(self) -> dict[str, Any]:
        """Read all battery status registers.

        Returns a dictionary with battery data or empty dict on failure.
        """
        if not self._available:
            return {}

        data = {}

        # Read main status block (10740-10759)
        result = await self._read_registers(10740, 20)
        if result and len(result) >= 18:
            data["voltage"] = result[0] * 0.1
            data["current"] = self._to_signed(result[1]) * 0.1
            data["temperature"] = result[2] * 0.1
            data["soc"] = result[3] * 0.1
            data["soh"] = result[4]
            data["total_charge"] = (result[5] << 16 | result[6]) * 0.1
            data["total_discharge"] = (result[7] << 16 | result[8]) * 0.1
            # Skip reserved registers 10749-10755
            if len(result) >= 20:
                data["cell_voltage_max"] = result[16] * 0.0001
                data["cell_voltage_max_position"] = result[17]
                data["cell_voltage_min"] = result[18] * 0.0001
                data["cell_voltage_min_position"] = result[19]

            # Update battery stack data
            self.battery.voltage = data.get("voltage", 0)
            self.battery.current = data.get("current", 0)
            self.battery.temperature = data.get("temperature", 0)
            self.battery.soc = data.get("soc", 0)
            self.battery.soh = data.get("soh", 0)
            self.battery.total_charge_energy = data.get("total_charge", 0)
            self.battery.total_discharge_energy = data.get("total_discharge", 0)
            self.battery.cell_voltage_max = data.get("cell_voltage_max", 0)
            self.battery.cell_voltage_min = data.get("cell_voltage_min", 0)

        return data

    async def read_serial_and_firmware(self) -> bool:
        """Read battery serial number and firmware version.

        These are typically read once at startup.
        """
        # Read serial number (10710-10719)
        result = await self._read_registers(10710, 10)
        if result:
            self.battery.serial_number = self._decode_string(result)

        # Read firmware version (10720-10729)
        result = await self._read_registers(10720, 10)
        if result:
            self.battery.firmware_version = self._decode_string(result)

        return bool(self.battery.serial_number)

    async def read_module_serials(self) -> list[str]:
        """Read serial numbers of all battery modules.

        Returns list of serial numbers for detected modules.
        """
        serials = []
        for module_idx in range(self.MAX_MODULES):
            address = self.MODULE_SERIAL_BASE + (module_idx * self.MODULE_SERIAL_COUNT)
            result = await self._read_registers(address, self.MODULE_SERIAL_COUNT)
            if result:
                serial = self._decode_string(result)
                if serial and serial.strip():
                    serials.append(serial)
                    if module_idx >= len(self.battery.modules):
                        self.battery.modules.append(BatteryModule(index=module_idx, serial_number=serial))
                    else:
                        self.battery.modules[module_idx].serial_number = serial
                else:
                    # Empty serial means no more modules
                    break
        return serials

    @staticmethod
    def _decode_string(registers: list[int]) -> str:
        """Decode a UTF-8 string from register values."""
        try:
            bytes_data = b""
            for reg in registers:
                bytes_data += reg.to_bytes(2, byteorder="big")
            return bytes_data.decode("utf-8", errors="ignore").rstrip("\x00").strip()
        except Exception:
            return ""

    @staticmethod
    def _to_signed(value: int, bits: int = 16) -> int:
        """Convert unsigned int to signed."""
        if value >= (1 << (bits - 1)):
            value -= 1 << bits
        return value


async def detect_battery_stacks(
    hass: HomeAssistant,
    inverter_controller: ModbusController,
) -> list[BatteryController]:
    """Detect all connected battery stacks.

    Probes slave IDs 200-203 to find connected batteries.
    Returns list of BatteryController instances for detected stacks.
    """
    detected = []

    for stack_idx in range(MAX_BATTERY_STACKS):
        controller = BatteryController(
            hass=hass,
            inverter_controller=inverter_controller,
            stack_index=stack_idx,
        )

        if await controller.probe():
            # Read initial info
            await controller.read_serial_and_firmware()
            await controller.read_module_serials()
            detected.append(controller)
            _LOGGER.info(
                "Detected battery stack %d: SN=%s, FW=%s, Modules=%d",
                stack_idx,
                controller.battery.serial_number,
                controller.battery.firmware_version,
                len(controller.battery.modules),
            )
        else:
            # Stop probing after first failure (stacks must be sequential)
            break

    return detected
