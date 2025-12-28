import logging
import struct
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_utils

from custom_components.sungrow_modbus import DOMAIN
from custom_components.sungrow_modbus.const import (
    CONF_CONNECTION_TYPE,
    CONF_SERIAL_PORT,
    CONN_TYPE_SERIAL,
    CONN_TYPE_TCP,
    CONTROLLER,
    DRIFT_COUNTER,
    VALUES,
)

_LOGGER = logging.getLogger(__name__)

# Clock correction cooldown (seconds) - prevents spam if RTC is faulty
CLOCK_CORRECTION_COOLDOWN = 3600  # 1 hour
LAST_CLOCK_CORRECTION = "last_clock_correction"


def hex_to_ascii(hex_value):
    # Convert hexadecimal to decimal
    decimal_value = hex_value

    # Split into bytes
    byte1 = (decimal_value >> 8) & 0xFF
    byte2 = decimal_value & 0xFF

    # Convert bytes to ASCII characters
    ascii_chars = "".join([chr(byte) for byte in [byte1, byte2]])

    return ascii_chars


def extract_serial_number(values):
    packed = struct.pack(">" + "H" * len(values), *values)
    return packed.decode("ascii", errors="ignore").strip("\x00\r\n ")


def clock_drift_test(hass, controller, hours, minutes, seconds):
    import time

    current_time = dt_utils.now()
    device_time = datetime(
        current_time.year, current_time.month, current_time.day, hours, minutes, seconds, tzinfo=current_time.tzinfo
    )
    total_drift = (current_time - device_time).total_seconds()

    # Handle midnight edge case: if drift exceeds 12 hours, adjust date
    # Example: Device shows 23:59:50, current is 00:00:10 (next day)
    # Raw drift would be -23:59:40, but actual drift is +20 seconds
    if total_drift > 43200:  # More than 12 hours ahead - device is probably yesterday
        device_time = device_time - timedelta(days=1)
        total_drift = (current_time - device_time).total_seconds()
    elif total_drift < -43200:  # More than 12 hours behind - device is probably tomorrow
        device_time = device_time + timedelta(days=1)
        total_drift = (current_time - device_time).total_seconds()

    # Ensure structure
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    drift_counter = hass.data[DOMAIN].get(DRIFT_COUNTER, 0)
    last_correction = hass.data[DOMAIN].get(LAST_CLOCK_CORRECTION, 0)
    clock_adjusted = False

    if abs(total_drift) > 60:
        if drift_counter > 5:
            # Check cooldown to prevent spam if RTC is faulty
            time_since_correction = time.time() - last_correction
            if time_since_correction >= CLOCK_CORRECTION_COOLDOWN:
                if controller.connected():
                    hass.create_task(
                        controller.async_write_holding_registers(
                            43003, [current_time.hour, current_time.minute, current_time.second]
                        )
                    )
                    hass.data[DOMAIN][LAST_CLOCK_CORRECTION] = time.time()
                    hass.data[DOMAIN][DRIFT_COUNTER] = 0  # Reset counter after correction
                    clock_adjusted = True
            else:
                _LOGGER.debug(
                    f"Clock correction skipped: cooldown active ({CLOCK_CORRECTION_COOLDOWN - time_since_correction:.0f}s remaining)"
                )
        else:
            hass.data[DOMAIN][DRIFT_COUNTER] = drift_counter + 1
    else:
        hass.data[DOMAIN][DRIFT_COUNTER] = 0

    _LOGGER.debug(f"Drift: {total_drift}s, Counter: {drift_counter}, Adjusted: {clock_adjusted}")
    return clock_adjusted


def decode_inverter_model(hex_value):
    """
    Decodes an inverter model code into its protocol version and description.

    :param hex_value: The hexadecimal or decimal inverter model code.
    :return: A tuple (protocol_version, model_description)
    """
    # Convert hexadecimal string to integer if necessary
    if isinstance(hex_value, str):
        hex_value = int(hex_value, 16)

    # Extract high byte (protocol version) and low byte (inverter model)
    protocol_version = (hex_value >> 8) & 0xFF
    inverter_model = hex_value & 0xFF

    inverter_models = {
        0x00: "No definition",
        0x10: "1-Phase Grid-Tied Inverter (0.7-8K1P / 7-10K1P)",
        0x20: "3-Phase Grid-Tied Inverter (3-20K 3P)",
        0x21: "3-Phase Grid-Tied Inverter (25-50K / 50-70K / 80-110K / 90-136K / 125K / 250K)",
        0x30: "1-Phase LV Hybrid Inverter",
        0x31: "1-Phase LV AC Coupled Energy Storage Inverter",
        0x32: "5-15kWh All-in-One Hybrid",
        0x40: "1-Phase HV Hybrid Inverter",
        0x50: "3-Phase LV Hybrid Inverter",
        0x60: "3-Phase HV Hybrid Inverter (5G)",
        0x70: "S6 3-Phase HV Hybrid (5-10kW)",
        0x71: "S6 3-Phase HV Hybrid (12-20kW)",
        0x72: "S6 3-Phase LV Hybrid (10-15kW)",
        0x73: "S6 3-Phase HV Hybrid (50kW)",
        0x80: "1-Phase HV Hybrid Inverter (S6)",
        0x90: "1-Phase LV Hybrid Inverter (S6)",
        0x91: "S6 1-Phase LV AC Coupled Hybrid",
        0xA0: "OGI Off-Grid Inverter",
        0xA1: "S6 1-Phase LV Off-Grid Hybrid",
    }

    # Get model description or default to "Unknown Model"
    model_description = inverter_models.get(inverter_model, "Unknown Model")

    return protocol_version, model_description


def get_controller_key(controller) -> str:
    """Generate a unique key for a controller (includes port for TCP, path for serial)."""
    return f"{controller.connection_id}_{controller.device_id}"


def get_controller_key_from_config(config: dict) -> str:
    """Generate controller key from config dict."""
    slave = config.get("slave", 1)
    connection_type = config.get(CONF_CONNECTION_TYPE, CONN_TYPE_TCP if "host" in config else CONN_TYPE_SERIAL)

    if connection_type == CONN_TYPE_TCP:
        host = config.get("host")
        port = config.get("port", 502)
        connection_id = f"{host}:{port}"
    else:  # Serial
        connection_id = config.get(CONF_SERIAL_PORT, "/dev/ttyUSB0")

    return f"{connection_id}_{slave}"


def cache_save(hass: HomeAssistant, register: str | int, value, controller_key: str = None):
    """Save value to cache, optionally namespaced by controller."""
    hass.data.setdefault(DOMAIN, {}).setdefault(VALUES, {})

    if controller_key:
        key = f"{controller_key}:{register}"
    else:
        key = str(register)
    hass.data[DOMAIN][VALUES][key] = value


def cache_get(hass: HomeAssistant, register: str | int, controller_key: str = None):
    """Get value from cache, optionally namespaced by controller."""
    values = hass.data.get(DOMAIN, {}).get(VALUES)
    if values is None:
        return None

    if controller_key:
        key = f"{controller_key}:{register}"
    else:
        key = str(register)
    return values.get(key, None)


def set_controller(hass: HomeAssistant, controller):
    """Register a controller with proper key (includes port/path + slave)."""
    key = get_controller_key(controller)
    hass.data[DOMAIN][CONTROLLER][key] = controller


def get_controller_from_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Get controller from config entry (works for both TCP and Serial)."""
    config = {**config_entry.data, **config_entry.options}
    key = get_controller_key_from_config(config)
    return hass.data[DOMAIN][CONTROLLER].get(key)


def get_controller(hass: HomeAssistant, controller_host: str, controller_slave: int):
    """Get controller by host/port and slave (legacy function for backwards compatibility)."""
    if controller_host is None:
        # This is a serial connection, but we don't have the port info here
        # Return the first controller with matching slave
        for _key, controller in hass.data[DOMAIN][CONTROLLER].items():
            if controller.device_id == controller_slave:
                return controller
        return None

    # Try exact match first (for backwards compatibility with host_slave format)
    controller = hass.data[DOMAIN][CONTROLLER].get(f"{controller_host}_{controller_slave}")
    if controller:
        return controller

    # Try with default port for TCP
    controller = hass.data[DOMAIN][CONTROLLER].get(f"{controller_host}:502_{controller_slave}")
    if controller:
        return controller

    # Search all controllers for matching host and slave
    for _key, ctrl in hass.data[DOMAIN][CONTROLLER].items():
        if ctrl.host == controller_host and ctrl.device_id == controller_slave:
            return ctrl

    return None


def split_s32(s32_values: list[int]):
    """Combine two 16-bit registers into a signed 32-bit integer.

    Args:
        s32_values: List of two 16-bit register values [high_word, low_word]

    Returns:
        Signed 32-bit integer
    """
    if len(s32_values) < 2:
        return 0

    # High word determines sign, low word is always unsigned
    high_word = s32_values[0]
    low_word = s32_values[1]

    # Combine as unsigned 32-bit first
    unsigned_value = (high_word << 16) | (low_word & 0xFFFF)

    # Convert to signed if high bit is set
    if unsigned_value >= (1 << 31):
        return unsigned_value - (1 << 32)
    return unsigned_value


def _any_in(target: list[int], collection: set[int]) -> bool:
    return any(item in collection for item in target)


def is_correct_controller(controller, connection_id: str, slave: int):
    """Check if an event is for the correct controller.

    Args:
        controller: The ModbusController instance
        connection_id: The connection identifier (host:port for TCP, serial path for serial)
        slave: The Modbus slave/device ID

    Returns:
        bool: True if the event is for this controller
    """
    return controller.connection_id == connection_id and controller.device_id == slave


def get_bit_bool(modbus_value: int, bit_position: int) -> bool:
    """
    Decode Modbus value to boolean state for the specified bit position.

    Parameters:
    - modbus_value: The Modbus value to decode.
    - bit_position: The position of the bit to extract (0-based).

    Returns:
    - True if the bit is ON, False if the bit is OFF.
    """
    return (modbus_value >> bit_position) & 1 == 1


def set_bit(value: int, bit_position: int, new_bit_value: bool) -> int:
    """Set or clear a specific bit in an integer value."""
    mask = 1 << bit_position
    value &= ~mask  # Clear the bit
    if new_bit_value:
        value |= mask  # Set the bit
    return round(value)
