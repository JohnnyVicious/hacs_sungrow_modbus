import logging

from homeassistant.components.select import SelectEntity
from homeassistant.core import callback
from homeassistant.helpers.restore_state import RestoreEntity

from custom_components.sungrow_modbus import ModbusController
from custom_components.sungrow_modbus.const import CONTROLLER, DOMAIN, REGISTER, SLAVE
from custom_components.sungrow_modbus.helpers import cache_get, get_bit_bool, is_correct_controller, set_bit

_LOGGER = logging.getLogger(__name__)


class SungrowSelectEntity(RestoreEntity, SelectEntity):
    def __init__(self, hass, modbus_controller, entity_definition) -> None:
        self._hass = hass
        self._modbus_controller: ModbusController = modbus_controller
        self._register = entity_definition["register"]
        self._attr_name = entity_definition["name"]
        self._attr_has_entity_name = True
        self._attr_unique_id = "{}_{}_{}_select".format(
            DOMAIN, self._modbus_controller.device_serial_number, entity_definition["register"]
        )
        self._attr_options = [e["name"] for e in entity_definition["entities"]]
        self._attr_options_raw = entity_definition["entities"]
        self._current_option = None
        self._unsub_listener = None

    async def async_added_to_hass(self) -> None:
        """Called when entity is added to HA."""
        await super().async_added_to_hass()
        # Restore previous state if available
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (None, "unknown", "unavailable"):
            self._current_option = last_state.state

        # Register event listener for real-time updates
        self._unsub_listener = self._hass.bus.async_listen(DOMAIN, self.handle_modbus_update)

    async def async_will_remove_from_hass(self) -> None:
        """Cleanup when entity is removed."""
        if self._unsub_listener:
            self._unsub_listener()
            self._unsub_listener = None
        await super().async_will_remove_from_hass()

    @callback
    def handle_modbus_update(self, event):
        """Callback function that updates entity when new register data is available."""
        updated_register = int(event.data.get(REGISTER))
        updated_controller = str(event.data.get(CONTROLLER))
        updated_controller_slave = int(event.data.get(SLAVE))

        if not is_correct_controller(self._modbus_controller, updated_controller, updated_controller_slave):
            return  # meant for a different sensor/inverter combo

        if updated_register == self._register:
            # The current_option property will read from cache, so just trigger a state update
            self.async_write_ha_state()

    @property
    def current_option(self) -> str | None:
        reg_cache = cache_get(self._hass, self._register, self._modbus_controller.controller_key)
        if reg_cache is None:
            return

        # Sort by number of requires descending to prioritize more specific matches
        sorted_options = sorted(
            self._attr_options_raw, key=lambda e: len(e.get("requires", [])) if "requires" in e else 0, reverse=True
        )

        for e in sorted_options:
            on_value = e.get("on_value")
            bit_position = e.get("bit_position")
            requires = e.get("requires")

            if (on_value is not None and reg_cache == on_value) or (
                bit_position is not None
                and get_bit_bool(reg_cache, bit_position)
                and (not requires or all(get_bit_bool(reg_cache, rbit) for rbit in requires))
            ):
                return e["name"]

        return None

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        for e in self._attr_options_raw:
            on_value = e.get("on_value", None)
            bit_position = e.get("bit_position", None)
            conflicts_with = e.get("conflicts_with", None)
            requires = e.get("requires", None)

            if e["name"] == option:
                if on_value is not None:
                    await self._modbus_controller.async_write_holding_register(self._register, on_value)
                    self._attr_current_option = option
                    self.async_write_ha_state()
                    break
                else:
                    self.set_register_bit(on_value, bit_position, conflicts_with, requires)
                    self.async_write_ha_state()
                    break

    @property
    def device_info(self):
        """Return device info."""
        return self._modbus_controller.device_info

    def set_register_bit(self, on_value, bit_position, conflicts_with, requires):
        """Set or clear a specific bit in the Modbus register."""
        controller = self._modbus_controller
        current_register_value = cache_get(self._hass, self._register, self._modbus_controller.controller_key)

        # Default to 0 if cache is empty (before first poll)
        if current_register_value is None:
            current_register_value = 0

        if bit_position is not None:
            # Clear conflicts
            if conflicts_with:
                for wbit in conflicts_with:
                    current_register_value = set_bit(current_register_value, wbit, False)

            # Set dependencies
            if requires:
                for rbit in requires:
                    current_register_value = set_bit(current_register_value, rbit, True)

            new_register_value: int = set_bit(current_register_value, bit_position, True)

        else:
            new_register_value: int = on_value

        _LOGGER.debug(
            f"Attempting bit {bit_position} to {True} in register {self._register}. New value for register {new_register_value}"
        )
        # we only want to write when values has changed. After, we read the register again to make sure it applied.
        # Note: cache_save is handled by ModbusController on successful write
        if current_register_value != new_register_value and controller.connected():
            self._hass.create_task(controller.async_write_holding_register(self._register, new_register_value))
        self._attr_available = True
