"""Tests for multi-inverter configuration and controller management."""

from unittest.mock import MagicMock

from custom_components.sungrow_modbus.const import (
    CONF_CONNECTION_TYPE,
    CONF_SERIAL_PORT,
    CONN_TYPE_SERIAL,
    CONN_TYPE_TCP,
    CONTROLLER,
    DOMAIN,
    VALUES,
)
from custom_components.sungrow_modbus.data.enums import InverterType, PollSpeed
from custom_components.sungrow_modbus.helpers import (
    cache_get,
    cache_save,
    get_controller,
    get_controller_from_entry,
    get_controller_key,
    get_controller_key_from_config,
    is_correct_controller,
    set_controller,
)


def create_mock_controller(host="10.0.0.1", port=502, slave=1, connection_type=CONN_TYPE_TCP):
    """Create a mock controller."""
    controller = MagicMock()
    controller.host = host
    controller.port = port
    controller.device_id = slave
    controller.slave = slave
    controller.connection_id = f"{host}:{port}" if connection_type == CONN_TYPE_TCP else host
    controller.connected.return_value = True
    controller.inverter_config = MagicMock()
    controller.inverter_config.type = InverterType.HYBRID
    controller.poll_speed = {PollSpeed.FAST: 5, PollSpeed.NORMAL: 15, PollSpeed.SLOW: 30}
    return controller


class TestControllerKeyGeneration:
    """Test controller key generation for different connection types."""

    def test_get_controller_key_tcp(self):
        """Test key generation for TCP connection."""
        controller = create_mock_controller(host="192.168.1.100", port=502, slave=1)
        key = get_controller_key(controller)
        assert key == "192.168.1.100:502_1"

    def test_get_controller_key_tcp_different_port(self):
        """Test key generation with non-default port."""
        controller = create_mock_controller(host="192.168.1.100", port=8502, slave=1)
        key = get_controller_key(controller)
        assert key == "192.168.1.100:8502_1"

    def test_get_controller_key_tcp_different_slave(self):
        """Test key generation with different slave ID."""
        controller = create_mock_controller(host="192.168.1.100", port=502, slave=2)
        key = get_controller_key(controller)
        assert key == "192.168.1.100:502_2"

    def test_get_controller_key_serial(self):
        """Test key generation for serial connection."""
        controller = MagicMock()
        controller.connection_id = "/dev/ttyUSB0"
        controller.device_id = 1
        key = get_controller_key(controller)
        assert key == "/dev/ttyUSB0_1"

    def test_get_controller_key_from_config_tcp(self):
        """Test key from config dict for TCP."""
        config = {"host": "192.168.1.100", "port": 502, "slave": 1, CONF_CONNECTION_TYPE: CONN_TYPE_TCP}
        key = get_controller_key_from_config(config)
        assert key == "192.168.1.100:502_1"

    def test_get_controller_key_from_config_tcp_default_port(self):
        """Test key from config uses default port 502."""
        config = {"host": "192.168.1.100", "slave": 1, CONF_CONNECTION_TYPE: CONN_TYPE_TCP}
        key = get_controller_key_from_config(config)
        assert key == "192.168.1.100:502_1"

    def test_get_controller_key_from_config_serial(self):
        """Test key from config for serial connection."""
        config = {CONF_SERIAL_PORT: "/dev/ttyUSB0", "slave": 1, CONF_CONNECTION_TYPE: CONN_TYPE_SERIAL}
        key = get_controller_key_from_config(config)
        assert key == "/dev/ttyUSB0_1"

    def test_get_controller_key_from_config_default_slave(self):
        """Test key from config uses default slave 1."""
        config = {"host": "192.168.1.100", CONF_CONNECTION_TYPE: CONN_TYPE_TCP}
        key = get_controller_key_from_config(config)
        assert key == "192.168.1.100:502_1"


class TestControllerRegistry:
    """Test controller registration and retrieval."""

    def test_set_controller_registers_correctly(self):
        """Test controller is registered with correct key."""
        hass = MagicMock()
        hass.data = {DOMAIN: {CONTROLLER: {}}}

        controller = create_mock_controller(host="192.168.1.100", port=502, slave=1)
        set_controller(hass, controller)

        assert "192.168.1.100:502_1" in hass.data[DOMAIN][CONTROLLER]
        assert hass.data[DOMAIN][CONTROLLER]["192.168.1.100:502_1"] is controller

    def test_get_controller_from_entry_tcp(self):
        """Test retrieving controller from config entry."""
        controller = create_mock_controller(host="192.168.1.100", port=502, slave=1)

        hass = MagicMock()
        hass.data = {DOMAIN: {CONTROLLER: {"192.168.1.100:502_1": controller}}}

        config_entry = MagicMock()
        config_entry.data = {"host": "192.168.1.100", "port": 502, "slave": 1}
        config_entry.options = {}

        result = get_controller_from_entry(hass, config_entry)
        assert result is controller

    def test_get_controller_by_host_and_slave(self):
        """Test legacy get_controller function."""
        controller = create_mock_controller(host="192.168.1.100", port=502, slave=1)

        hass = MagicMock()
        hass.data = {DOMAIN: {CONTROLLER: {"192.168.1.100:502_1": controller}}}

        result = get_controller(hass, "192.168.1.100", 1)
        assert result is controller

    def test_get_controller_not_found(self):
        """Test get_controller returns None for missing controller."""
        hass = MagicMock()
        hass.data = {DOMAIN: {CONTROLLER: {}}}

        result = get_controller(hass, "192.168.1.100", 1)
        assert result is None


class TestMultiInverterIsolation:
    """Test event isolation between multiple inverters."""

    def test_is_correct_controller_matches(self):
        """Test is_correct_controller returns True for matching controller."""
        controller = create_mock_controller(host="192.168.1.100", slave=1)
        assert is_correct_controller(controller, "192.168.1.100", 1) is True

    def test_is_correct_controller_wrong_host(self):
        """Test is_correct_controller returns False for wrong host."""
        controller = create_mock_controller(host="192.168.1.100", slave=1)
        assert is_correct_controller(controller, "192.168.1.101", 1) is False

    def test_is_correct_controller_wrong_slave(self):
        """Test is_correct_controller returns False for wrong slave."""
        controller = create_mock_controller(host="192.168.1.100", slave=1)
        assert is_correct_controller(controller, "192.168.1.100", 2) is False

    def test_multi_inverter_cache_isolation(self):
        """Test cache values are isolated per controller."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {}}}

        # Save values for two different controllers
        cache_save(hass, 33000, 100, "192.168.1.100:502_1")
        cache_save(hass, 33000, 200, "192.168.1.101:502_1")

        # Retrieve and verify isolation
        value1 = cache_get(hass, 33000, "192.168.1.100:502_1")
        value2 = cache_get(hass, 33000, "192.168.1.101:502_1")

        assert value1 == 100
        assert value2 == 200

    def test_cache_get_missing_returns_none(self):
        """Test cache_get returns None for missing values."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {}}}

        result = cache_get(hass, 33000, "192.168.1.100:502_1")
        assert result is None

    def test_cache_without_controller_key(self):
        """Test cache operations without controller key (backward compat)."""
        hass = MagicMock()
        hass.data = {DOMAIN: {VALUES: {}}}

        cache_save(hass, 33000, 100)
        value = cache_get(hass, 33000)

        assert value == 100


class TestMultiInverterSetup:
    """Test setup with multiple inverters."""

    def test_multiple_controllers_registered(self):
        """Test multiple controllers can be registered."""
        hass = MagicMock()
        hass.data = {DOMAIN: {CONTROLLER: {}}}

        controller1 = create_mock_controller(host="192.168.1.100", port=502, slave=1)
        controller2 = create_mock_controller(host="192.168.1.101", port=502, slave=1)
        controller3 = create_mock_controller(host="192.168.1.100", port=502, slave=2)

        set_controller(hass, controller1)
        set_controller(hass, controller2)
        set_controller(hass, controller3)

        assert len(hass.data[DOMAIN][CONTROLLER]) == 3
        assert "192.168.1.100:502_1" in hass.data[DOMAIN][CONTROLLER]
        assert "192.168.1.101:502_1" in hass.data[DOMAIN][CONTROLLER]
        assert "192.168.1.100:502_2" in hass.data[DOMAIN][CONTROLLER]

    def test_controller_lookup_by_host_slave(self):
        """Test finding controller by host and slave when multiple exist."""
        controller1 = create_mock_controller(host="192.168.1.100", slave=1)
        controller2 = create_mock_controller(host="192.168.1.100", slave=2)

        hass = MagicMock()
        hass.data = {DOMAIN: {CONTROLLER: {"192.168.1.100:502_1": controller1, "192.168.1.100:502_2": controller2}}}

        result1 = get_controller(hass, "192.168.1.100", 1)
        result2 = get_controller(hass, "192.168.1.100", 2)

        assert result1 is controller1
        assert result2 is controller2


class TestConnectionTypes:
    """Test different connection type handling."""

    def test_tcp_connection_id_format(self):
        """Test TCP connection ID includes port."""
        controller = create_mock_controller(host="192.168.1.100", port=8502)
        assert controller.connection_id == "192.168.1.100:8502"

    def test_serial_connection_id_format(self):
        """Test serial connection ID is the port path."""
        controller = MagicMock()
        controller.connection_id = "/dev/ttyUSB0"
        controller.device_id = 1
        key = get_controller_key(controller)
        assert key == "/dev/ttyUSB0_1"

    def test_config_auto_detects_connection_type(self):
        """Test connection type is auto-detected from config."""
        # TCP config (has host)
        tcp_config = {"host": "192.168.1.100", "slave": 1}
        tcp_key = get_controller_key_from_config(tcp_config)
        assert "192.168.1.100" in tcp_key

        # Serial config (no host, has serial_port)
        serial_config = {CONF_SERIAL_PORT: "/dev/ttyUSB0", "slave": 1, CONF_CONNECTION_TYPE: CONN_TYPE_SERIAL}
        serial_key = get_controller_key_from_config(serial_config)
        assert "/dev/ttyUSB0" in serial_key
