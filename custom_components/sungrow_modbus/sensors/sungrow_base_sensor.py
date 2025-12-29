# sungrow_base.py
import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.const import (
    PERCENTAGE,
    UnitOfApparentPower,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant

from custom_components.sungrow_modbus.const import DOMAIN
from custom_components.sungrow_modbus.data.alarm_codes import (
    get_alarm_description,
    get_running_state,
    get_system_state,
)
from custom_components.sungrow_modbus.data.enums import Category, InverterFeature, PollSpeed
from custom_components.sungrow_modbus.helpers import _any_in, cache_get, extract_serial_number, split_s32

_LOGGER = logging.getLogger(__name__)

# Mapping type names to lookup functions
VALUE_MAPPING_FUNCTIONS = {
    "alarm": get_alarm_description,
    "running_state": get_running_state,
    "system_state": get_system_state,
}

# Default validation bounds by unit of measurement
# Used when sensor definitions don't specify explicit min/max values
DEFAULT_BOUNDS_BY_UNIT = {
    PERCENTAGE: (0, 100),
    UnitOfTemperature.CELSIUS: (-40, 100),
    UnitOfElectricPotential.VOLT: (0, 1000),
    UnitOfElectricCurrent.AMPERE: (-100, 100),
    UnitOfPower.WATT: (-50000, 50000),
    UnitOfPower.KILO_WATT: (-50, 50),
    UnitOfEnergy.KILO_WATT_HOUR: (0, 1000000),
    UnitOfFrequency.HERTZ: (45, 65),
}


class SungrowBaseSensor:
    """Base class for all Sungrow sensors."""

    def __init__(
        self,
        hass: HomeAssistant,
        controller,
        unique_id: str,
        name: str,
        registrars: list[int],
        write_register: int,
        multiplier: float,
        device_class: SwitchDeviceClass | SensorDeviceClass | str = None,
        unit_of_measurement: UnitOfElectricPotential
        | UnitOfApparentPower
        | UnitOfElectricCurrent
        | UnitOfPower = None,
        editable: bool = False,
        state_class: SensorStateClass = None,
        default=None,
        step=0.1,
        hidden=False,
        enabled=True,
        category: Category = None,
        min_value: int | None = None,
        max_value: int | None = None,
        poll_speed=PollSpeed.NORMAL,
        value_mapping: str | dict[int, str] | None = None,
        signed: bool = False,
    ):
        """
        :param name: Sensor name
        :param registrars: First register address
        :param signed: If True, treat single register values as signed 16-bit integers (S16)
        :param value_mapping: Optional mapping for value lookup. Can be:
            - A string: "alarm", "running_state", "system_state" to use predefined mappings
            - A dict: Custom {int: str} mapping for this specific sensor
        """
        self.hass = hass
        self.unique_id = unique_id
        self.controller = controller
        self.name = name
        self.default = default
        self.registrars = registrars
        self.write_register = write_register
        _LOGGER.debug(f" self.registrars = {self.registrars} | self.write_register = {self.write_register}")
        self.editable = editable
        self.multiplier = multiplier
        self.device_class = device_class
        self.unit_of_measurement = unit_of_measurement
        self.hidden = hidden
        self.state_class = state_class
        self.max_value = max_value
        self.adjust_max(max_value)
        self.step = self.get_step(step)
        self.enabled = enabled
        self.min_value = min_value
        self._apply_default_bounds()
        self.poll_speed = poll_speed
        self.category = category
        self.value_mapping = value_mapping
        self.signed = signed
        self._last_raw_value = None  # Store raw value for attributes

        self.dynamic_adjustments()

    def dynamic_adjustments(self):
        inv_model = self.controller.inverter_config.model
        inv_features = self.controller.inverter_config.features

        # HV battery-specific adjustments
        if InverterFeature.HV_BATTERY in inv_features:
            hv_battery_sensitive_regs = {33205, 33206, 33207, 43013, 43117}
            if _any_in(self.registrars, hv_battery_sensitive_regs):
                self.min_value = 0
                self.step = min(self.step, 0.1)

        # RHI/RAI models: 1 <--> 1W (range: 0–30000)
        if inv_model in {"RHI-1P", "RHI-3P", "RAI-3K-48ES-5G"} and 43074 in self.registrars:
            self.multiplier = 1

        # S6-EH3P10K-H-ZP or ZONNEPLAN feature: apply 0.01 multiplier
        elif inv_model == "S6-EH3P10K-H-ZP" or InverterFeature.ZONNEPLAN in inv_features:
            s6_registers = {33142, 33161, 33162, 33163, 33164, 33165, 33166, 33167, 33168}
            if _any_in(self.registrars, s6_registers):
                self.multiplier = 0.01

    def adjust_max(self, max_default):
        try:
            new_max = max_default
            if self.unit_of_measurement == UnitOfElectricCurrent.AMPERE:
                new_max = round((self.controller.inverter_config.wattage_chosen / 44) / 5) * 5
            elif self.unit_of_measurement == UnitOfPower.WATT:
                new_max = self.controller.inverter_config.wattage_chosen
            elif self.unit_of_measurement == UnitOfPower.KILO_WATT:
                new_max = self.controller.inverter_config.wattage_chosen / 1000
            _LOGGER.debug(
                f"max value for {self.registrars} with UOM {self.unit_of_measurement} set to {new_max} instead of {max_default}"
            )
            self.max_value = new_max
        except Exception as e:
            _LOGGER.error(
                "Dynamic UOM set failed, wanted = %s : %s", self.controller.inverter_config.wattage_chosen, e
            )

    def get_step(self, wanted_step):
        if wanted_step is not None:
            return wanted_step
        if self.unit_of_measurement == PERCENTAGE:
            return 1
        if self.unit_of_measurement == UnitOfPower.KILO_WATT:
            return 0.1
        if self.unit_of_measurement == UnitOfPower.WATT:
            return 1

    @property
    def get_raw_values(self):
        return [cache_get(self.hass, reg, self.controller.controller_key) for reg in self.registrars]

    @property
    def get_value(self):
        return self._convert_raw_value(self.get_raw_values)

    def convert_value(self, value: list[int]):
        return self._convert_raw_value(value)

    def _convert_raw_value(self, values: list[int]):
        if None in values:
            return None

        # multiplier == 0 indicates string type (serial numbers, firmware versions, etc.)
        if self.multiplier == 0 and len(self.registrars) > 1:
            n_value = extract_serial_number(values)
        elif len(self.registrars) > 1:
            combined_value = split_s32(values)

            if self.multiplier == 0 or self.multiplier == 1:
                n_value = round(combined_value)
            else:
                n_value = combined_value * self.multiplier
        else:
            # Treat it as a single register (U16/S16)
            raw_value = values[0]
            # Convert from unsigned to signed 16-bit if needed
            if self.signed and raw_value >= 32768:
                raw_value = raw_value - 65536
            if self.multiplier == 0 or self.multiplier == 1:
                n_value = round(raw_value)
            else:
                n_value = raw_value * self.multiplier

        # Store raw value for attribute access
        self._last_raw_value = n_value

        # Validate converted value against bounds
        self._validate_read_value(n_value)

        # Apply value mapping if configured
        if self.value_mapping is not None:
            n_value = self._apply_value_mapping(n_value)

        return n_value

    def _apply_value_mapping(self, raw_value: int) -> str:
        """
        Convert a raw numeric value to a human-readable string using the configured mapping.

        Args:
            raw_value: The numeric value to look up

        Returns:
            The mapped string value, or a default "Unknown" string if not found
        """
        if raw_value is None:
            return None

        # Handle string mapping type (predefined mappings)
        if isinstance(self.value_mapping, str):
            lookup_func = VALUE_MAPPING_FUNCTIONS.get(self.value_mapping)
            if lookup_func:
                return lookup_func(int(raw_value))
            else:
                _LOGGER.warning(f"Unknown value mapping type: {self.value_mapping}")
                return str(raw_value)

        # Handle dict mapping type (custom mapping)
        elif isinstance(self.value_mapping, dict):
            return self.value_mapping.get(int(raw_value), f"Unknown ({raw_value})")

        return str(raw_value)

    @property
    def raw_value(self) -> int | None:
        """Get the last raw numeric value before mapping was applied."""
        return self._last_raw_value

    @property
    def has_value_mapping(self) -> bool:
        """Check if this sensor uses value mapping."""
        return self.value_mapping is not None

    def get_info(self):
        """Return basic sensor information."""
        return {"name": self.name, "registrars": self.registrars}

    @staticmethod
    def _get_default_bounds(unit_of_measurement) -> tuple[int | None, int | None]:
        """
        Get default validation bounds based on unit of measurement.

        Returns:
            Tuple of (min_value, max_value) or (None, None) if no defaults defined
        """
        return DEFAULT_BOUNDS_BY_UNIT.get(unit_of_measurement, (None, None))

    def _apply_default_bounds(self) -> None:
        """
        Apply default validation bounds based on unit of measurement.

        Only applies defaults when min_value or max_value is None (not explicitly set).
        Explicit values in sensor definitions always take precedence.
        """
        default_min, default_max = self._get_default_bounds(self.unit_of_measurement)

        if self.min_value is None and default_min is not None:
            self.min_value = default_min
        if self.max_value is None and default_max is not None:
            self.max_value = default_max

    def _validate_read_value(self, value) -> None:
        """
        Log warning if converted value is outside expected bounds.

        This validation runs in debug mode - values are still returned but
        out-of-range readings are logged for investigation.
        """
        if value is None:
            return

        # Skip validation for value-mapped sensors (enums like running_state)
        if self.value_mapping is not None:
            return

        # Skip validation for string values (serial numbers, firmware versions)
        if isinstance(value, str):
            return

        if self.min_value is not None and value < self.min_value:
            _LOGGER.warning(
                "Sensor '%s' (register %s) value %s below minimum %s",
                self.name,
                self.registrars,
                value,
                self.min_value,
            )
        elif self.max_value is not None and value > self.max_value:
            _LOGGER.warning(
                "Sensor '%s' (register %s) value %s above maximum %s",
                self.name,
                self.registrars,
                value,
                self.max_value,
            )


class SungrowSensorGroup:
    sensors: list[SungrowBaseSensor]

    def __init__(self, hass, definition, controller):
        self._sensors = list(
            map(
                lambda entity: SungrowBaseSensor(
                    hass=hass,
                    name=entity.get("name", "reserve"),
                    controller=controller,
                    registrars=[int(r) for r in entity["register"]],
                    write_register=entity.get("write_register", None),
                    state_class=entity.get("state_class", None),
                    device_class=entity.get("device_class", None),
                    unit_of_measurement=entity.get("unit_of_measurement", None),
                    hidden=entity.get("hidden", False),
                    editable=entity.get("editable", False),
                    max_value=entity.get("max"),
                    min_value=entity.get("min"),
                    step=entity.get("step", None),
                    category=entity.get("category", None),
                    default=entity.get("default", 0),
                    multiplier=entity.get("multiplier", 1),
                    value_mapping=entity.get("value_mapping", None),
                    signed=entity.get("signed", False),
                    unique_id="{}_{}_{}".format(
                        DOMAIN, controller.device_serial_number, entity.get("unique", "reserve")
                    ),
                    poll_speed=definition.get("poll_speed", PollSpeed.NORMAL),
                ),
                definition.get("entities", []),
            )
        )
        self.poll_speed: PollSpeed = definition.get(
            "poll_speed", PollSpeed.NORMAL if self.start_register < 40000 else PollSpeed.SLOW
        )
        self._is_holding: bool = definition.get("holding", False)
        self._cache_ttl: int | None = definition.get("cache_ttl", None)

        _LOGGER.debug(
            f"Sensor group creation. start registrar = {self.start_register}, sensor count = {self.sensors_count}, registrar count = {self.registrar_count}"
        )
        self.validate_sequential_registrars()

    def validate_sequential_registrars(self):
        """Ensure all registrars increase sequentially without skipping numbers."""
        all_registrars = sorted(set(reg for sensor in self._sensors for reg in sensor.registrars))

        for i in range(len(all_registrars) - 1):
            if all_registrars[i + 1] != all_registrars[i] + 1:
                _LOGGER.error(
                    f"Registrar sequence error! Found gap between {all_registrars[i]} and {all_registrars[i + 1]} in sensor group."
                )

    @property
    def sensors_count(self):
        return len(self._sensors)

    @property
    def sensors(self):
        return self._sensors

    @property
    def registrar_count(self):
        return sum(len(sensor.registrars) for sensor in self._sensors)

    @property
    def start_register(self):
        return min(reg for sensor in self._sensors for reg in sensor.registrars)

    @property
    def is_holding(self) -> bool:
        """Return True if this group uses holding registers instead of input registers."""
        return self._is_holding

    @property
    def cache_ttl(self) -> int | None:
        """Return the cache TTL in seconds, or None if caching is disabled.

        When set, register values are cached for this duration to reduce
        Modbus reads for slow-changing values like firmware versions.
        """
        return self._cache_ttl
