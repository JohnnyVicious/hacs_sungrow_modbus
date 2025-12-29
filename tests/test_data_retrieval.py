from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.sungrow_modbus.data.enums import PollSpeed
from custom_components.sungrow_modbus.data_retrieval import DataRetrieval
from custom_components.sungrow_modbus.sensors.sungrow_base_sensor import SungrowSensorGroup


class TestDataRetrieval:
    """Test the DataRetrieval class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock Home Assistant
        self.hass = MagicMock()
        self.hass.is_running = True
        self.hass.bus.async_fire = MagicMock()
        self.hass.create_task = MagicMock()

        # Mock the ModbusController
        self.controller = MagicMock()
        self.controller.host = "192.168.1.100"
        self.controller.slave = 1
        self.controller.enabled = True
        self.controller.connected = MagicMock(return_value=True)
        self.controller.poll_speed = {PollSpeed.FAST: 5, PollSpeed.NORMAL: 15, PollSpeed.SLOW: 30}

        # Mock the circuit breaker
        self.controller.circuit_breaker = MagicMock()
        self.controller.circuit_breaker.is_open = False
        self.controller.circuit_breaker.can_attempt = MagicMock(return_value=True)
        self.controller.circuit_breaker.time_until_retry = None

        # Create sensor groups for testing
        self.fast_group = MagicMock(spec=SungrowSensorGroup)
        self.fast_group.poll_speed = PollSpeed.FAST
        self.fast_group.start_register = 1000
        self.fast_group.registrar_count = 10
        self.fast_group.cache_ttl = None  # No TTL caching
        self.fast_group.is_holding = False

        self.normal_group = MagicMock(spec=SungrowSensorGroup)
        self.normal_group.poll_speed = PollSpeed.NORMAL
        self.normal_group.start_register = 2000
        self.normal_group.registrar_count = 10
        self.normal_group.cache_ttl = None  # No TTL caching
        self.normal_group.is_holding = False

        self.slow_group = MagicMock(spec=SungrowSensorGroup)
        self.slow_group.poll_speed = PollSpeed.SLOW
        self.slow_group.start_register = 3000
        self.slow_group.registrar_count = 10
        self.slow_group.cache_ttl = None  # No TTL caching
        self.slow_group.is_holding = False

        self.once_group = MagicMock(spec=SungrowSensorGroup)
        self.once_group.poll_speed = PollSpeed.ONCE
        self.once_group.start_register = 4000
        self.once_group.registrar_count = 10
        self.once_group.cache_ttl = None  # No TTL caching
        self.once_group.is_holding = False

        # Set up the controller's sensor groups
        self.controller.sensor_groups = [self.fast_group, self.normal_group, self.slow_group, self.once_group]

        # Create the DataRetrieval instance with patched time tracking
        self.track_time_patcher = patch("custom_components.sungrow_modbus.data_retrieval.async_track_time_interval")
        self.mock_track_time = self.track_time_patcher.start()
        self.data_retrieval = DataRetrieval(self.hass, self.controller)

    def teardown_method(self):
        """Tear down test fixtures."""
        self.track_time_patcher.stop()

    @pytest.mark.asyncio
    async def test_check_connection_already_connected(self):
        """Test check_connection when already connected."""
        self.data_retrieval.connection_check = False
        self.controller.connected.return_value = True

        await self.data_retrieval.check_connection()

        # Should fire event for connection status
        self.hass.bus.async_fire.assert_called()
        self.controller.connected.assert_called()
        # Should not attempt to connect if already connected
        self.controller.connect.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_connection_not_connected(self):
        """Test check_connection when not connected."""
        self.data_retrieval.connection_check = False
        self.controller.connected.return_value = False
        self.controller.connect = AsyncMock(return_value=True)

        await self.data_retrieval.check_connection()

        self.hass.bus.async_fire.assert_called_once()
        self.controller.connected.assert_called()
        self.controller.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_poll_controller(self):
        """Test poll_controller method."""
        # Mock the check_connection method
        self.data_retrieval.check_connection = AsyncMock()

        # Call the method
        await self.data_retrieval.poll_controller()

        # Verify check_connection was called
        self.data_retrieval.check_connection.assert_called_once()

        # Verify time interval tracking was set up (3 intervals for fast/normal/slow)
        assert self.mock_track_time.call_count >= 3

        # Verify controller's process_write_queue was started
        self.hass.create_task.assert_called()

    @pytest.mark.asyncio
    async def test_modbus_update_all(self):
        """Test modbus_update_all method."""
        # Mock the update methods
        self.data_retrieval.modbus_update_fast = AsyncMock()
        self.data_retrieval.modbus_update_normal = AsyncMock()
        self.data_retrieval.modbus_update_slow = AsyncMock()

        # Call the method
        await self.data_retrieval.modbus_update_all()

        # Verify all update methods were called
        self.data_retrieval.modbus_update_fast.assert_called_once()
        self.data_retrieval.modbus_update_normal.assert_called_once()
        self.data_retrieval.modbus_update_slow.assert_called_once()

    @pytest.mark.asyncio
    async def test_modbus_update_fast(self):
        """Test modbus_update_fast method."""
        # Mock the get_modbus_updates method
        self.data_retrieval.get_modbus_updates = AsyncMock()

        # Call the method
        await self.data_retrieval.modbus_update_fast()

        # Verify get_modbus_updates was called with fast groups
        self.data_retrieval.get_modbus_updates.assert_called_once()
        args, kwargs = self.data_retrieval.get_modbus_updates.call_args
        assert args[1] == PollSpeed.FAST

        # Verify event was fired
        self.hass.bus.async_fire.assert_called_once()

    @pytest.mark.asyncio
    async def test_modbus_update_normal(self):
        """Test modbus_update_normal method."""
        # Mock the get_modbus_updates method
        self.data_retrieval.get_modbus_updates = AsyncMock()

        # Call the method
        await self.data_retrieval.modbus_update_normal()

        # Verify get_modbus_updates was called with normal groups
        self.data_retrieval.get_modbus_updates.assert_called_once()
        args, kwargs = self.data_retrieval.get_modbus_updates.call_args
        assert args[1] == PollSpeed.NORMAL

    @pytest.mark.asyncio
    async def test_modbus_update_slow(self):
        """Test modbus_update_slow method."""
        # Mock the get_modbus_updates method
        self.data_retrieval.get_modbus_updates = AsyncMock()

        # Call the method
        await self.data_retrieval.modbus_update_slow()

        # Verify get_modbus_updates was called with slow groups
        self.data_retrieval.get_modbus_updates.assert_called_once()
        args, kwargs = self.data_retrieval.get_modbus_updates.call_args
        assert args[1] == PollSpeed.SLOW

    @pytest.mark.asyncio
    async def test_get_modbus_updates_controller_disabled(self):
        """Test get_modbus_updates when controller is disabled."""
        self.controller.enabled = False

        await self.data_retrieval.get_modbus_updates([self.fast_group], PollSpeed.FAST)

        # Should return early without doing anything
        self.controller.async_read_holding_register.assert_not_called()
        self.controller.async_read_input_register.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_modbus_updates_controller_not_connected(self):
        """Test get_modbus_updates when controller is not connected."""
        self.controller.enabled = True
        self.controller.connected.return_value = False

        await self.data_retrieval.get_modbus_updates([self.fast_group], PollSpeed.FAST)

        # Should return early without doing anything
        self.controller.async_read_holding_register.assert_not_called()
        self.controller.async_read_input_register.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_modbus_updates_success(self):
        """Test successful get_modbus_updates reads registers."""
        # Set up the controller to return register values
        self.controller.async_read_holding_register = AsyncMock(return_value=[42] * 10)
        self.controller.async_read_input_register = AsyncMock(return_value=[44] * 10)

        # Call the method - it should attempt to read registers
        self.fast_group.start_register = 5000  # Input register range
        self.fast_group.registrar_count = 10
        await self.data_retrieval.get_modbus_updates([self.fast_group], PollSpeed.FAST)

        # Verify a read method was called (either input or holding depending on register)
        total_calls = (
            self.controller.async_read_holding_register.call_count
            + self.controller.async_read_input_register.call_count
        )
        assert total_calls > 0, "Expected at least one register read"

    def test_spike_filtering(self):
        """Test spike filtering logic."""
        # Non-target register
        assert self.data_retrieval.spike_filtering(12345, 50) == 50

        # Target register 33139
        reg = 33139

        # Initial non-spike
        assert self.data_retrieval.spike_filtering(reg, 50) == 50

        # Spike check: value 0 should be ignored initially
        with patch("custom_components.sungrow_modbus.data_retrieval.cache_get", return_value=50):
            # 1st spike
            assert self.data_retrieval.spike_filtering(reg, 0) == 50
            # 2nd spike
            assert self.data_retrieval.spike_filtering(reg, 0) == 50
            # 3rd spike (accepted)
            assert self.data_retrieval.spike_filtering(reg, 0) == 0

    @pytest.mark.asyncio
    async def test_concurrency_lock(self):
        """Test that get_modbus_updates respects concurrency."""
        # Manually set the group hash in poll_updating
        groups = [self.fast_group]
        group_hash = frozenset({g.start_register for g in groups})

        self.data_retrieval.poll_updating[PollSpeed.FAST][group_hash] = True

        await self.data_retrieval.get_modbus_updates(groups, PollSpeed.FAST)

        # Should return early
        self.controller.async_read_holding_register.assert_not_called()
        self.controller.async_read_input_register.assert_not_called()

    @pytest.mark.asyncio
    async def test_remove_once_groups(self):
        """Test that ONCE groups are removed after updating."""
        # Create fresh groups for this test to avoid interference
        once_group = MagicMock(spec=SungrowSensorGroup)
        once_group.poll_speed = PollSpeed.ONCE
        once_group.start_register = 4000
        once_group.registrar_count = 10
        once_group.cache_ttl = None  # No TTL caching
        once_group.is_holding = False

        normal_group = MagicMock(spec=SungrowSensorGroup)
        normal_group.poll_speed = PollSpeed.NORMAL
        normal_group.start_register = 2000
        normal_group.registrar_count = 10
        normal_group.cache_ttl = None  # No TTL caching
        normal_group.is_holding = False

        # Use a real list for sensor_groups (the implementation reads sensor_groups
        # but uses remove_sensor_groups() method, so we need to track calls)
        sensor_groups_list = [once_group, normal_group]
        self.controller.sensor_groups = sensor_groups_list
        self.controller.enabled = True
        self.controller.connected.return_value = True
        self.controller.async_read_holding_register = AsyncMock(return_value=[1] * 10)
        self.controller.async_read_input_register = AsyncMock(return_value=[1] * 10)
        self.controller.mark_data_received = MagicMock()
        self.controller.remove_sensor_groups = MagicMock()

        await self.data_retrieval.get_modbus_updates([once_group], PollSpeed.NORMAL)

        # The implementation calls remove_sensor_groups() to remove ONCE groups
        # Verify that remove_sensor_groups was called with the once_group
        self.controller.remove_sensor_groups.assert_called_once()
        removed_groups = self.controller.remove_sensor_groups.call_args[0][0]
        assert once_group in removed_groups
        assert normal_group not in removed_groups


class TestDataRetrievalBatteryPolling:
    """Test battery polling in DataRetrieval."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock Home Assistant
        self.hass = MagicMock()
        self.hass.is_running = True
        self.hass.bus.async_fire = MagicMock()
        self.hass.create_task = MagicMock()
        self.hass.data = {}

        # Mock the ModbusController
        self.controller = MagicMock()
        self.controller.host = "192.168.1.100"
        self.controller.slave = 1
        self.controller.enabled = True
        self.controller.connected = MagicMock(return_value=True)
        self.controller.sensor_groups = []
        self.controller.poll_speed = {PollSpeed.FAST: 5, PollSpeed.NORMAL: 15, PollSpeed.SLOW: 30}

    @pytest.mark.asyncio
    async def test_poll_battery_stacks_no_entry_id(self):
        """Test poll_battery_stacks returns early when no entry_id."""
        with patch("custom_components.sungrow_modbus.data_retrieval.async_track_time_interval"):
            data_retrieval = DataRetrieval(self.hass, self.controller, entry_id=None)

        await data_retrieval.poll_battery_stacks()

        # Should return early without accessing hass.data
        # (no exception means it worked)

    @pytest.mark.asyncio
    async def test_poll_battery_stacks_no_battery_controllers(self):
        """Test poll_battery_stacks when no battery controllers exist."""
        from custom_components.sungrow_modbus.const import BATTERY_CONTROLLER, DOMAIN

        self.hass.data[DOMAIN] = {BATTERY_CONTROLLER: {}}

        with patch("custom_components.sungrow_modbus.data_retrieval.async_track_time_interval"):
            data_retrieval = DataRetrieval(self.hass, self.controller, entry_id="test_entry")

        await data_retrieval.poll_battery_stacks()

        # Should return early without error

    @pytest.mark.asyncio
    async def test_poll_battery_stacks_success(self):
        """Test successful battery polling."""
        from custom_components.sungrow_modbus.const import BATTERY_CONTROLLER, BATTERY_SENSORS, DOMAIN

        # Create mock battery controller
        mock_battery_controller = MagicMock()
        mock_battery_controller.stack_index = 0
        mock_battery_controller.read_status = AsyncMock(
            return_value={"voltage": 51.2, "current": -5.0, "soc": 85.5, "temperature": 25.0}
        )

        # Create mock battery sensor
        mock_sensor = MagicMock()
        mock_sensor._stack_index = 0
        mock_sensor.update_from_battery_data = MagicMock()

        self.hass.data[DOMAIN] = {
            BATTERY_CONTROLLER: {"test_entry": [mock_battery_controller]},
            BATTERY_SENSORS: {"test_entry": [mock_sensor]},
        }

        with patch("custom_components.sungrow_modbus.data_retrieval.async_track_time_interval"):
            data_retrieval = DataRetrieval(self.hass, self.controller, entry_id="test_entry")

        await data_retrieval.poll_battery_stacks()

        # Verify battery controller was polled
        mock_battery_controller.read_status.assert_called_once()
        # Verify sensor was updated
        mock_sensor.update_from_battery_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_poll_battery_stacks_exception_handling(self):
        """Test poll_battery_stacks handles exceptions gracefully."""
        from custom_components.sungrow_modbus.const import BATTERY_CONTROLLER, BATTERY_SENSORS, DOMAIN

        # Create mock battery controller that raises exception
        mock_battery_controller = MagicMock()
        mock_battery_controller.stack_index = 0
        mock_battery_controller.read_status = AsyncMock(side_effect=Exception("Connection failed"))

        self.hass.data[DOMAIN] = {
            BATTERY_CONTROLLER: {"test_entry": [mock_battery_controller]},
            BATTERY_SENSORS: {"test_entry": []},
        }

        with patch("custom_components.sungrow_modbus.data_retrieval.async_track_time_interval"):
            data_retrieval = DataRetrieval(self.hass, self.controller, entry_id="test_entry")

        # Should not raise exception
        await data_retrieval.poll_battery_stacks()

    @pytest.mark.asyncio
    async def test_modbus_update_slow_calls_poll_battery_stacks(self):
        """Test that modbus_update_slow calls poll_battery_stacks."""
        with patch("custom_components.sungrow_modbus.data_retrieval.async_track_time_interval"):
            data_retrieval = DataRetrieval(self.hass, self.controller, entry_id="test_entry")

        data_retrieval.get_modbus_updates = AsyncMock()
        data_retrieval.poll_battery_stacks = AsyncMock()

        await data_retrieval.modbus_update_slow()

        # Verify poll_battery_stacks was called
        data_retrieval.poll_battery_stacks.assert_called_once()
