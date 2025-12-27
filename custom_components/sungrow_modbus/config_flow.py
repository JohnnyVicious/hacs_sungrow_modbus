import asyncio
import copy
import logging
import struct

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import OptionsFlowWithConfigEntry

from .const import (
    DOMAIN, CONN_TYPE_TCP, CONN_TYPE_SERIAL, CONF_SERIAL_PORT,
    CONF_BAUDRATE, CONF_BYTESIZE, CONF_PARITY, CONF_STOPBITS,
    CONF_CONNECTION_TYPE, CONF_INVERTER_SERIAL, CONF_MULTI_BATTERY,
    DEFAULT_BAUDRATE, DEFAULT_BYTESIZE, DEFAULT_PARITY, DEFAULT_STOPBITS
)
from .data.sungrow_config import SUNGROW_INVERTERS, CONNECTION_METHOD

_LOGGER = logging.getLogger(__name__)

# Extract model names for dropdown selection
SUNGROW_MODELS = {inverter.model: inverter.model for inverter in SUNGROW_INVERTERS}

# Connection type options
CONNECTION_TYPES = {
    CONN_TYPE_TCP: "TCP (WiFi Dongle)",
    CONN_TYPE_SERIAL: "Serial (RS485)"
}

# Parity options
PARITY_OPTIONS = {
    "N": "None",
    "E": "Even",
    "O": "Odd"
}

# Device type code to model mapping
# Sources: SunGather registers-sungrow.yaml, Sungrow Modbus Protocol documentation
# Organized by inverter family for maintainability
DEVICE_TYPE_MAP = {
    # ==========================================================================
    # RESIDENTIAL HYBRID INVERTERS (SH Series - with battery storage)
    # ==========================================================================

    # --- SH-RS series (single phase residential hybrid) ---
    0x0D0F: "SH5.0RS",
    0x0D10: "SH3.6RS",
    0x0D11: "SH4.6RS",
    0x0D12: "SH6.0RS",
    0x0D23: "SH8.0RS",
    0x0D24: "SH10RS",
    0x0D25: "SH3.0RS",
    0x0D26: "SH4.0RS",

    # --- SH-RT series (three phase residential hybrid) ---
    0x0E00: "SH5.0RT",
    0x0E01: "SH6.0RT",
    0x0E02: "SH8.0RT",
    0x0E03: "SH10RT",
    0x0E04: "SH6.0RT",      # Alternate code
    0x0E05: "SH8.0RT",      # Alternate code
    0x0E06: "SH10RT",       # Alternate code
    0x0E07: "SH5.0RT-20",
    0x0E08: "SH6.0RT-20",
    0x0E09: "SH8.0RT-20",
    0x0E0A: "SH10RT-20",
    0x0E0B: "SH5.0RT-V112",
    0x0E0C: "SH5.0RT-V112", # Alternate mapping
    0x0E0D: "SH8.0RT-V112",
    0x0E0E: "SH10RT-V112",
    0x0E0F: "SH10RT-V112",  # Alternate code
    0x0E13: "SH10RT-20",    # Alternate code
    0x0E23: "SH5.0RT-V122",
    0x0E24: "SH6.0RT-V122",
    0x0E25: "SH8.0RT-V122",
    0x0E26: "SH10RT-V122",

    # --- SH-T series (three phase large hybrid) ---
    0x0E27: "SH5T",
    0x0E28: "SH25T",
    0x0E29: "SH15T",
    0x0E2A: "SH20T",
    0x0E2B: "SH10T",

    # --- Legacy SH series (older models) ---
    0x0D03: "SH5K-V13",
    0x0D06: "SH3K6",
    0x0D07: "SH4K6",
    0x0D09: "SH5K-20",
    0x0D0A: "SH5K-30",
    0x0D0B: "SH5K-30",      # Alternate code
    0x0D0C: "SH3K6-30",
    0x0D0D: "SH4K6-30",

    # ==========================================================================
    # STRING INVERTERS - RESIDENTIAL (SG-RS Series - grid-tied, no battery)
    # ==========================================================================

    # --- SG-RS series (single phase residential string) ---
    0x2603: "SG3.0RS",
    0x2604: "SG3.6RS",
    0x2605: "SG4.0RS",
    0x2606: "SG5.0RS",
    0x2607: "SG6.0RS",
    0x260E: "SG9.0RS",
    0x2609: "SG10RS",

    # --- SG-RT series (three phase residential string) ---
    0x243D: "SG3.0RT",
    0x243E: "SG4.0RT",
    0x2430: "SG5.0RT",
    0x2431: "SG6.0RT",
    0x243C: "SG7.0RT",
    0x2432: "SG8.0RT",
    0x2433: "SG10RT",
    0x2434: "SG12RT",
    0x2435: "SG15RT",
    0x2436: "SG17RT",
    0x2437: "SG20RT",

    # ==========================================================================
    # STRING INVERTERS - COMMERCIAL (SG-KTL/CX/HX Series)
    # ==========================================================================

    # --- SG-KTL series (commercial string, older) ---
    0x0027: "SG30KTL",
    0x0026: "SG10KTL",
    0x0029: "SG12KTL",
    0x0028: "SG15KTL",
    0x002A: "SG20KTL",
    0x002C: "SG30KU",
    0x002D: "SG36KTL",
    0x002E: "SG36KU",
    0x002F: "SG40KTL",
    0x0070: "SG30KTL-M-V31",
    0x0072: "SG34KJ",
    0x0073: "LP_P34KSG",
    0x0074: "SG36KTL-M",
    0x010F: "SG60KTL",
    0x011B: "SG50KTL-M-20",
    0x0131: "SG60KTL-M",
    0x0132: "SG60KU-M",
    0x0134: "SG33KTL-M",
    0x0135: "SG40KTL-M",
    0x0136: "SG60KU",
    0x0137: "SG49K5J",
    0x0138: "SG80KTL",
    0x0139: "SG80KTL-M",
    0x013B: "SG125HV",
    0x013C: "SG12KTL-M",
    0x013D: "SG33K3J",
    0x013E: "SG10KTL-M",
    0x013F: "SG8KTL-M",
    0x0141: "SG30KTL-M",
    0x0142: "SG15KTL-M",
    0x0143: "SG20KTL-M",
    0x0147: "SG5KTL-MT",
    0x0148: "SG6KTL-MT",
    0x0149: "SG17KTL-M",
    0x014C: "SG111HV",

    # --- SG-CX series (commercial string, current gen) ---
    0x2C00: "SG33CX",
    0x2C01: "SG40CX",
    0x2C02: "SG50CX",
    0x2C03: "SG125HV-20",
    0x2C06: "SG110CX",
    0x2C0A: "SG36CX-US",
    0x2C0B: "SG60CX-US",
    0x2C0F: "SG10KTL-MT",
    0x2C10: "SG30CX",
    0x2C12: "SG100CX",
    0x2C13: "SG250HX-IN",
    0x2C15: "SG25CX-SA",
    0x2C22: "SG75CX",

    # --- SG-HX series (commercial high power) ---
    0x2C0C: "SG250HX",
    0x2C11: "SG250HX-US",

    # ==========================================================================
    # G2 INVERTERS (Older generation)
    # ==========================================================================
    0x0122: "SG3K-D",
    0x0126: "SG5K-D",
    0x2403: "SG8K-D",

    # ==========================================================================
    # LEGACY STRING INVERTERS (kept for backwards compatibility)
    # ==========================================================================
    0x0233: "SG3.0RS",
    0x0234: "SG4.0RS",
    0x0235: "SG5.0RS",
    0x0236: "SG6.0RS",
}


class ModbusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Modbus configuration flow - simplified to just ask for connection details."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._connection_type = None
        self._connection_data = {}
        self._device_info = {}

    async def async_step_user(self, user_input=None):
        """Handle initial step - ask for connection type."""
        errors = {}

        if user_input is not None:
            conn_type = user_input.get(CONF_CONNECTION_TYPE)
            if conn_type:
                self._connection_type = conn_type
                return await self.async_step_connection()

            errors["base"] = "invalid_connection_type"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_CONNECTION_TYPE, default=CONN_TYPE_TCP): vol.In(CONNECTION_TYPES),
            }),
            errors=errors
        )

    async def async_step_connection(self, user_input=None):
        """Handle connection details step."""
        errors = {}

        if user_input is not None:
            self._connection_data = {CONF_CONNECTION_TYPE: self._connection_type, **user_input}

            # Try to connect and auto-detect device info
            device_info = await self._detect_device(self._connection_data)

            if device_info:
                self._device_info = device_info
                serial = device_info.get("serial_number", "")

                # Use serial number as unique ID
                if serial:
                    await self.async_set_unique_id(serial)
                    self._abort_if_unique_id_configured()

                # Create entry with detected info
                return await self._create_entry()
            else:
                errors["base"] = "cannot_connect"

        # Show connection-specific form
        if self._connection_type == CONN_TYPE_TCP:
            schema = vol.Schema({
                vol.Required("host"): str,
                vol.Required("port", default=502): int,
                vol.Required("slave", default=1): int,
            })
        else:
            schema = vol.Schema({
                vol.Required(CONF_SERIAL_PORT, default="/dev/ttyUSB0"): str,
                vol.Required(CONF_BAUDRATE, default=DEFAULT_BAUDRATE): vol.In([9600, 19200, 38400, 57600, 115200]),
                vol.Required(CONF_BYTESIZE, default=DEFAULT_BYTESIZE): vol.In([7, 8]),
                vol.Required(CONF_PARITY, default=DEFAULT_PARITY): vol.In(PARITY_OPTIONS),
                vol.Required(CONF_STOPBITS, default=DEFAULT_STOPBITS): vol.In([1, 2]),
                vol.Required("slave", default=1): int,
            })

        return self.async_show_form(
            step_id="connection",
            data_schema=schema,
            errors=errors
        )

    async def _detect_device(self, config) -> dict | None:
        """Connect to device and auto-detect serial number and model."""
        from pymodbus.client import AsyncModbusTcpClient, AsyncModbusSerialClient

        conn_type = config.get(CONF_CONNECTION_TYPE, CONN_TYPE_TCP)
        slave_id = config.get("slave", 1)

        try:
            if conn_type == CONN_TYPE_TCP:
                client = AsyncModbusTcpClient(
                    host=config["host"],
                    port=config.get("port", 502),
                    timeout=10
                )
            else:
                client = AsyncModbusSerialClient(
                    port=config[CONF_SERIAL_PORT],
                    baudrate=config.get(CONF_BAUDRATE, DEFAULT_BAUDRATE),
                    bytesize=config.get(CONF_BYTESIZE, DEFAULT_BYTESIZE),
                    parity=config.get(CONF_PARITY, DEFAULT_PARITY),
                    stopbits=config.get(CONF_STOPBITS, DEFAULT_STOPBITS),
                    timeout=10
                )

            connected = await client.connect()
            if not connected:
                _LOGGER.error("Failed to connect to inverter")
                return None

            # Read serial number (registers 4989-4998, 10 registers)
            result = await client.read_input_registers(address=4989, count=10, device_id=slave_id)
            if result.isError():
                _LOGGER.error(f"Failed to read serial number: {result}")
                client.close()
                return None

            # Decode serial number
            packed = struct.pack('>' + 'H' * len(result.registers), *result.registers)
            serial_number = packed.decode('ascii', errors='ignore').strip('\x00\r\n ')

            # Read device type code (register 4999)
            result = await client.read_input_registers(address=4999, count=1, device_id=slave_id)
            device_type_code = result.registers[0] if not result.isError() else 0

            # Map to model name
            model = DEVICE_TYPE_MAP.get(device_type_code, f"Unknown (0x{device_type_code:04X})")

            # Read nominal power (register 5000)
            result = await client.read_input_registers(address=5000, count=1, device_id=slave_id)
            nominal_power = result.registers[0] * 0.1 if not result.isError() else 0

            # Read firmware version (registers 13249-13263, 15 registers)
            firmware_version = "N/A"
            result = await client.read_input_registers(address=13249, count=15, device_id=slave_id)
            if not result.isError():
                packed = struct.pack('>' + 'H' * len(result.registers), *result.registers)
                firmware_version = packed.decode('ascii', errors='ignore').strip('\x00\r\n ')

            client.close()

            _LOGGER.info(f"Detected inverter: {model}, Serial: {serial_number}, Power: {nominal_power}kW, Firmware: {firmware_version}")

            return {
                "serial_number": serial_number,
                "device_type_code": device_type_code,
                "model": model,
                "nominal_power": nominal_power,
                "firmware_version": firmware_version,
            }

        except Exception as e:
            _LOGGER.error(f"Error detecting device: {e}")
            return None

    async def _create_entry(self):
        """Create the config entry with detected device info."""
        serial = self._device_info.get("serial_number", "unknown")
        model = self._device_info.get("model", "Sungrow")
        device_type_code = self._device_info.get("device_type_code", 0)
        firmware_version = self._device_info.get("firmware_version", "N/A")

        # Find matching inverter config or use first hybrid as default
        inverter_config = next(
            (inv for inv in SUNGROW_INVERTERS if inv.model == model),
            SUNGROW_INVERTERS[0]  # Default to first inverter if not found
        )

        # Build entry data
        data = {
            **self._connection_data,
            CONF_INVERTER_SERIAL: serial,
            "model": inverter_config.model,
            "device_type_code": device_type_code,
            "firmware_version": firmware_version,
            # Default settings - can be changed in options
            "poll_interval_fast": 10,
            "poll_interval_normal": 15,
            "poll_interval_slow": 30,
            "connection": "S2_WL_ST",
            "has_v2": True,
            "has_pv": True,
            "has_battery": True,
            "has_hv_battery": False,
        }

        title = f"Sungrow {model} ({serial})"

        return self.async_create_entry(title=title, data=data)

    async def async_step_reconfigure(self, user_input=None):
        """Handle reconfiguration."""
        errors = {}
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        conn_type = entry.data.get(CONF_CONNECTION_TYPE, CONN_TYPE_TCP)

        if user_input is not None:
            data = {**entry.data, **user_input}

            # Test connection
            device_info = await self._detect_device(data)
            if device_info:
                return self.async_update_reload_and_abort(entry, data=data)

            errors["base"] = "cannot_connect"

        # Show connection form with existing values
        if conn_type == CONN_TYPE_TCP:
            schema = vol.Schema({
                vol.Required("host", default=entry.data.get("host", "")): str,
                vol.Required("port", default=entry.data.get("port", 502)): int,
                vol.Required("slave", default=entry.data.get("slave", 1)): int,
            })
        else:
            schema = vol.Schema({
                vol.Required(CONF_SERIAL_PORT, default=entry.data.get(CONF_SERIAL_PORT, "/dev/ttyUSB0")): str,
                vol.Required(CONF_BAUDRATE, default=entry.data.get(CONF_BAUDRATE, DEFAULT_BAUDRATE)): vol.In(
                    [9600, 19200, 38400, 57600, 115200]),
                vol.Required(CONF_BYTESIZE, default=entry.data.get(CONF_BYTESIZE, DEFAULT_BYTESIZE)): vol.In([7, 8]),
                vol.Required(CONF_PARITY, default=entry.data.get(CONF_PARITY, DEFAULT_PARITY)): vol.In(PARITY_OPTIONS),
                vol.Required(CONF_STOPBITS, default=entry.data.get(CONF_STOPBITS, DEFAULT_STOPBITS)): vol.In([1, 2]),
                vol.Required("slave", default=entry.data.get("slave", 1)): int,
            })

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors
        )

    @staticmethod
    @config_entries.HANDLERS.register(DOMAIN)
    def async_get_options_flow(config_entry):
        """Return the options flow handler."""
        return ModbusOptionsFlowHandler(config_entry)


OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required("poll_interval_fast"): vol.All(int, vol.Range(min=5)),
        vol.Required("poll_interval_normal"): vol.All(int, vol.Range(min=10)),
        vol.Required("poll_interval_slow"): vol.All(int, vol.Range(min=15)),
        vol.Required("model"): vol.In(SUNGROW_MODELS),
        vol.Required("connection", default=list(CONNECTION_METHOD.keys())[0]): vol.In(CONNECTION_METHOD),
        vol.Required("has_v2", default=True): vol.Coerce(bool),
        vol.Required("has_pv", default=True): vol.Coerce(bool),
        vol.Required("has_battery", default=True): vol.Coerce(bool),
        vol.Required("has_hv_battery", default=False): vol.Coerce(bool),
        vol.Optional(CONF_MULTI_BATTERY, default=False): vol.Coerce(bool),
    }
)


class ModbusOptionsFlowHandler(OptionsFlowWithConfigEntry):
    """Handle options flow for Modbus."""

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        errors = {}

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get current values from config entry data (not options)
        current_data = {**self.config_entry.data, **self.config_entry.options}

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(OPTIONS_SCHEMA, current_data),
            errors=errors
        )
