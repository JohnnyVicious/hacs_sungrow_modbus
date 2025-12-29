"""Tests for data validation in sensors and entities."""

import inspect
import logging
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.exceptions import HomeAssistantError

from custom_components.sungrow_modbus.const import DOMAIN
from custom_components.sungrow_modbus.data.enums import Category, PollSpeed
from custom_components.sungrow_modbus.sensors.sungrow_base_sensor import (
    DEFAULT_BOUNDS_BY_UNIT,
    SungrowBaseSensor,
)
from custom_components.sungrow_modbus.sensors.sungrow_number_sensor import SungrowNumberEntity
from custom_components.sungrow_modbus.sensors.sungrow_select_entity import SungrowSelectEntity


def create_mock_controller():
    """Create a mock controller for testing."""
    controller = MagicMock()
    controller.host = "10.0.0.1"
    controller.port = 502
    controller.device_id = 1
    controller.connection_id = "10.0.0.1:502"
    controller.controller_key = "10.0.0.1:502_1"
    controller.device_serial_number = "SN123456"
    controller.connected.return_value = True
    controller.inverter_config = MagicMock()
    controller.inverter_config.model = "SH10RT"
    controller.inverter_config.features = []
    controller.inverter_config.wattage_chosen = 10000
    controller.async_write_holding_register = AsyncMock()
    controller.device_info = {
        "identifiers": {(DOMAIN, "10.0.0.1:502_1")},
        "manufacturer": "Sungrow",
        "name": "SH10RT",
    }
    return controller


def create_mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.data = {DOMAIN: {"VALUES": {}}}
    hass.bus = MagicMock()
    hass.bus.async_listen = MagicMock(return_value=MagicMock())
    hass.create_task = MagicMock()
    return hass


def close_create_task_coroutine(hass_mock):
    """Close any coroutine passed to hass.create_task to prevent 'never awaited' warnings."""
    if hass_mock.create_task.called:
        for call in hass_mock.create_task.call_args_list:
            task = call[0][0]
            if inspect.iscoroutine(task):
                task.close()


def create_sensor(
    name="Test Sensor",
    registers=None,
    min_value=None,
    max_value=None,
    multiplier=1,
    unit_of_measurement=None,
    value_mapping=None,
    signed=False,
    controller=None,
    hass=None,
):
    """Create a SungrowBaseSensor for testing."""
    if registers is None:
        registers = [5000]
    if controller is None:
        controller = create_mock_controller()
    if hass is None:
        hass = create_mock_hass()

    return SungrowBaseSensor(
        hass=hass,
        controller=controller,
        unique_id=f"{DOMAIN}_SN123456_test_sensor",
        name=name,
        registrars=registers,
        write_register=None,
        multiplier=multiplier,
        device_class=None,
        unit_of_measurement=unit_of_measurement,
        editable=False,
        state_class=None,
        default=0,
        step=1,
        hidden=False,
        enabled=True,
        category=Category.BASIC_INFORMATION,
        min_value=min_value,
        max_value=max_value,
        poll_speed=PollSpeed.NORMAL,
        value_mapping=value_mapping,
        signed=signed,
    )


class TestDefaultBounds:
    """Test default validation bounds derived from unit types."""

    def test_default_bounds_constant_defined(self):
        """Verify DEFAULT_BOUNDS_BY_UNIT contains expected unit types."""
        assert PERCENTAGE in DEFAULT_BOUNDS_BY_UNIT
        assert UnitOfTemperature.CELSIUS in DEFAULT_BOUNDS_BY_UNIT
        assert UnitOfElectricPotential.VOLT in DEFAULT_BOUNDS_BY_UNIT
        assert UnitOfElectricCurrent.AMPERE in DEFAULT_BOUNDS_BY_UNIT
        assert UnitOfPower.WATT in DEFAULT_BOUNDS_BY_UNIT
        assert UnitOfPower.KILO_WATT in DEFAULT_BOUNDS_BY_UNIT
        assert UnitOfEnergy.KILO_WATT_HOUR in DEFAULT_BOUNDS_BY_UNIT
        assert UnitOfFrequency.HERTZ in DEFAULT_BOUNDS_BY_UNIT

    def test_percentage_defaults_to_0_100(self):
        """Percentage sensors should default to 0-100 range."""
        sensor = create_sensor(unit_of_measurement=PERCENTAGE)
        assert sensor.min_value == 0
        assert sensor.max_value == 100

    def test_temperature_defaults(self):
        """Temperature sensors should have reasonable operating range."""
        sensor = create_sensor(unit_of_measurement=UnitOfTemperature.CELSIUS)
        assert sensor.min_value == -40
        assert sensor.max_value == 100

    def test_voltage_defaults(self):
        """Voltage sensors should default to 0-1000V range."""
        sensor = create_sensor(unit_of_measurement=UnitOfElectricPotential.VOLT)
        assert sensor.min_value == 0
        assert sensor.max_value == 1000

    def test_current_defaults_signed(self):
        """Current sensors should support signed values (charge/discharge).

        Note: max_value is dynamically adjusted by adjust_max() based on inverter wattage.
        The default from DEFAULT_BOUNDS_BY_UNIT is only applied if adjust_max() doesn't override.
        """
        sensor = create_sensor(unit_of_measurement=UnitOfElectricCurrent.AMPERE)
        assert sensor.min_value == -100
        # max_value is calculated from inverter wattage (10000W / 44 = ~227A, rounded to 225)
        assert sensor.max_value == 225

    def test_power_watt_defaults_signed(self):
        """Power (W) sensors should support signed values (import/export).

        Note: max_value is dynamically adjusted by adjust_max() based on inverter wattage.
        """
        sensor = create_sensor(unit_of_measurement=UnitOfPower.WATT)
        assert sensor.min_value == -50000
        # max_value is set to inverter wattage (10000W)
        assert sensor.max_value == 10000

    def test_power_kw_defaults_signed(self):
        """Power (kW) sensors should support signed values.

        Note: max_value is dynamically adjusted by adjust_max() based on inverter wattage.
        """
        sensor = create_sensor(unit_of_measurement=UnitOfPower.KILO_WATT)
        assert sensor.min_value == -50
        # max_value is set to inverter wattage / 1000 (10000W / 1000 = 10kW)
        assert sensor.max_value == 10

    def test_energy_defaults(self):
        """Energy sensors should default to large positive range."""
        sensor = create_sensor(unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR)
        assert sensor.min_value == 0
        assert sensor.max_value == 1000000

    def test_frequency_defaults(self):
        """Frequency sensors should default to grid frequency range."""
        sensor = create_sensor(unit_of_measurement=UnitOfFrequency.HERTZ)
        assert sensor.min_value == 45
        assert sensor.max_value == 65

    def test_explicit_min_overrides_default(self):
        """Explicit min_value should override unit-based default."""
        sensor = create_sensor(unit_of_measurement=PERCENTAGE, min_value=10)
        assert sensor.min_value == 10  # Explicit value wins
        assert sensor.max_value == 100  # Default still applied

    def test_explicit_max_overrides_default(self):
        """Explicit max_value should override unit-based default."""
        sensor = create_sensor(unit_of_measurement=PERCENTAGE, max_value=90)
        assert sensor.min_value == 0  # Default still applied
        assert sensor.max_value == 90  # Explicit value wins

    def test_explicit_both_override_defaults(self):
        """Explicit min and max should both override defaults."""
        sensor = create_sensor(unit_of_measurement=PERCENTAGE, min_value=20, max_value=80)
        assert sensor.min_value == 20
        assert sensor.max_value == 80

    def test_unknown_unit_no_defaults(self):
        """Unknown unit types should not get default bounds."""
        sensor = create_sensor(unit_of_measurement="unknown_unit")
        assert sensor.min_value is None
        assert sensor.max_value is None

    def test_no_unit_no_defaults(self):
        """Sensors without unit should not get default bounds."""
        sensor = create_sensor(unit_of_measurement=None)
        assert sensor.min_value is None
        assert sensor.max_value is None


class TestReadValidation:
    """Test sensor read validation (logging warnings for out-of-range values)."""

    def test_value_within_bounds_no_warning(self, caplog):
        """Value within min/max should not log any warning."""
        sensor = create_sensor(min_value=0, max_value=100)
        with caplog.at_level(logging.WARNING):
            result = sensor._convert_raw_value([50])
        assert result == 50
        assert "below minimum" not in caplog.text
        assert "above maximum" not in caplog.text

    def test_value_at_min_boundary_no_warning(self, caplog):
        """Value exactly at min should not log warning."""
        sensor = create_sensor(min_value=0, max_value=100)
        with caplog.at_level(logging.WARNING):
            result = sensor._convert_raw_value([0])
        assert result == 0
        assert "below minimum" not in caplog.text

    def test_value_at_max_boundary_no_warning(self, caplog):
        """Value exactly at max should not log warning."""
        sensor = create_sensor(min_value=0, max_value=100)
        with caplog.at_level(logging.WARNING):
            result = sensor._convert_raw_value([100])
        assert result == 100
        assert "above maximum" not in caplog.text

    def test_value_below_minimum_logs_warning(self, caplog):
        """Value below min should log warning but still return value."""
        sensor = create_sensor(min_value=0, max_value=100, signed=True)
        with caplog.at_level(logging.WARNING):
            # 65535 as unsigned becomes -1 when signed
            result = sensor._convert_raw_value([65535])
        assert result == -1  # Value is still returned
        assert "below minimum" in caplog.text
        assert "Test Sensor" in caplog.text

    def test_value_above_maximum_logs_warning(self, caplog):
        """Value above max should log warning but still return value."""
        sensor = create_sensor(min_value=0, max_value=100)
        with caplog.at_level(logging.WARNING):
            result = sensor._convert_raw_value([500])
        assert result == 500  # Value is still returned
        assert "above maximum" in caplog.text
        assert "Test Sensor" in caplog.text

    def test_none_value_skips_validation(self, caplog):
        """None values should skip validation entirely."""
        sensor = create_sensor(min_value=0, max_value=100)
        with caplog.at_level(logging.WARNING):
            result = sensor._convert_raw_value([None])
        assert result is None
        assert "below minimum" not in caplog.text
        assert "above maximum" not in caplog.text

    def test_value_mapped_sensor_skips_validation(self, caplog):
        """Value-mapped sensors (enums) should skip numeric validation."""
        sensor = create_sensor(min_value=0, max_value=10, value_mapping="running_state")
        with caplog.at_level(logging.WARNING):
            # This would be out of range for numeric validation
            sensor._convert_raw_value([999])
        # No numeric validation warning for mapped values
        assert "below minimum" not in caplog.text
        assert "above maximum" not in caplog.text

    def test_multiplier_applied_before_validation(self, caplog):
        """Validation should occur on converted value, not raw register value."""
        # Sensor with 0.1 multiplier: raw 500 -> converted 50
        sensor = create_sensor(min_value=0, max_value=100, multiplier=0.1)
        with caplog.at_level(logging.WARNING):
            result = sensor._convert_raw_value([500])  # 500 * 0.1 = 50
        assert result == 50
        assert "below minimum" not in caplog.text
        assert "above maximum" not in caplog.text

    def test_no_min_bound_skips_min_check(self, caplog):
        """When min_value is None, skip minimum validation."""
        sensor = create_sensor(min_value=None, max_value=100, signed=True)
        with caplog.at_level(logging.WARNING):
            result = sensor._convert_raw_value([65535])  # -1 signed
        assert result == -1
        assert "below minimum" not in caplog.text

    def test_no_max_bound_skips_max_check(self, caplog):
        """When max_value is None, skip maximum validation."""
        sensor = create_sensor(min_value=0, max_value=None)
        with caplog.at_level(logging.WARNING):
            result = sensor._convert_raw_value([65000])
        assert result == 65000
        assert "above maximum" not in caplog.text


class TestNumberEntityWriteValidation:
    """Test number entity write validation (blocking invalid writes)."""

    def create_number_entity(self, min_value=0, max_value=100, multiplier=1):
        """Create a SungrowNumberEntity for testing."""
        hass = create_mock_hass()
        controller = create_mock_controller()
        controller.async_write_holding_register = AsyncMock(return_value=MagicMock())

        # Create a mock base sensor with all required attributes
        sensor = MagicMock()
        sensor.name = "Test Number"
        sensor.registrars = [33000]
        sensor.write_register = 33000  # Must be set for writes to work
        sensor.min_value = min_value
        sensor.max_value = max_value
        sensor.multiplier = multiplier
        sensor.default = 50
        sensor.step = 1
        sensor.hidden = False
        sensor.enabled = True
        sensor.state_class = None
        sensor.device_class = "power"
        sensor.unit_of_measurement = "W"
        sensor.controller = controller
        sensor.unique_id = f"{DOMAIN}_SN123456_test_number"
        sensor.convert_value = MagicMock(side_effect=lambda vals: vals[0] * multiplier)

        entity = SungrowNumberEntity(hass, sensor)
        return entity

    @pytest.mark.asyncio
    async def test_valid_write_succeeds(self):
        """Write within bounds should succeed."""
        entity = self.create_number_entity(min_value=0, max_value=100)
        entity.async_write_ha_state = MagicMock()
        # Entity starts at default=50, so write a different valid value
        await entity.async_set_native_value(75)
        # Controller write should have been called
        entity.base_sensor.controller.async_write_holding_register.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_at_min_boundary_succeeds(self):
        """Write exactly at min boundary should succeed."""
        entity = self.create_number_entity(min_value=0, max_value=100)
        entity.async_write_ha_state = MagicMock()
        # Entity starts at default=50, so 0 is different
        await entity.async_set_native_value(0)
        entity.base_sensor.controller.async_write_holding_register.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_at_max_boundary_succeeds(self):
        """Write exactly at max boundary should succeed."""
        entity = self.create_number_entity(min_value=0, max_value=100)
        entity.async_write_ha_state = MagicMock()
        # Entity starts at default=50, so 100 is different
        await entity.async_set_native_value(100)
        entity.base_sensor.controller.async_write_holding_register.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_below_minimum_raises_error(self):
        """Write below min should raise HomeAssistantError."""
        entity = self.create_number_entity(min_value=0, max_value=100)
        with pytest.raises(HomeAssistantError, match="below minimum"):
            await entity.async_set_native_value(-5)

    @pytest.mark.asyncio
    async def test_write_above_maximum_raises_error(self):
        """Write above max should raise HomeAssistantError."""
        entity = self.create_number_entity(min_value=0, max_value=100)
        with pytest.raises(HomeAssistantError, match="above maximum"):
            await entity.async_set_native_value(150)

    @pytest.mark.asyncio
    async def test_write_no_min_bound_allows_negative(self):
        """When min_value is None, negative values should be allowed."""
        entity = self.create_number_entity(min_value=None, max_value=100)
        entity.async_write_ha_state = MagicMock()
        # Entity starts at default=50, so -50 is different
        await entity.async_set_native_value(-50)
        entity.base_sensor.controller.async_write_holding_register.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_no_max_bound_allows_large(self):
        """When max_value is None, large values should be allowed."""
        entity = self.create_number_entity(min_value=0, max_value=None)
        entity.async_write_ha_state = MagicMock()
        # Entity starts at default=50, so 99999 is different
        await entity.async_set_native_value(99999)
        entity.base_sensor.controller.async_write_holding_register.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_same_value_no_action(self):
        """Writing the same value should not trigger validation or write."""
        entity = self.create_number_entity(min_value=0, max_value=100)
        entity._attr_native_value = 50
        await entity.async_set_native_value(50)  # Same as current
        # Controller write should NOT be called (early return)
        entity.base_sensor.controller.async_write_holding_register.assert_not_called()


class TestSelectEntityValidation:
    """Test select entity validation."""

    def create_select_entity(self, options=None):
        """Create a SungrowSelectEntity for testing."""
        hass = create_mock_hass()
        controller = create_mock_controller()

        if options is None:
            options = [
                {"name": "Option A", "on_value": 0},
                {"name": "Option B", "on_value": 1},
                {"name": "Option C", "on_value": 2},
            ]

        entity_definition = {
            "name": "Test Select",
            "register": 33000,
            "entities": options,
        }

        entity = SungrowSelectEntity(hass, controller, entity_definition)
        # Mock async_write_ha_state to avoid Home Assistant entity registration requirements
        entity.async_write_ha_state = MagicMock()
        return entity

    @pytest.mark.asyncio
    async def test_valid_option_succeeds(self):
        """Selecting a valid option should succeed."""
        entity = self.create_select_entity()
        await entity.async_select_option("Option A")
        entity._modbus_controller.async_write_holding_register.assert_called_once_with(33000, 0)

    @pytest.mark.asyncio
    async def test_invalid_option_raises_error(self):
        """Selecting an invalid option should raise HomeAssistantError."""
        entity = self.create_select_entity()
        with pytest.raises(HomeAssistantError, match="not valid"):
            await entity.async_select_option("Invalid Option")

    @pytest.mark.asyncio
    async def test_invalid_on_value_raises_error(self):
        """Option with on_value outside u16 range should raise error."""
        options = [
            {"name": "Valid", "on_value": 100},
            {"name": "Invalid", "on_value": 70000},  # > 65535
        ]
        entity = self.create_select_entity(options=options)
        with pytest.raises(HomeAssistantError, match="Invalid register value"):
            await entity.async_select_option("Invalid")

    @pytest.mark.asyncio
    async def test_negative_on_value_raises_error(self):
        """Option with negative on_value should raise error."""
        options = [
            {"name": "Negative", "on_value": -1},
        ]
        entity = self.create_select_entity(options=options)
        with pytest.raises(HomeAssistantError, match="Invalid register value"):
            await entity.async_select_option("Negative")
