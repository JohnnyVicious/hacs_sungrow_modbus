"""The Modbus Integration."""

import asyncio
import copy
import logging
from datetime import datetime

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryError

from .const import (
    BATTERY_CONTROLLER,
    BATTERY_SENSORS,
    CONF_BAUDRATE,
    CONF_BYTESIZE,
    CONF_CONNECTION_TYPE,
    CONF_INVERTER_SERIAL,
    CONF_MULTI_BATTERY,
    CONF_PARITY,
    CONF_SERIAL_PORT,
    CONF_STOPBITS,
    CONN_TYPE_SERIAL,
    CONN_TYPE_TCP,
    CONTROLLER,
    DEFAULT_BAUDRATE,
    DEFAULT_BYTESIZE,
    DEFAULT_PARITY,
    DEFAULT_STOPBITS,
    DOMAIN,
    SENSOR_DERIVED_ENTITIES,
    SENSOR_ENTITIES,
    SWITCH_ENTITIES,
    TIME_ENTITIES,
    VALUES,
)
from .data.enums import InverterFeature
from .data.sungrow_config import SUNGROW_INVERTERS, InverterConfig, InverterType
from .data_retrieval import DataRetrieval
from .helpers import get_controller, get_controller_from_entry, get_controller_key, set_controller
from .modbus_controller import ModbusController
from .sensors.sungrow_base_sensor import SungrowBaseSensor, SungrowSensorGroup

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.NUMBER, Platform.SWITCH, Platform.TIME, Platform.SELECT]

SCHEME_HOLDING_REGISTER = vol.Schema(
    {
        vol.Required("address"): vol.Coerce(int),
        vol.Required("value"): vol.Coerce(int),
        vol.Optional("host"): vol.Coerce(str),
        vol.Optional("slave"): vol.All(vol.Coerce(int), vol.Range(min=1, max=247)),
    }
)
SCHEME_TIME_SET = vol.Schema({vol.Required("entity_id"): vol.Coerce(str), vol.Required("time"): vol.Coerce(str)})


# Known safe writable Sungrow holding register ranges
# These are registers documented as writable in the Sungrow Modbus protocol
SAFE_HOLDING_REGISTER_RANGES = [
    (13049, 13100),  # EMS control, SoC limits, export limits
    (33046, 33150),  # Battery power settings
    (43003, 43010),  # Clock/time settings
    (43013, 43020),  # Additional control registers
    (43074, 43090),  # Power control registers
    (43110, 43120),  # Extended control registers
]


def _is_safe_register(address: int) -> bool:
    """Check if a register address is in known safe writable ranges."""
    return any(start <= address <= end for start, end in SAFE_HOLDING_REGISTER_RANGES)


async def async_setup(hass: HomeAssistant, entry: ConfigEntry):
    """Set up the Modbus integration."""

    async def service_write_holding_register(call: ServiceCall):
        address = call.data.get("address")
        value = call.data.get("value")
        host = call.data.get("host")
        slave = call.data.get("slave", 1)

        # Validate register address is in reasonable range for Sungrow inverters
        if not (0 <= address <= 65535):
            _LOGGER.error("Invalid register address %s: must be 0-65535", address)
            return

        # Validate value is within 16-bit unsigned range
        if not (0 <= value <= 65535):
            _LOGGER.error("Invalid register value %s: must be 0-65535", value)
            return

        # Warn about unvalidated registers (but still allow the write)
        if not _is_safe_register(address):
            _LOGGER.warning(
                "Writing to register %s which is not in the known safe register list. "
                "Ensure this register is writable to avoid potential issues.",
                address,
            )

        async def write_with_logging(ctrl, addr, val):
            """Write to register with error logging."""
            try:
                result = await ctrl.async_write_holding_register(int(addr), int(val))
                if result:
                    _LOGGER.debug("Successfully wrote value %s to register %s", val, addr)
                else:
                    _LOGGER.warning("Failed to write value %s to register %s on %s", val, addr, ctrl.connection_id)
                return result
            except Exception as e:
                _LOGGER.warning("Error writing to register %s: %s", addr, e)
                return False

        if host:
            controller = get_controller(hass, host, slave)
            if controller is None:
                _LOGGER.error("No controller found for host %s, slave %s", host, slave)
                return
            await write_with_logging(controller, address, value)
        else:
            controllers = hass.data.get(DOMAIN, {}).get(CONTROLLER, {})
            if not controllers:
                _LOGGER.error("No controllers available for write operation")
                return
            for controller in controllers.values():
                await write_with_logging(controller, address, value)

    # @Ian-Johnston
    async def service_set_time(call: ServiceCall) -> None:
        """Service to update a Sungrow time entity."""
        entity_id = call.data.get("entity_id")
        time_str = call.data.get("time")

        if not entity_id or not time_str:
            _LOGGER.error("Missing entity_id or time parameter in service call")
            return

        try:
            # Try to parse time in HH:MM:SS format first, then fallback to HH:MM
            try:
                new_time = datetime.strptime(time_str, "%H:%M:%S").time()
            except ValueError:
                new_time = datetime.strptime(time_str, "%H:%M").time()
        except Exception as e:
            _LOGGER.error("Failed to parse time string '%s': %s", time_str, e)
            return

        # Look through the registered time entities for one that matches the given entity_id
        # TIME_ENTITIES is now a dict keyed by controller_key for multi-inverter support
        time_entities_dict = call.hass.data.get(DOMAIN, {}).get(TIME_ENTITIES, {})
        for _controller_key, entities in time_entities_dict.items():
            for entity in entities:
                if entity.entity_id == entity_id:
                    await entity.async_set_value(new_time)
                    _LOGGER.debug("Set time for %s to %s", entity_id, new_time)
                    return

        _LOGGER.error("Entity with id %s not found in sungrow_modbus TIME_ENTITIES", entity_id)

    hass.services.async_register(
        DOMAIN, "sungrow_write_holding_register", service_write_holding_register, schema=SCHEME_HOLDING_REGISTER
    )
    hass.services.async_register(DOMAIN, "sungrow_write_time", service_set_time, schema=SCHEME_TIME_SET)

    return True


async def async_update_options(entry):
    """Handle options updates."""
    hass = entry.hass
    await hass.config_entries.async_update_entry(entry, options=entry.options)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Modbus from a config entry."""

    # Merge data and options (options take priority)
    config = {**entry.data, **entry.options}
    slave = config.get("slave", 1)
    inverter_serial = config.get(CONF_INVERTER_SERIAL)

    if not inverter_serial:
        hass.components.persistent_notification.async_create(
            "Sungrow Modbus: Inverter Serial is missing. Please reconfigure the integration.",
            title="Sungrow Modbus Configuration Issue",
            notification_id="sungrow_modbus_missing_serial",
        )
        raise ConfigEntryError("Inverter Serial is missing")

    # Determine connection type (default to TCP for backwards compatibility with old configs)
    connection_type = config.get(CONF_CONNECTION_TYPE, CONN_TYPE_TCP if "host" in config else CONN_TYPE_SERIAL)

    # Get connection-specific parameters
    host = config.get("host")
    port = config.get("port", 502)

    if connection_type == CONN_TYPE_TCP:
        connection_id = f"{host}:{port}"
    else:  # Serial
        serial_port = config.get(CONF_SERIAL_PORT, "/dev/ttyUSB0")
        connection_id = serial_port

    # Migrate old TCP configs
    if entry.unique_id and "_" not in entry.unique_id and connection_type == CONN_TYPE_TCP:
        host = config.get("host")
        new_unique_id = f"{host}_{slave}"
        hass.config_entries.async_update_entry(entry, unique_id=new_unique_id)
        _LOGGER.debug("Migrated unique_id from %s to %s", entry.unique_id, new_unique_id)

        # Migrate title if needed
        expected_title = f"Sungrow: Host {host}, Modbus Address {slave}"
        if entry.title != expected_title:
            hass.config_entries.async_update_entry(entry, title=expected_title)
            _LOGGER.debug("Migrated title")

    _LOGGER.debug(config)

    # Initialize storage for controllers
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(CONTROLLER, {})
    hass.data[DOMAIN][entry.entry_id] = entry
    _LOGGER.info(f"Loaded Sungrow Modbus Integration ({connection_type}) with Model: {config.get('model')}")

    poll_interval_fast = config.get("poll_interval_fast", 5)
    poll_interval_normal = config.get("poll_interval_normal", 15)
    poll_interval_slow = config.get("poll_interval_slow", 30)
    inverter_model = config.get("model")

    if inverter_model is None:
        old_type = config.get("type", "hybrid")
        inverter_model = (
            "S6-EH3P" if old_type == "hybrid" else ("WAVESHARE" if old_type == "hybrid-waveshare" else "S6-GR1P")
        )

    inverter_config_template: InverterConfig = next(
        (inv for inv in SUNGROW_INVERTERS if inv.model == inverter_model), None
    )

    # defaulting
    if inverter_config_template is None:
        hass.components.persistent_notification.async_create(
            "Your Sungrow Modbus configuration is invalid. Please reconfigure the integration.",
            title="Sungrow Modbus Configuration Issue",
            notification_id="sungrow_modbus_invalid_config",
        )
        raise ConfigEntryError

    # Clone the config to avoid mutating the shared template
    inverter_config = copy.deepcopy(inverter_config_template)

    # Update options and rebuild features
    inverter_config.update_options(
        options={
            "v2": config.get("has_v2", True),
            "pv": config.get(
                "has_pv", inverter_config.type in [InverterType.HYBRID, InverterType.GRID, InverterType.WAVESHARE]
            ),
            "battery": config.get("has_battery", True),
            "hv_battery": config.get("has_hv_battery", False),
        },
        connection=config.get("connection", "S2_WL_ST"),
    )

    # Load correct sensor data based on inverter type
    if inverter_config.type in [InverterType.STRING, InverterType.GRID]:
        from .sensor_data.string_sensors import string_sensors as sensors, string_sensors_derived as sensors_derived
    else:
        from .sensor_data.hybrid_sensors import hybrid_sensors as sensors, hybrid_sensors_derived as sensors_derived

    # Apply model-specific register overrides
    from .sensor_data.model_overrides import apply_derived_overrides, apply_model_overrides

    sensors = apply_model_overrides(sensors, inverter_config.model)
    sensors_derived = apply_derived_overrides(sensors_derived, inverter_config.model)

    # Create the Modbus controller and assign sensor groups
    # Build controller parameters based on connection type
    controller_params = {
        "hass": hass,
        "device_id": slave,
        "fast_poll": poll_interval_fast,
        "normal_poll": poll_interval_normal,
        "slow_poll": poll_interval_slow,
        "inverter_config": inverter_config,
        "connection_type": connection_type,
        "serial_number": inverter_serial,
        "firmware_version": config.get("firmware_version"),
    }

    if connection_type == CONN_TYPE_TCP:
        controller_params["host"] = host
        controller_params["port"] = port
    else:  # Serial
        controller_params["serial_port"] = config.get(CONF_SERIAL_PORT, "/dev/ttyUSB0")
        controller_params["baudrate"] = config.get(CONF_BAUDRATE, DEFAULT_BAUDRATE)
        controller_params["bytesize"] = config.get(CONF_BYTESIZE, DEFAULT_BYTESIZE)
        controller_params["parity"] = config.get(CONF_PARITY, DEFAULT_PARITY)
        controller_params["stopbits"] = config.get(CONF_STOPBITS, DEFAULT_STOPBITS)

    controller = ModbusController(**controller_params)

    controller._sensor_groups = []
    for group in sensors:
        feature_requirement = group.get("feature_requirement", [])

        # If there are feature requirements, check if they exist in inverter_config.features
        if feature_requirement and not any(feature in inverter_config.features for feature in feature_requirement):
            _LOGGER.warning(
                f"Skipping sensor group '{group.get('name', group.get('register_start', 'Unnamed'))}' due to missing required features: {feature_requirement}"
            )
            continue  # Skip this group

        # If it passes the check, add to sensor groups
        controller._sensor_groups.append(SungrowSensorGroup(hass=hass, definition=group, controller=controller))

    controller._derived_sensors = [
        SungrowBaseSensor(
            hass=hass,
            name=entity.get("name"),
            controller=controller,
            registrars=[int(r) for r in entity.get("register", [])],
            write_register=entity.get("write_register", None),
            state_class=entity.get("state_class", None),
            device_class=entity.get("device_class", None),
            unit_of_measurement=entity.get("unit_of_measurement", None),
            editable=entity.get("editable", False),
            hidden=entity.get("hidden", False),
            multiplier=entity.get("multiplier", 1),
            category=entity.get("category", None),
            unique_id=f"{DOMAIN}_{controller.serial_number}_{entity['unique']}"
            if controller.serial_number
            else f"{DOMAIN}_{connection_id.replace(':', '_').replace('/', '_')}{f'_{slave}' if slave != 1 else ''}_{entity['unique']}",
        )
        for entity in sensors_derived
    ]

    set_controller(hass, controller)

    _LOGGER.debug(f"Config entry setup for {connection_type} connection: {connection_id}, slave {slave}")

    # Multi-battery detection (if enabled and using direct LAN connection)
    hass.data[DOMAIN].setdefault(BATTERY_CONTROLLER, {})
    multi_battery_enabled = config.get(CONF_MULTI_BATTERY, False)

    if multi_battery_enabled and InverterFeature.BATTERY in inverter_config.features:
        # Only attempt battery detection on TCP connections (requires direct LAN port)
        if connection_type == CONN_TYPE_TCP:
            from .battery_controller import detect_battery_stacks

            _LOGGER.info("Multi-battery monitoring enabled, detecting battery stacks...")
            try:
                battery_controllers = await detect_battery_stacks(hass, controller)
                if battery_controllers:
                    hass.data[DOMAIN][BATTERY_CONTROLLER][entry.entry_id] = battery_controllers
                    _LOGGER.info(
                        "Detected %d battery stack(s) for inverter %s", len(battery_controllers), inverter_serial
                    )
                    # Add MULTI_BATTERY feature if stacks detected
                    if InverterFeature.MULTI_BATTERY not in inverter_config.features:
                        inverter_config.features.append(InverterFeature.MULTI_BATTERY)
                else:
                    _LOGGER.info("No battery stacks detected on slave IDs 200-203")
            except Exception as e:
                _LOGGER.warning("Failed to detect battery stacks: %s", e)
        else:
            _LOGGER.warning(
                "Multi-battery monitoring requires TCP connection via direct LAN port, "
                "not available on serial connections"
            )

    # Forward entry to platforms (SENSOR is included in PLATFORMS)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Start data retrieval
    hass.data[DOMAIN].setdefault("data_retrieval", {})
    hass.data[DOMAIN]["data_retrieval"][entry.entry_id] = DataRetrieval(hass, controller, entry.entry_id)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a Modbus config entry."""
    _LOGGER.debug("init async_unload_entry")
    # Unload platforms associated with this integration
    unload_ok = all(
        await asyncio.gather(
            *(hass.config_entries.async_forward_entry_unload(entry, platform) for platform in PLATFORMS)
        )
    )

    # Clean up resources
    if unload_ok:
        data_retrieval = hass.data[DOMAIN].get("data_retrieval", {}).pop(entry.entry_id, None)
        if data_retrieval:
            await data_retrieval.async_stop()

        # Close only this entry's controller, not all controllers
        controller = get_controller_from_entry(hass, entry)
        controller_key = None
        if controller:
            controller.close_connection()
            # Remove from controller registry using proper key
            controller_key = get_controller_key(controller)
            hass.data[DOMAIN][CONTROLLER].pop(controller_key, None)

        # Clean up battery controllers
        battery_controllers = hass.data[DOMAIN].get(BATTERY_CONTROLLER, {}).pop(entry.entry_id, None)
        if battery_controllers:
            _LOGGER.debug("Cleaned up %d battery controller(s)", len(battery_controllers))

        # Clean up entity caches to prevent stale references
        if SENSOR_ENTITIES in hass.data[DOMAIN]:
            hass.data[DOMAIN][SENSOR_ENTITIES].pop(entry.entry_id, None)
        if SENSOR_DERIVED_ENTITIES in hass.data[DOMAIN]:
            hass.data[DOMAIN][SENSOR_DERIVED_ENTITIES].pop(entry.entry_id, None)
        if BATTERY_SENSORS in hass.data[DOMAIN]:
            hass.data[DOMAIN][BATTERY_SENSORS].pop(entry.entry_id, None)
        if SWITCH_ENTITIES in hass.data[DOMAIN]:
            hass.data[DOMAIN][SWITCH_ENTITIES].pop(entry.entry_id, None)
        if TIME_ENTITIES in hass.data[DOMAIN] and controller_key:
            hass.data[DOMAIN][TIME_ENTITIES].pop(controller_key, None)

        # Clean up cached register values for this controller
        if VALUES in hass.data[DOMAIN] and controller_key:
            values = hass.data[DOMAIN][VALUES]
            keys_to_remove = [k for k in values if k.startswith(f"{controller_key}:")]
            for key in keys_to_remove:
                values.pop(key, None)

        # Clean up entry data
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok
