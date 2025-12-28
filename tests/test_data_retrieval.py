import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.sungrow_modbus.data.enums import PollSpeed
from custom_components.sungrow_modbus.data_retrieval import DataRetrieval
from custom_components.sungrow_modbus.sensors.sungrow_base_sensor import SungrowSensorGroup


class TestDataRetrieval(unittest.TestCase):
    """Test the DataRetrieval class."""

    def setUp(self):
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

        # Create sensor groups for testing
        self.fast_group = MagicMock(spec=SungrowSensorGroup)
        self.fast_group.poll_speed = PollSpeed.FAST
        self.fast_group.start_register = 1000
        self.fast_group.registrar_count = 10

        self.normal_group = MagicMock(spec=SungrowSensorGroup)
        self.normal_group.poll_speed = PollSpeed.NORMAL
        self.normal_group.start_register = 2000
        self.normal_group.registrar_count = 10

        self.slow_group = MagicMock(spec=SungrowSensorGroup)
        self.slow_group.poll_speed = PollSpeed.SLOW
        self.slow_group.start_register = 3000
        self.slow_group.registrar_count = 10

        self.once_group = MagicMock(spec=SungrowSensorGroup)
        self.once_group.poll_speed = PollSpeed.ONCE
        self.once_group.start_register = 4000
        self.once_group.registrar_count = 10

        # Set up the controller's sensor groups
        self.controller.sensor_groups = [self.fast_group, self.normal_group, self.slow_group, self.once_group]

        # Create the DataRetrieval instance
        with patch(
            "custom_components.sungrow_modbus.data_retrieval.async_track_time_interval"
        ) as self.mock_track_time:
            self.data_retrieval = DataRetrieval(self.hass, self.controller)

    async def test_check_connection_already_connected(self):
        """Test check_connection when already connected."""
        self.data_retrieval.connection_check = False
        self.controller.connected.return_value = True

        await self.data_retrieval.check_connection()

        self.hass.bus.async_fire.assert_called_once()
        self.controller.connected.assert_called_once()
        # Should not attempt to connect if already connected
        self.controller.connect.assert_not_called()

    async def test_check_connection_not_connected(self):
        """Test check_connection when not connected."""
        self.data_retrieval.connection_check = False
        self.controller.connected.return_value = False
        self.controller.connect = AsyncMock(return_value=True)

        await self.data_retrieval.check_connection()

        self.hass.bus.async_fire.assert_called_once()
        self.controller.connected.assert_called()
        self.controller.connect.assert_called_once()

    async def test_poll_controller(self):
        """Test poll_controller method."""
        # Mock the check_connection method
        self.data_retrieval.check_connection = AsyncMock()

        # Call the method
        await self.data_retrieval.poll_controller()

        # Verify check_connection was called
        self.data_retrieval.check_connection.assert_called_once()

        # Verify time interval tracking was set up
        self.assertEqual(3, self.mock_track_time.call_count)

        # Verify controller's process_write_queue was started
        self.hass.create_task.assert_called_once_with(self.controller.process_write_queue())

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

    async def test_modbus_update_fast(self):
        """Test modbus_update_fast method."""
        # Mock the get_modbus_updates method
        self.data_retrieval.get_modbus_updates = AsyncMock()

        # Call the method
        await self.data_retrieval.modbus_update_fast()

        # Verify get_modbus_updates was called with fast groups
        self.data_retrieval.get_modbus_updates.assert_called_once()
        args, kwargs = self.data_retrieval.get_modbus_updates.call_args
        self.assertEqual(PollSpeed.FAST, args[1])

        # Verify event was fired
        self.hass.bus.async_fire.assert_called_once()

    async def test_modbus_update_normal(self):
        """Test modbus_update_normal method."""
        # Mock the get_modbus_updates method
        self.data_retrieval.get_modbus_updates = AsyncMock()

        # Call the method
        await self.data_retrieval.modbus_update_normal()

        # Verify get_modbus_updates was called with normal groups
        self.data_retrieval.get_modbus_updates.assert_called_once()
        args, kwargs = self.data_retrieval.get_modbus_updates.call_args
        self.assertEqual(PollSpeed.NORMAL, args[1])

    async def test_modbus_update_slow(self):
        """Test modbus_update_slow method."""
        # Mock the get_modbus_updates method
        self.data_retrieval.get_modbus_updates = AsyncMock()

        # Call the method
        await self.data_retrieval.modbus_update_slow()

        # Verify get_modbus_updates was called with slow groups
        self.data_retrieval.get_modbus_updates.assert_called_once()
        args, kwargs = self.data_retrieval.get_modbus_updates.call_args
        self.assertEqual(PollSpeed.SLOW, args[1])

    async def test_get_modbus_updates_controller_disabled(self):
        """Test get_modbus_updates when controller is disabled."""
        self.controller.enabled = False

        await self.data_retrieval.get_modbus_updates([self.fast_group], PollSpeed.FAST)

        # Should return early without doing anything
        self.controller.async_read_holding_register.assert_not_called()
        self.controller.async_read_input_register.assert_not_called()

    async def test_get_modbus_updates_controller_not_connected(self):
        """Test get_modbus_updates when controller is not connected."""
        self.controller.enabled = True
        self.controller.connected.return_value = False

        await self.data_retrieval.get_modbus_updates([self.fast_group], PollSpeed.FAST)

        # Should return early without doing anything
        self.controller.async_read_holding_register.assert_not_called()
        self.controller.async_read_input_register.assert_not_called()

    async def test_get_modbus_updates_success(self):
        """Test successful get_modbus_updates."""
        # Set up the controller to return register values
        self.controller.async_read_holding_register = AsyncMock(return_value=[42, 43])
        self.controller.async_read_input_register = AsyncMock(return_value=[44, 45])

        # Call the method with a holding register group
        self.fast_group.start_register = 40000  # Holding register
        await self.data_retrieval.get_modbus_updates([self.fast_group], PollSpeed.FAST)

        # Verify the correct read method was called
        self.controller.async_read_holding_register.assert_called_once()
        self.controller.async_read_input_register.assert_not_called()

        # Call the method with an input register group
        self.controller.async_read_holding_register.reset_mock()
        self.controller.async_read_input_register.reset_mock()
        self.fast_group.start_register = 30000  # Input register
        await self.data_retrieval.get_modbus_updates([self.fast_group], PollSpeed.FAST)

        # Verify the correct read method was called
        self.controller.async_read_holding_register.assert_not_called()
        self.controller.async_read_input_register.assert_called_once()

        self.controller.async_read_input_register.assert_called_once()

    def test_spike_filtering(self):
        """Test spike filtering logic."""
        # Non-target register
        self.assertEqual(50, self.data_retrieval.spike_filtering(12345, 50))

        # Target register 33139
        reg = 33139

        # Initial non-spike
        self.assertEqual(50, self.data_retrieval.spike_filtering(reg, 50))

        # Spike check: value 0 should be ignored initially
        with patch("custom_components.sungrow_modbus.data_retrieval.cache_get", return_value=50):
            # 1st spike
            self.assertEqual(50, self.data_retrieval.spike_filtering(reg, 0))
            # 2nd spike
            self.assertEqual(50, self.data_retrieval.spike_filtering(reg, 0))
            # 3rd spike (accepted)
            self.assertEqual(0, self.data_retrieval.spike_filtering(reg, 0))

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

    async def test_remove_once_groups(self):
        """Test that ONCE groups are removed after updating."""
        self.once_group.poll_speed = PollSpeed.ONCE
        self.controller.sensor_groups = [self.once_group, self.normal_group]
        self.controller.enabled = True
        self.controller.connected.return_value = True
        self.controller.async_read_holding_register = AsyncMock(return_value=[1] * 10)
        self.controller.async_read_input_register = AsyncMock(return_value=[1] * 10)

        await self.data_retrieval.get_modbus_updates([self.once_group], PollSpeed.NORMAL)

        # Check if once_group is removed from controller.sensor_groups
        self.assertNotIn(self.once_group, self.controller.sensor_groups)
        self.assertIn(self.normal_group, self.controller.sensor_groups)


class TestDataRetrievalBatteryPolling(unittest.TestCase):
    """Test battery polling in DataRetrieval."""

    def setUp(self):
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

    async def test_poll_battery_stacks_no_entry_id(self):
        """Test poll_battery_stacks returns early when no entry_id."""
        with patch("custom_components.sungrow_modbus.data_retrieval.async_track_time_interval"):
            data_retrieval = DataRetrieval(self.hass, self.controller, entry_id=None)

        await data_retrieval.poll_battery_stacks()

        # Should return early without accessing hass.data
        # (no exception means it worked)

    async def test_poll_battery_stacks_no_battery_controllers(self):
        """Test poll_battery_stacks when no battery controllers exist."""
        from custom_components.sungrow_modbus.const import BATTERY_CONTROLLER, DOMAIN

        self.hass.data[DOMAIN] = {BATTERY_CONTROLLER: {}}

        with patch("custom_components.sungrow_modbus.data_retrieval.async_track_time_interval"):
            data_retrieval = DataRetrieval(self.hass, self.controller, entry_id="test_entry")

        await data_retrieval.poll_battery_stacks()

        # Should return early without error

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

    async def test_modbus_update_slow_calls_poll_battery_stacks(self):
        """Test that modbus_update_slow calls poll_battery_stacks."""
        with patch("custom_components.sungrow_modbus.data_retrieval.async_track_time_interval"):
            data_retrieval = DataRetrieval(self.hass, self.controller, entry_id="test_entry")

        data_retrieval.get_modbus_updates = AsyncMock()
        data_retrieval.poll_battery_stacks = AsyncMock()

        await data_retrieval.modbus_update_slow()

        # Verify poll_battery_stacks was called
        data_retrieval.poll_battery_stacks.assert_called_once()
