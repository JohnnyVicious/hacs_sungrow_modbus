import logging
from datetime import UTC, datetime, time

from homeassistant.components.sensor import RestoreSensor, SensorDeviceClass
from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback

from custom_components.sungrow_modbus import ModbusController
from custom_components.sungrow_modbus.const import (
    CONTROLLER,
    DOMAIN,
    REGISTER,
    SLAVE,
    TIME_ENTITIES,
    VALUE,
)
from custom_components.sungrow_modbus.data.enums import InverterFeature, InverterType
from custom_components.sungrow_modbus.helpers import (
    cache_get,
    get_controller_from_entry,
    get_controller_key,
    is_correct_controller,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry: ConfigEntry, async_add_devices):
    """Set up the time platform."""
    modbus_controller: ModbusController = get_controller_from_entry(hass, config_entry)

    inverter_config = modbus_controller.inverter_config

    timeEntities: list[SungrowTimeEntity] = []
    time_definitions = []

    # Sungrow Hybrid Inverter time entities
    # These are for Load timing control (smart loads connected to inverter)
    # Reference: sungrow_sh10rt_modbus.yaml
    # Requires hybrid inverter with battery feature
    if inverter_config.type == InverterType.HYBRID and InverterFeature.BATTERY in inverter_config.features:
        time_definitions = [
            # Load Timing Period 1 - Register 13003-13006
            # Used when Load Adjustment Mode (13002) is set to "Timing" (0)
            {"name": "Load Timing Period 1 Start", "register": 13003, "enabled": True},
            {"name": "Load Timing Period 1 End", "register": 13005, "enabled": True},
            # Load Timing Period 2 - Register 13007-13010
            {"name": "Load Timing Period 2 Start", "register": 13007, "enabled": True},
            {"name": "Load Timing Period 2 End", "register": 13009, "enabled": True},
            # Load Power Optimized Mode Period - Register 13012-13015
            # Used when Load Adjustment Mode (13002) is set to "Power optimization" (2)
            {"name": "Load Power Optimized Period Start", "register": 13012, "enabled": True},
            {"name": "Load Power Optimized Period End", "register": 13014, "enabled": True},
        ]

    for entity_definition in time_definitions:
        timeEntities.append(SungrowTimeEntity(hass, modbus_controller, entity_definition))

    # Store time entities per controller to support multi-inverter setups
    if TIME_ENTITIES not in hass.data[DOMAIN]:
        hass.data[DOMAIN][TIME_ENTITIES] = {}
    controller_key = get_controller_key(modbus_controller)
    hass.data[DOMAIN][TIME_ENTITIES][controller_key] = timeEntities

    async_add_devices(timeEntities, True)


class SungrowTimeEntity(RestoreSensor, TimeEntity):
    """Representation of a Time entity."""

    def __init__(self, hass, modbus_controller, entity_definition):
        """Initialize the Time entity."""
        #
        # Visible Instance Attributes Outside Class
        self._hass = hass
        self._modbus_controller = modbus_controller
        self._register: int = entity_definition["register"]

        # Hidden Inherited Instance Attributes
        self._attr_unique_id = f"{DOMAIN}_{modbus_controller.device_serial_number if modbus_controller.device_serial_number is not None else modbus_controller.host}_{self._register}"
        self._attr_name = entity_definition["name"]
        self._attr_has_entity_name = True
        self._attr_available = True
        self._attr_device_class = entity_definition.get("device_class", None)
        self._attr_available = True

        self._received_values = {}

    async def async_added_to_hass(self) -> None:
        """Called when entity is added to HA."""
        await super().async_added_to_hass()
        state = await self.async_get_last_sensor_data()
        if state:
            self._attr_native_value = state.native_value

        # Register event listener for real-time updates and store unsubscribe callback
        self._unsub_listener = self._hass.bus.async_listen(DOMAIN, self.handle_modbus_update)

    async def async_will_remove_from_hass(self) -> None:
        """Cleanup when entity is removed."""
        if hasattr(self, "_unsub_listener") and self._unsub_listener:
            self._unsub_listener()
            self._unsub_listener = None
        await super().async_will_remove_from_hass()

    @callback
    def handle_modbus_update(self, event):
        """Callback function that updates sensor when new register data is available."""
        updated_register = int(event.data.get(REGISTER))
        updated_controller = str(event.data.get(CONTROLLER))
        updated_controller_slave = int(event.data.get(SLAVE))

        if not is_correct_controller(self._modbus_controller, updated_controller, updated_controller_slave):
            return  # meant for a different sensor/inverter combo

        if updated_register == self._register:
            value = event.data.get(VALUE)
            if self._attr_device_class == SensorDeviceClass.TIMESTAMP:
                if isinstance(value, datetime):
                    updated_value = value
                else:
                    updated_value = datetime.now(UTC)
            else:
                updated_value = int(value)
            _LOGGER.debug(f"Sensor update received, register = {updated_register}, value = {updated_value}")
            self._received_values[updated_register] = updated_value

            if updated_value is not None:
                hour = cache_get(self.hass, self._register, self._modbus_controller.controller_key)
                minute = cache_get(self.hass, self._register + 1, self._modbus_controller.controller_key)

                if hour is not None and minute is not None:
                    hour, minute = int(hour), int(minute)

                    if 0 <= minute <= 59 and 0 <= hour <= 23:
                        _LOGGER.debug(
                            f"✅ Time updated to {hour}:{minute}, regs = {self._register}:{self._register + 1}"
                        )
                        self._attr_native_value = time(hour=hour, minute=minute)
                        self._attr_available = True
                    else:
                        self._attr_available = False
                        _LOGGER.debug(
                            f"⚠️ Time disabled due to invalid values {hour}:{minute}, regs = {self._register}:{self._register + 1}"
                        )
                else:
                    self._attr_available = False
                    _LOGGER.debug(
                        f"⚠️ Time disabled because hour or minute is None, regs = {self._register}:{self._register + 1}"
                    )

                self.schedule_update_ha_state()

    @property
    def device_info(self):
        """Return device info."""
        return self._modbus_controller.device_info

    async def async_set_value(self, value: time) -> None:
        """Set the time."""
        _LOGGER.debug(f"async_set_value : register = {self._register}, value = {value}")
        await self._modbus_controller.async_write_holding_registers(self._register, [value.hour, value.minute])
        self._attr_native_value = value
        self.async_write_ha_state()
