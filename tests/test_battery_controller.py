"""Tests for the BatteryController class."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.sungrow_modbus.battery_controller import (
    BatteryController,
    BatteryModule,
    BatteryStack,
    detect_battery_stacks,
)
from custom_components.sungrow_modbus.const import BATTERY_SLAVE_BASE, DOMAIN, MANUFACTURER, MAX_BATTERY_STACKS


class TestBatteryModule:
    """Test the BatteryModule dataclass."""

    def test_default_values(self):
        """Test default values for BatteryModule."""
        module = BatteryModule(index=0)
        assert module.index == 0
        assert module.serial_number == ""
        assert module.cell_voltage_max == 0.0
        assert module.cell_voltage_min == 0.0
        assert module.temperature == 0.0

    def test_with_values(self):
        """Test BatteryModule with values."""
        module = BatteryModule(
            index=1, serial_number="MOD001", cell_voltage_max=3.45, cell_voltage_min=3.30, temperature=25.5
        )
        assert module.index == 1
        assert module.serial_number == "MOD001"
        assert module.cell_voltage_max == 3.45
        assert module.cell_voltage_min == 3.30
        assert module.temperature == 25.5


class TestBatteryStack:
    """Test the BatteryStack dataclass."""

    def test_default_values(self):
        """Test default values for BatteryStack."""
        stack = BatteryStack(stack_index=0, slave_id=200)
        assert stack.stack_index == 0
        assert stack.slave_id == 200
        assert stack.serial_number == ""
        assert stack.firmware_version == ""
        assert stack.voltage == 0.0
        assert stack.current == 0.0
        assert stack.soc == 0.0
        assert stack.soh == 0.0
        assert stack.available is False
        assert stack.modules == []

    def test_with_values(self):
        """Test BatteryStack with values."""
        stack = BatteryStack(
            stack_index=1,
            slave_id=201,
            serial_number="BAT001",
            firmware_version="1.2.3",
            voltage=51.2,
            current=-5.5,
            soc=85.5,
            soh=98,
            available=True,
        )
        assert stack.stack_index == 1
        assert stack.slave_id == 201
        assert stack.serial_number == "BAT001"
        assert stack.voltage == 51.2
        assert stack.current == -5.5
        assert stack.soc == 85.5
        assert stack.available is True


class TestBatteryControllerInit:
    """Test BatteryController initialization."""

    def setup_method(self):
        """Set up test fixtures."""
        self.hass = MagicMock()
        self.inverter_controller = MagicMock()
        self.inverter_controller.connection_id = "192.168.1.100:502"
        self.inverter_controller.serial_number = "INV123456"

    def test_init_stack_0(self):
        """Test initialization for first battery stack."""
        controller = BatteryController(hass=self.hass, inverter_controller=self.inverter_controller, stack_index=0)
        assert controller.stack_index == 0
        assert controller.slave_id == 200
        assert controller.battery.stack_index == 0
        assert controller.battery.slave_id == 200
        assert controller._available is False

    def test_init_stack_1(self):
        """Test initialization for second battery stack."""
        controller = BatteryController(hass=self.hass, inverter_controller=self.inverter_controller, stack_index=1)
        assert controller.stack_index == 1
        assert controller.slave_id == 201

    def test_init_stack_3(self):
        """Test initialization for fourth battery stack."""
        controller = BatteryController(hass=self.hass, inverter_controller=self.inverter_controller, stack_index=3)
        assert controller.stack_index == 3
        assert controller.slave_id == 203

    def test_connection_id(self):
        """Test connection_id property."""
        controller = BatteryController(hass=self.hass, inverter_controller=self.inverter_controller, stack_index=0)
        assert controller.connection_id == "192.168.1.100:502_battery_0"

    def test_device_info(self):
        """Test device_info property."""
        controller = BatteryController(hass=self.hass, inverter_controller=self.inverter_controller, stack_index=0)
        controller.battery.serial_number = "BAT123"
        controller.battery.firmware_version = "1.0.0"

        info = controller.device_info
        assert (DOMAIN, "INV123456_battery_0") in info["identifiers"]
        assert info["name"] == "Sungrow Battery Stack 1"
        assert info["manufacturer"] == MANUFACTURER
        assert info["model"] == "SBR Battery"
        assert info["sw_version"] == "1.0.0"
        assert info["serial_number"] == "BAT123"
        assert info["via_device"] == (DOMAIN, "INV123456")


class TestBatteryControllerStaticMethods:
    """Test BatteryController static methods."""

    def test_decode_string_ascii(self):
        """Test decoding ASCII string from registers."""
        # "HELLO" in UTF-16BE
        registers = [0x4845, 0x4C4C, 0x4F00, 0x0000, 0x0000]
        result = BatteryController._decode_string(registers)
        assert result == "HELLO"

    def test_decode_string_with_nulls(self):
        """Test decoding string with null padding."""
        registers = [0x4142, 0x4300, 0x0000]
        result = BatteryController._decode_string(registers)
        assert result == "ABC"

    def test_decode_string_empty(self):
        """Test decoding empty registers."""
        registers = [0x0000, 0x0000]
        result = BatteryController._decode_string(registers)
        assert result == ""

    def test_decode_string_numeric(self):
        """Test decoding numeric string."""
        # "123456" in UTF-16BE
        registers = [0x3132, 0x3334, 0x3536]
        result = BatteryController._decode_string(registers)
        assert result == "123456"

    def test_to_signed_positive(self):
        """Test converting positive value."""
        assert BatteryController._to_signed(100) == 100
        assert BatteryController._to_signed(32767) == 32767

    def test_to_signed_negative(self):
        """Test converting negative value."""
        # -1 in unsigned 16-bit is 65535
        assert BatteryController._to_signed(65535) == -1
        # -100 in unsigned 16-bit is 65436
        assert BatteryController._to_signed(65436) == -100
        # -32768 (minimum) in unsigned 16-bit is 32768
        assert BatteryController._to_signed(32768) == -32768

    def test_to_signed_zero(self):
        """Test converting zero."""
        assert BatteryController._to_signed(0) == 0


class TestBatteryControllerProbe:
    """Test BatteryController probe method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.hass = MagicMock()
        self.inverter_controller = MagicMock()
        self.inverter_controller.connection_id = "192.168.1.100:502"
        self.inverter_controller.serial_number = "INV123456"

        # Mock the poll_lock as an async context manager
        self.mock_lock = MagicMock()
        self.mock_lock.__aenter__ = AsyncMock(return_value=None)
        self.mock_lock.__aexit__ = AsyncMock(return_value=None)
        self.inverter_controller.poll_lock = self.mock_lock

        # Mock the client
        self.mock_client = MagicMock()
        self.mock_client.connected = True
        self.inverter_controller.client = self.mock_client

    @pytest.mark.asyncio
    async def test_probe_success(self):
        """Test successful probe."""
        mock_result = MagicMock()
        mock_result.isError.return_value = False
        mock_result.registers = [512]  # 51.2V
        self.mock_client.read_input_registers = AsyncMock(return_value=mock_result)

        controller = BatteryController(hass=self.hass, inverter_controller=self.inverter_controller, stack_index=0)

        result = await controller.probe()

        assert result is True
        assert controller._available is True
        assert controller.battery.available is True
        self.mock_client.read_input_registers.assert_called_once_with(address=10740, count=1, slave=200)

    @pytest.mark.asyncio
    async def test_probe_error_response(self):
        """Test probe with error response."""
        mock_result = MagicMock()
        mock_result.isError.return_value = True
        self.mock_client.read_input_registers = AsyncMock(return_value=mock_result)

        controller = BatteryController(hass=self.hass, inverter_controller=self.inverter_controller, stack_index=0)

        result = await controller.probe()

        assert result is False
        assert controller._available is False
        assert controller.battery.available is False

    @pytest.mark.asyncio
    async def test_probe_exception(self):
        """Test probe with exception."""
        self.mock_client.read_input_registers = AsyncMock(side_effect=Exception("Connection failed"))

        controller = BatteryController(hass=self.hass, inverter_controller=self.inverter_controller, stack_index=0)

        result = await controller.probe()

        assert result is False
        assert controller._available is False

    @pytest.mark.asyncio
    async def test_probe_connects_if_disconnected(self):
        """Test probe connects if client is disconnected."""
        self.mock_client.connected = False
        self.mock_client.connect = AsyncMock()

        mock_result = MagicMock()
        mock_result.isError.return_value = False
        mock_result.registers = [512]
        self.mock_client.read_input_registers = AsyncMock(return_value=mock_result)

        controller = BatteryController(hass=self.hass, inverter_controller=self.inverter_controller, stack_index=0)

        await controller.probe()

        self.mock_client.connect.assert_called_once()


class TestBatteryControllerReadStatus:
    """Test BatteryController read_status method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.hass = MagicMock()
        self.inverter_controller = MagicMock()
        self.inverter_controller.connection_id = "192.168.1.100:502"
        self.inverter_controller.serial_number = "INV123456"

        # Mock the poll_lock
        self.mock_lock = MagicMock()
        self.mock_lock.__aenter__ = AsyncMock(return_value=None)
        self.mock_lock.__aexit__ = AsyncMock(return_value=None)
        self.inverter_controller.poll_lock = self.mock_lock

        # Mock the client
        self.mock_client = MagicMock()
        self.mock_client.connected = True
        self.inverter_controller.client = self.mock_client

    @pytest.mark.asyncio
    async def test_read_status_not_available(self):
        """Test read_status when battery is not available."""
        controller = BatteryController(hass=self.hass, inverter_controller=self.inverter_controller, stack_index=0)
        # Battery not available by default

        result = await controller.read_status()

        assert result == {}

    @pytest.mark.asyncio
    async def test_read_status_success(self):
        """Test successful read_status."""
        # Prepare register data:
        # [voltage, current, temp, soc, soh, charge_hi, charge_lo, discharge_hi, discharge_lo,
        #  reserved(7), cell_max, cell_max_pos, cell_min, cell_min_pos]
        registers = [
            512,  # voltage: 51.2V
            65436,  # current: -10.0A (negative = discharging)
            250,  # temperature: 25.0C
            855,  # soc: 85.5%
            98,  # soh: 98%
            0,
            10000,  # total_charge: 1000.0 kWh
            0,
            8000,  # total_discharge: 800.0 kWh
            0,
            0,
            0,
            0,
            0,
            0,
            0,  # reserved
            34500,  # cell_voltage_max: 3.45V
            5,  # cell_max_position
            33000,  # cell_voltage_min: 3.30V
            12,  # cell_min_position
        ]

        mock_result = MagicMock()
        mock_result.isError.return_value = False
        mock_result.registers = registers
        self.mock_client.read_input_registers = AsyncMock(return_value=mock_result)

        controller = BatteryController(hass=self.hass, inverter_controller=self.inverter_controller, stack_index=0)
        controller._available = True

        result = await controller.read_status()

        assert result["voltage"] == pytest.approx(51.2, rel=0.01)
        assert result["current"] == pytest.approx(-10.0, rel=0.01)
        assert result["temperature"] == pytest.approx(25.0, rel=0.01)
        assert result["soc"] == pytest.approx(85.5, rel=0.01)
        assert result["soh"] == 98

        # Verify battery object was updated
        assert controller.battery.voltage == pytest.approx(51.2, rel=0.01)
        assert controller.battery.current == pytest.approx(-10.0, rel=0.01)
        assert controller.battery.soc == pytest.approx(85.5, rel=0.01)


class TestBatteryControllerReadSerial:
    """Test BatteryController read_serial_and_firmware method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.hass = MagicMock()
        self.inverter_controller = MagicMock()
        self.inverter_controller.connection_id = "192.168.1.100:502"
        self.inverter_controller.serial_number = "INV123456"

        self.mock_lock = MagicMock()
        self.mock_lock.__aenter__ = AsyncMock(return_value=None)
        self.mock_lock.__aexit__ = AsyncMock(return_value=None)
        self.inverter_controller.poll_lock = self.mock_lock

        self.mock_client = MagicMock()
        self.mock_client.connected = True
        self.inverter_controller.client = self.mock_client

    @pytest.mark.asyncio
    async def test_read_serial_and_firmware(self):
        """Test reading serial and firmware."""
        # "BAT12345" as registers
        serial_registers = [0x4241, 0x5431, 0x3233, 0x3435, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000]
        # "1.2.3" as registers
        firmware_registers = [0x312E, 0x322E, 0x3300, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000]

        call_count = 0

        def create_result(registers):
            result = MagicMock()
            result.isError.return_value = False
            result.registers = registers
            return result

        async def mock_read(address, count, slave):
            nonlocal call_count
            call_count += 1
            if address == 10710:
                return create_result(serial_registers)
            elif address == 10720:
                return create_result(firmware_registers)
            return create_result([0] * count)

        self.mock_client.read_input_registers = mock_read

        controller = BatteryController(hass=self.hass, inverter_controller=self.inverter_controller, stack_index=0)

        result = await controller.read_serial_and_firmware()

        assert result is True
        assert controller.battery.serial_number == "BAT12345"
        assert controller.battery.firmware_version == "1.2.3"


class TestBatteryControllerReadModules:
    """Test BatteryController read_module_serials method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.hass = MagicMock()
        self.inverter_controller = MagicMock()
        self.inverter_controller.connection_id = "192.168.1.100:502"
        self.inverter_controller.serial_number = "INV123456"

        self.mock_lock = MagicMock()
        self.mock_lock.__aenter__ = AsyncMock(return_value=None)
        self.mock_lock.__aexit__ = AsyncMock(return_value=None)
        self.inverter_controller.poll_lock = self.mock_lock

        self.mock_client = MagicMock()
        self.mock_client.connected = True
        self.inverter_controller.client = self.mock_client

    @pytest.mark.asyncio
    async def test_read_module_serials_two_modules(self):
        """Test reading module serials with 2 modules."""
        # Module 1: "MOD001"
        mod1_registers = [0x4D4F, 0x4430, 0x3031, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000]
        # Module 2: "MOD002"
        mod2_registers = [0x4D4F, 0x4430, 0x3032, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000]
        # Empty module (no more modules)
        empty_registers = [0x0000] * 9

        def create_result(registers):
            result = MagicMock()
            result.isError.return_value = False
            result.registers = registers
            return result

        async def mock_read(address, count, slave):
            if address == 10821:  # Module 0
                return create_result(mod1_registers)
            elif address == 10830:  # Module 1
                return create_result(mod2_registers)
            else:  # All others empty
                return create_result(empty_registers)

        self.mock_client.read_input_registers = mock_read

        controller = BatteryController(hass=self.hass, inverter_controller=self.inverter_controller, stack_index=0)

        serials = await controller.read_module_serials()

        assert len(serials) == 2
        assert serials[0] == "MOD001"
        assert serials[1] == "MOD002"
        assert len(controller.battery.modules) == 2
        assert controller.battery.modules[0].serial_number == "MOD001"
        assert controller.battery.modules[1].serial_number == "MOD002"


class TestDetectBatteryStacks:
    """Test the detect_battery_stacks function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.hass = MagicMock()
        self.inverter_controller = MagicMock()
        self.inverter_controller.connection_id = "192.168.1.100:502"
        self.inverter_controller.serial_number = "INV123456"

        self.mock_lock = MagicMock()
        self.mock_lock.__aenter__ = AsyncMock(return_value=None)
        self.mock_lock.__aexit__ = AsyncMock(return_value=None)
        self.inverter_controller.poll_lock = self.mock_lock

        self.mock_client = MagicMock()
        self.mock_client.connected = True
        self.inverter_controller.client = self.mock_client

    @pytest.mark.asyncio
    async def test_detect_no_batteries(self):
        """Test detection when no batteries are present."""
        mock_result = MagicMock()
        mock_result.isError.return_value = True
        self.mock_client.read_input_registers = AsyncMock(return_value=mock_result)

        detected = await detect_battery_stacks(self.hass, self.inverter_controller)

        assert len(detected) == 0

    @pytest.mark.asyncio
    async def test_detect_one_battery(self):
        """Test detection of single battery."""
        call_count = 0

        def create_success_result(registers):
            result = MagicMock()
            result.isError.return_value = False
            result.registers = registers
            return result

        def create_error_result():
            result = MagicMock()
            result.isError.return_value = True
            return result

        async def mock_read(address, count, slave):
            nonlocal call_count
            call_count += 1

            # First battery (slave 200) succeeds
            if slave == 200:
                if address == 10740:  # voltage probe
                    return create_success_result([512])
                elif address == 10710:  # serial
                    return create_success_result(
                        [0x4241, 0x5431, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000]
                    )
                elif address == 10720:  # firmware
                    return create_success_result(
                        [0x312E, 0x3000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000]
                    )
                elif address >= 10821:  # modules (all empty)
                    return create_success_result([0x0000] * count)
                return create_success_result([0] * count)
            else:
                # Second battery (slave 201) fails
                return create_error_result()

        self.mock_client.read_input_registers = mock_read

        detected = await detect_battery_stacks(self.hass, self.inverter_controller)

        assert len(detected) == 1
        assert detected[0].stack_index == 0
        assert detected[0].slave_id == 200
        assert detected[0].battery.serial_number == "BAT1"

    @pytest.mark.asyncio
    async def test_detect_two_batteries(self):
        """Test detection of two batteries."""

        def create_success_result(registers):
            result = MagicMock()
            result.isError.return_value = False
            result.registers = registers
            return result

        def create_error_result():
            result = MagicMock()
            result.isError.return_value = True
            return result

        async def mock_read(address, count, slave):
            # First two batteries succeed, third fails
            if slave in [200, 201]:
                if address == 10740:
                    return create_success_result([512])
                elif address == 10710:
                    serial_num = str(slave - 199)  # "1" or "2"
                    return create_success_result(
                        [
                            0x4241,
                            0x5400 | ord(serial_num),
                            0x0000,
                            0x0000,
                            0x0000,
                            0x0000,
                            0x0000,
                            0x0000,
                            0x0000,
                            0x0000,
                        ]
                    )
                elif address == 10720:
                    return create_success_result(
                        [0x312E, 0x3000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000]
                    )
                elif address >= 10821:
                    return create_success_result([0x0000] * count)
                return create_success_result([0] * count)
            else:
                return create_error_result()

        self.mock_client.read_input_registers = mock_read

        detected = await detect_battery_stacks(self.hass, self.inverter_controller)

        assert len(detected) == 2
        assert detected[0].slave_id == 200
        assert detected[1].slave_id == 201


class TestBatteryControllerConstants:
    """Test BatteryController constants and register definitions."""

    def test_register_addresses(self):
        """Test register address definitions."""
        assert BatteryController.REGISTERS["voltage"]["address"] == 10740
        assert BatteryController.REGISTERS["current"]["address"] == 10741
        assert BatteryController.REGISTERS["soc"]["address"] == 10743
        assert BatteryController.REGISTERS["soh"]["address"] == 10744
        assert BatteryController.REGISTERS["serial_number"]["address"] == 10710
        assert BatteryController.REGISTERS["firmware_version"]["address"] == 10720

    def test_register_scales(self):
        """Test register scale factors."""
        assert BatteryController.REGISTERS["voltage"]["scale"] == 0.1
        assert BatteryController.REGISTERS["current"]["scale"] == 0.1
        assert BatteryController.REGISTERS["soc"]["scale"] == 0.1
        assert BatteryController.REGISTERS["cell_voltage_max"]["scale"] == 0.0001

    def test_module_constants(self):
        """Test module-related constants."""
        assert BatteryController.MODULE_SERIAL_BASE == 10821
        assert BatteryController.MODULE_SERIAL_COUNT == 9
        assert BatteryController.MAX_MODULES == 8

    def test_slave_id_constants(self):
        """Test slave ID constants."""
        assert BATTERY_SLAVE_BASE == 200
        assert MAX_BATTERY_STACKS == 4
