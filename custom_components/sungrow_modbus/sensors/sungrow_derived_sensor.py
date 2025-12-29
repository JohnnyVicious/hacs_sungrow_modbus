import logging
from datetime import UTC, datetime

from homeassistant.components.sensor import RestoreSensor, SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant, callback

from custom_components.sungrow_modbus.const import CONTROLLER, DOMAIN, REGISTER, SLAVE, VALUE
from custom_components.sungrow_modbus.data.status_mapping import STATUS_MAPPING
from custom_components.sungrow_modbus.helpers import clock_drift_test, decode_inverter_model, is_correct_controller
from custom_components.sungrow_modbus.sensors.sungrow_base_sensor import SungrowBaseSensor

_LOGGER = logging.getLogger(__name__)

# Virtual registers (not real Modbus addresses, used for derived sensor logic)
REGISTER_PLACEHOLDER_0 = 0  # Placeholder for derived sensors
REGISTER_PLACEHOLDER_1 = 1  # Placeholder for derived sensors
REGISTER_CLOCK_DRIFT = 90007  # Triggers clock drift check
REGISTER_LAST_SUCCESS = 90006  # Last successful Modbus timestamp

# Real register addresses
REGISTER_RUNNING_STATUS = 33095  # System running status code
REGISTER_PROTOCOL_VERSION = 35000  # Protocol/model version

# Phase voltage/current registers for power calculation
REGISTERS_PHASE_POWER = (33049, 33051, 33053, 33055)

# Active/reactive power registers for power factor calculation
REGISTERS_POWER_FACTOR = (33079, 33080, 33081, 33082)

# Battery power calculation registers
REGISTER_BATTERY_POWER = 33135

# Grid power direction registers
REGISTER_POWER_TO_GRID = 33175
REGISTER_POWER_FROM_GRID = 33171

# Sign inversion register
REGISTER_SIGN_INVERSION = 33263

# Battery power calculation constants
POWER_SCALE_FACTOR = 10
BATTERY_DIRECTION_CHARGING = 0


class SungrowDerivedSensor(RestoreSensor, SensorEntity):
    """Representation of a Modbus derived/calculated sensor."""

    def __init__(self, hass: HomeAssistant, sensor: SungrowBaseSensor):
        self._hass = hass
        self.base_sensor = sensor

        self._attr_name = sensor.name
        self._attr_has_entity_name = True
        self._attr_unique_id = sensor.unique_id

        self._register: list[int] = sensor.registrars

        self._device_class = sensor.device_class
        self._unit_of_measurement = sensor.unit_of_measurement
        self._attr_device_class = sensor.device_class
        self._attr_state_class = sensor.state_class
        self._attr_native_unit_of_measurement = sensor.unit_of_measurement
        self._attr_available = not sensor.hidden

        self.is_added_to_hass = False
        self._state = None
        self._received_values = {}

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        state = await self.async_get_last_sensor_data()
        if state:
            if self.base_sensor.device_class != SensorDeviceClass.TIMESTAMP:
                self._attr_native_value = state.native_value
            else:
                self._attr_native_value = datetime.now(UTC)
        self.is_added_to_hass = True

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

        if not is_correct_controller(self.base_sensor.controller, updated_controller, updated_controller_slave):
            return  # meant for a different sensor/inverter combo

        # Only process if this register belongs to the sensor
        if updated_register in self._register:
            self._received_values[updated_register] = event.data.get(VALUE)

            # If we haven't received all registers yet, wait
            filtered_registers = {
                reg
                for reg in self._register
                if reg not in (REGISTER_PLACEHOLDER_0, REGISTER_PLACEHOLDER_1, REGISTER_CLOCK_DRIFT)
            }
            if not all(reg in self._received_values for reg in filtered_registers):
                _LOGGER.debug(f"not all values received yet = {self._received_values}")
                return  # Wait until all registers are received

            ## start
            if REGISTER_CLOCK_DRIFT in self._register:
                is_adjusted = clock_drift_test(
                    self.hass,
                    self.base_sensor.controller,
                    self._received_values[33025],
                    self._received_values[33026],
                    self._received_values[33027],
                )
                if is_adjusted:
                    self._attr_available = True
                    self._attr_native_value = datetime.now(UTC)
                    self.async_write_ha_state()
                    self._received_values.clear()

            if REGISTER_LAST_SUCCESS in self._register:
                new_value = self.base_sensor.controller.last_modbus_success
                if new_value == 0 or new_value is None:
                    return
                self._attr_available = True
                self._attr_native_value = new_value
                self.async_write_ha_state()
                self._received_values.clear()
                return

            new_value = self.base_sensor.get_value

            if REGISTER_RUNNING_STATUS in self._register:
                new_value = round(self.base_sensor.get_value)
                new_value = STATUS_MAPPING.get(new_value, "Unknown")

            if any(r in self._register for r in REGISTERS_PHASE_POWER) and len(self._register) >= 2:
                r1_value = self._received_values[self._register[0]] * self.base_sensor.multiplier
                r2_value = self._received_values[self._register[1]] * self.base_sensor.multiplier
                new_value = round(r1_value * r2_value)

            if any(r in self._register for r in REGISTERS_POWER_FACTOR) and len(self._register) >= 4:
                active_power = self.base_sensor.convert_value(
                    [self._received_values[self._register[0]], self._received_values[self._register[1]]]
                )
                reactive_power = self.base_sensor.convert_value(
                    [self._received_values[self._register[2]], self._received_values[self._register[3]]]
                )

                # Power factor = P / sqrt(P² + Q²)
                # When both are zero, PF is undefined - use 1 (unity) as default
                # When active = 0 but reactive ≠ 0, PF = 0
                # When reactive = 0 but active ≠ 0, PF = ±1
                apparent_power = (active_power**2 + reactive_power**2) ** 0.5
                if apparent_power == 0:
                    new_value = 1  # No power flowing, unity power factor as default
                else:
                    new_value = round(active_power / apparent_power, 3)

            if REGISTER_BATTERY_POWER in self._register and len(self._register) == 4:
                registers = self._register.copy()
                # Use local copy for convert_value to avoid mutating self._register
                power_registers = registers[:2]

                p_value = self.base_sensor.convert_value([self._received_values[reg] for reg in power_registers])
                d_w_value = registers[3]
                d_value = self._received_values[registers[2]]

                if str(d_value) == str(d_w_value):
                    new_value = round(p_value * POWER_SCALE_FACTOR)
                else:
                    new_value = 0

            if REGISTER_BATTERY_POWER in self._register and len(self._register) == 3:
                registers = self._register.copy()
                # Use local copy for convert_value to avoid mutating self._register
                power_registers = registers[:2]

                p_value = self.base_sensor.convert_value([self._received_values[reg] for reg in power_registers])
                d_value = self._received_values[registers[2]]

                # BATTERY_DIRECTION_CHARGING (0) = charging, 1 = discharging
                if str(d_value) == str(BATTERY_DIRECTION_CHARGING):
                    new_value = round(p_value * POWER_SCALE_FACTOR) * -1
                else:
                    new_value = round(p_value * POWER_SCALE_FACTOR)

            if REGISTER_SIGN_INVERSION in self._register and len(self._register) == 2:
                new_value = new_value * -1

            if REGISTER_POWER_TO_GRID in self._register or REGISTER_POWER_FROM_GRID in self._register:
                to_grid = self._received_values[self._register[0]] * self.base_sensor.multiplier
                from_grid = self._received_values[self._register[1]] * self.base_sensor.multiplier
                new_value = from_grid - to_grid

            # set after
            if REGISTER_PROTOCOL_VERSION in self._register:
                protocol_version, model_description = decode_inverter_model(new_value)
                self.base_sensor.controller.set_sw_version(protocol_version)
                self.base_sensor.controller.set_model(model_description)
                new_value = model_description + f"(Protocol {protocol_version})"

            # Update state if valid value exists
            if new_value is not None:
                self._attr_available = True
                self._attr_native_value = new_value
                self._state = new_value
                self.async_write_ha_state()

            # Clear received values after update
            self._received_values.clear()

    @property
    def device_info(self):
        """Return device info."""
        return self.base_sensor.controller.device_info
