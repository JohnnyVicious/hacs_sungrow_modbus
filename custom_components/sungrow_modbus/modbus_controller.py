import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.template import is_number
from pymodbus.client import AsyncModbusSerialClient, AsyncModbusTcpClient
from pymodbus.exceptions import ConnectionException, ModbusException

from custom_components.sungrow_modbus.client_manager import ModbusClientManager
from custom_components.sungrow_modbus.const import (
    CONN_TYPE_TCP,
    CONTROLLER,
    DEFAULT_BAUDRATE,
    DEFAULT_BYTESIZE,
    DEFAULT_PARITY,
    DEFAULT_STOPBITS,
    DOMAIN,
    MANUFACTURER,
    REGISTER,
    SLAVE,
    VALUE,
)
from custom_components.sungrow_modbus.data.enums import PollSpeed
from custom_components.sungrow_modbus.data.sungrow_config import InverterConfig
from custom_components.sungrow_modbus.helpers import cache_save
from custom_components.sungrow_modbus.sensors.sungrow_base_sensor import SungrowSensorGroup
from custom_components.sungrow_modbus.sensors.sungrow_derived_sensor import SungrowDerivedSensor

_LOGGER = logging.getLogger(__name__)

# Write queue timing configuration
QUEUE_DISCONNECTED_SLEEP = 5.0  # Seconds to wait between queue checks when disconnected
QUEUE_EMPTY_SLEEP = 0.2  # Seconds to wait between queue checks when queue is empty

# Modbus inter-frame delay configuration (milliseconds)
# These delays ensure proper spacing between Modbus operations to avoid
# overwhelming the device. Write operations use longer delays for safety.
INTER_FRAME_DELAY_READ_MS = 50
INTER_FRAME_DELAY_WRITE_MS = 100

# Circuit breaker configuration
# Prevents repeated connection attempts to offline inverters
CIRCUIT_BREAKER_FAILURE_THRESHOLD = 5  # Open circuit after this many consecutive failures
CIRCUIT_BREAKER_RECOVERY_MINUTES = 5  # Wait this long before attempting recovery


class CircuitState(Enum):
    """States for the circuit breaker pattern."""

    CLOSED = "closed"  # Normal operation, connections allowed
    OPEN = "open"  # Circuit tripped, rejecting connection attempts
    HALF_OPEN = "half_open"  # Testing if service has recovered


@dataclass
class CircuitBreaker:
    """Circuit breaker to prevent repeated connection attempts to offline devices.

    The circuit breaker has three states:
    - CLOSED: Normal operation, all connection attempts are allowed
    - OPEN: Circuit is tripped after too many failures, rejecting attempts
    - HALF_OPEN: After recovery timeout, allows one attempt to test recovery

    Usage:
        breaker = CircuitBreaker()

        if breaker.can_attempt():
            success = await try_connect()
            if success:
                breaker.record_success()
            else:
                breaker.record_failure()
        else:
            # Skip connection attempt, circuit is open
            pass
    """

    failure_threshold: int = CIRCUIT_BREAKER_FAILURE_THRESHOLD
    recovery_timeout: timedelta = field(default_factory=lambda: timedelta(minutes=CIRCUIT_BREAKER_RECOVERY_MINUTES))

    state: CircuitState = field(default=CircuitState.CLOSED)
    failure_count: int = field(default=0)
    last_failure_time: datetime | None = field(default=None)
    _logger_prefix: str = field(default="")

    def record_success(self) -> None:
        """Record a successful connection attempt.

        Resets the circuit breaker to CLOSED state and clears failure count.
        """
        if self.state != CircuitState.CLOSED:
            _LOGGER.info(
                "%sCircuit breaker CLOSED after successful connection",
                self._logger_prefix,
            )
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.last_failure_time = None

    def record_failure(self) -> None:
        """Record a failed connection attempt.

        Increments failure count and opens the circuit if threshold is exceeded.
        """
        self.failure_count += 1
        self.last_failure_time = datetime.now(UTC)

        if self.state == CircuitState.HALF_OPEN:
            # Failed during recovery test, go back to OPEN
            self.state = CircuitState.OPEN
            _LOGGER.warning(
                "%sCircuit breaker OPEN (recovery attempt failed). Will retry in %s",
                self._logger_prefix,
                self.recovery_timeout,
            )
        elif self.failure_count >= self.failure_threshold and self.state == CircuitState.CLOSED:
            self.state = CircuitState.OPEN
            _LOGGER.warning(
                "%sCircuit breaker OPEN after %d consecutive failures. Will retry in %s",
                self._logger_prefix,
                self.failure_count,
                self.recovery_timeout,
            )

    def can_attempt(self) -> bool:
        """Check if a connection attempt is allowed.

        Returns:
            True if an attempt should be made, False if circuit is open.
        """
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self.last_failure_time is not None:
                elapsed = datetime.now(UTC) - self.last_failure_time
                if elapsed >= self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    _LOGGER.info(
                        "%sCircuit breaker HALF_OPEN, attempting recovery",
                        self._logger_prefix,
                    )
                    return True
            return False

        # HALF_OPEN state allows one attempt
        return True

    @property
    def is_open(self) -> bool:
        """Check if the circuit is currently open (rejecting attempts)."""
        return self.state == CircuitState.OPEN and not self.can_attempt()

    @property
    def time_until_retry(self) -> timedelta | None:
        """Get the time remaining until next retry is allowed.

        Returns:
            timedelta if circuit is open, None otherwise.
        """
        if self.state != CircuitState.OPEN or self.last_failure_time is None:
            return None

        elapsed = datetime.now(UTC) - self.last_failure_time
        remaining = self.recovery_timeout - elapsed
        return remaining if remaining > timedelta(0) else None


class ModbusController:
    def __init__(
        self,
        hass,
        inverter_config: InverterConfig,
        sensor_groups: list[SungrowSensorGroup] = None,
        derived_sensors: list[SungrowDerivedSensor] = None,
        device_id=1,
        fast_poll=5,
        normal_poll=15,
        slow_poll=30,
        connection_type=CONN_TYPE_TCP,
        # TCP parameters
        host=None,
        port=502,
        # Serial parameters
        serial_port=None,
        baudrate=DEFAULT_BAUDRATE,
        bytesize=DEFAULT_BYTESIZE,
        parity=DEFAULT_PARITY,
        stopbits=DEFAULT_STOPBITS,
        serial_number=None,
        firmware_version=None,
    ):
        """
        Initialize ModbusController with support for both TCP and Serial connections.

        Args:
            hass: Home Assistant instance
            inverter_config: Inverter configuration object
            connection_type: Either CONN_TYPE_TCP or CONN_TYPE_SERIAL

            TCP parameters:
                host: IP address or hostname for TCP connection
                port: Port number for TCP connection (default 502)

            Serial parameters:
                serial_port: Serial port path (e.g., /dev/ttyUSB0)
                baudrate: Serial baud rate (default 9600)
                bytesize: Number of data bits (default 8)
                parity: Parity setting - 'N', 'E', or 'O' (default 'N')
                stopbits: Number of stop bits (default 1)
        """
        self.hass = hass
        self.connection_type = connection_type
        self.device_id = device_id
        self.slave = device_id  # Alias for device_id
        self.serial_number = serial_number

        # Use ModbusClientManager to get shared client and lock
        manager = ModbusClientManager.get_instance()

        # Connection-specific setup
        if connection_type == CONN_TYPE_TCP:
            if not host:
                raise ValueError("host is required for TCP connection")
            self.host = host
            self.port = port
            self.connection_id = f"{host}:{port}"
            self.client: AsyncModbusTcpClient | AsyncModbusSerialClient = manager.get_tcp_client(host, port)
            self.poll_lock = manager.get_client_lock(self.connection_id)
        else:  # CONN_TYPE_SERIAL
            if not serial_port:
                raise ValueError("serial_port is required for Serial connection")
            self.serial_port = serial_port
            self.baudrate = baudrate
            self.bytesize = bytesize
            self.parity = parity
            self.stopbits = stopbits
            self.connection_id = serial_port
            # For serial, set host to serial_port for backwards compatibility with logging
            self.host = serial_port
            self.client: AsyncModbusTcpClient | AsyncModbusSerialClient = manager.get_serial_client(
                serial_port, baudrate, bytesize, parity, stopbits
            )
            self.poll_lock = manager.get_client_lock(self.connection_id)

        self.connect_failures = 0
        self._data_received = False
        self._poll_interval_fast = fast_poll
        self._poll_interval_normal = normal_poll
        self._poll_interval_slow = slow_poll
        self._model = inverter_config.model
        self.inverter_config = inverter_config
        self._sw_version = firmware_version or "N/A"
        self.enabled = True
        self._last_attempt = 0  # Track last connection attempt time
        self._sensor_groups = sensor_groups
        self._derived_sensors = derived_sensors
        # self.poll_lock = asyncio.Lock() # Replaced by shared lock from manager

        # Modbus Write Queue
        self.write_queue = asyncio.Queue()
        self._last_modbus_request = 0
        self._last_modbus_success = datetime.now(UTC)

        # Controller key for cache namespacing (includes port/path + slave)
        self.controller_key = f"{self.connection_id}_{self.device_id}"

        # Circuit breaker for connection management
        self.circuit_breaker = CircuitBreaker(
            _logger_prefix=f"({self.host}.{self.device_id}) ",
        )

    async def process_write_queue(self):
        """Process queued Modbus write requests sequentially.

        This method runs in a loop, processing write requests from the queue.
        It ensures that write operations are executed one at a time, with appropriate
        delays between operations to avoid overwhelming the Modbus device.

        Each queue item is a 4-tuple: (register, value, multiple, future)
        The future is resolved with the write result when the operation completes.

        The loop exits gracefully when cancelled, processing any pending writes first.

        Returns:
            None
        """
        try:
            while True:
                if not self.connected():
                    await asyncio.sleep(QUEUE_DISCONNECTED_SLEEP)
                    continue

                if self.write_queue.empty():
                    await asyncio.sleep(QUEUE_EMPTY_SLEEP)
                    continue

                write_request = await self.write_queue.get()
                register, value, multiple, future = write_request

                if multiple:
                    result = await self._execute_write_holding_registers(register, value)
                else:
                    result = await self._execute_write_holding_register(register, value)

                # Resolve the future with the result (success or None on failure)
                if not future.done():
                    future.set_result(result)

                self.write_queue.task_done()
        except asyncio.CancelledError:
            _LOGGER.debug(f"({self.host}.{self.device_id}) Write queue processor cancelled, draining pending writes")
            # Process any remaining items in the queue before exiting
            while not self.write_queue.empty():
                try:
                    write_request = self.write_queue.get_nowait()
                    register, value, multiple, future = write_request
                    if multiple:
                        result = await self._execute_write_holding_registers(register, value)
                    else:
                        result = await self._execute_write_holding_register(register, value)
                    # Resolve the future with the result
                    if not future.done():
                        future.set_result(result)
                    self.write_queue.task_done()
                except asyncio.QueueEmpty:
                    break
                except ConnectionException as e:
                    _LOGGER.warning(f"({self.host}.{self.device_id}) Connection lost during shutdown write: {e}")
                except ModbusException as e:
                    _LOGGER.warning(f"({self.host}.{self.device_id}) Modbus error during shutdown write: {e}")
                except Exception as e:
                    _LOGGER.error(
                        f"({self.host}.{self.device_id}) Unexpected error during shutdown write: {e}",
                        exc_info=True,
                    )
            raise  # Re-raise CancelledError for proper cleanup

    async def _execute_write_holding_register(self, register, value):
        """Executes a single register write with interframe delay.

        Args:
            register (int): The register address to write to.
            value (int): The value to write to the register.

        Returns:
            result: The result of the write operation, or None if an error occurred.

        Raises:
            Exception: If there is an error during the write operation.
        """
        try:
            if not await self.connect():
                _LOGGER.debug(f"({self.host}.{self.device_id}) Skipping write to register {register} - not connected")
                return None
            async with self.poll_lock:
                await self.inter_frame_wait(is_write=True)  # Delay before write
                int_value = int(value)
                int_register = register if is_number(register) else int(register)

                result = await self.client.write_register(
                    address=int_register, value=int_value, device_id=self.device_id
                )
                _LOGGER.debug(
                    f"({self.host}.{self.device_id}) Write Holding Register register = {int_register}, value = {value}, int_value = {int_value}: {result}"
                )

                if result.isError():
                    _LOGGER.error(
                        f"({self.host}.{self.device_id}) Failed to write holding register {register} with value {value}: {result}"
                    )
                    return None

                # Write response has .value (single) not .registers
                written_value = getattr(result, "value", int_value)
                cache_save(self.hass, int_register, written_value, self.controller_key)
                self.hass.bus.async_fire(
                    DOMAIN,
                    {
                        REGISTER: int_register,
                        VALUE: written_value,
                        CONTROLLER: self.connection_id,
                        SLAVE: self.device_id,
                    },
                )

                return result
        except asyncio.CancelledError:
            raise  # Never swallow cancellation
        except ConnectionException as e:
            _LOGGER.warning(f"({self.host}.{self.device_id}) Connection lost writing register {register}: {e}")
            return None
        except ModbusException as e:
            _LOGGER.error(f"({self.host}.{self.device_id}) Modbus error writing register {register}: {e}")
            return None
        except Exception as e:
            _LOGGER.error(
                f"({self.host}.{self.device_id}) Unexpected error writing register {register}: {e}",
                exc_info=True,
            )
            return None

    async def _execute_write_holding_registers(self, start_register, values):
        """Executes a multiple register write.

        Args:
            start_register (int): The starting register address to write to.
            values (list): A list of values to write to consecutive registers.

        Returns:
            result: The result of the write operation, or None if an error occurred.

        Raises:
            Exception: If there is an error during the write operation.
        """
        try:
            if not await self.connect():
                _LOGGER.debug(
                    f"({self.host}.{self.device_id}) Skipping write to registers {start_register}-{start_register + len(values) - 1} - not connected"
                )
                return None
            async with self.poll_lock:
                await self.inter_frame_wait(is_write=True)  # Delay before write

                result = await self.client.write_registers(
                    address=start_register, values=values, device_id=self.device_id
                )
                _LOGGER.debug(
                    f"({self.host}.{self.device_id}) Write Holding Register block for {len(values)} registers starting at register = {start_register}"
                )

                if result.isError():
                    _LOGGER.error(f"({self.host}.{self.device_id}) Write block failed: {result}")
                    return None

                for i, value in enumerate(values):
                    cache_save(self.hass, start_register + i, value, self.controller_key)
                    self.hass.bus.async_fire(
                        DOMAIN,
                        {
                            REGISTER: start_register + i,
                            VALUE: value,
                            CONTROLLER: self.connection_id,
                            SLAVE: self.device_id,
                        },
                    )
                return result
        except asyncio.CancelledError:
            raise  # Never swallow cancellation
        except ConnectionException as e:
            _LOGGER.warning(
                f"({self.host}.{self.device_id}) Connection lost writing registers {start_register}-{start_register + len(values) - 1}: {e}"
            )
            return None
        except ModbusException as e:
            _LOGGER.error(
                f"({self.host}.{self.device_id}) Modbus error writing registers {start_register}-{start_register + len(values) - 1}: {e}"
            )
            return None
        except Exception as e:
            _LOGGER.error(
                f"({self.host}.{self.device_id}) Unexpected error writing registers {start_register}-{start_register + len(values) - 1}: {e}",
                exc_info=True,
            )
            return None

    async def async_write_holding_register(self, register, value):
        """Queues a write request and waits for completion.

        Args:
            register (int): The register address to write to.
            value (int): The value to write to the register.

        Returns:
            The write result on success, or None on failure.
        """
        future = asyncio.get_event_loop().create_future()
        await self.write_queue.put((register, value, False, future))
        return await future

    async def async_write_holding_registers(self, start_register, values):
        """Queues a write request and waits for completion.

        Args:
            start_register (int): The starting register address to write to.
            values (list): A list of values to write to consecutive registers.

        Returns:
            The write result on success, or None on failure.
        """
        future = asyncio.get_event_loop().create_future()
        await self.write_queue.put((start_register, values, True, future))
        return await future

    async def inter_frame_wait(self, is_write=False):
        """Implements inter-frame delay to respect Modbus timing requirements.

        This method calculates the time since the last Modbus request and adds
        a delay if necessary to ensure proper spacing between operations.

        Args:
            is_write (bool): If True, uses a longer delay for write operations.

        Returns:
            None
        """
        delay_ms = INTER_FRAME_DELAY_WRITE_MS if is_write else INTER_FRAME_DELAY_READ_MS

        current_time = time.perf_counter()
        elapsed = (current_time - self._last_modbus_request) * 1000  # Convert to ms

        if elapsed < delay_ms:
            sleep_time = (delay_ms - elapsed) / 1000
            await asyncio.sleep(sleep_time)

        self._last_modbus_request = time.perf_counter()

    async def _async_read_input_register_raw(self, register, count):
        """Raw read input registers without connection check (internal use)."""
        async with self.poll_lock:
            await self.inter_frame_wait()

            result = await self.client.read_input_registers(address=register, count=count, device_id=self.device_id)

            _LOGGER.debug(
                f"({self.host}.{self.device_id}) Read Input Registers: register = {register}, count = {count}"
            )

            if result.isError():
                _LOGGER.error(
                    f"({self.host}.{self.device_id}) Failed to read input registers starting at {register}: {result}"
                )
                return None

            self._last_modbus_success = datetime.now(UTC)
            return result.registers

    async def async_read_input_register(self, register, count):
        """Reads input registers from the Modbus device.

        Args:
            register (int): The starting register address to read from.
            count (int): The number of registers to read.

        Returns:
            list: A list of register values if successful, or None if an error occurred.

        Raises:
            Exception: If there is an error during the read operation.
        """
        try:
            if not await self.connect():
                _LOGGER.debug(
                    f"({self.host}.{self.device_id}) Skipping read of input registers {register}-{register + count - 1} - not connected"
                )
                return None
            return await self._async_read_input_register_raw(register, count)
        except asyncio.CancelledError:
            raise  # Never swallow cancellation
        except ConnectionException as e:
            _LOGGER.warning(
                f"({self.host}.{self.device_id}) Connection lost reading input registers {register}-{register + count - 1}: {e}"
            )
            return None
        except ModbusException as e:
            _LOGGER.error(
                f"({self.host}.{self.device_id}) Modbus error reading input registers {register}-{register + count - 1}: {e}"
            )
            return None
        except Exception as e:
            _LOGGER.error(
                f"({self.host}.{self.device_id}) Unexpected error reading input registers {register}-{register + count - 1}: {e}",
                exc_info=True,
            )
            return None

    async def async_read_holding_register(self, register, count):
        """Reads holding registers from the Modbus device.

        Args:
            register (int): The starting register address to read from.
            count (int): The number of registers to read.

        Returns:
            list: A list of register values if successful, or None if an error occurred.

        Raises:
            Exception: If there is an error during the read operation.
        """
        try:
            if not await self.connect():
                _LOGGER.debug(
                    f"({self.host}.{self.device_id}) Skipping read of holding registers {register}-{register + count - 1} - not connected"
                )
                return None
            async with self.poll_lock:
                await self.inter_frame_wait()

                result = await self.client.read_holding_registers(
                    address=register, count=count, device_id=self.device_id
                )

                _LOGGER.debug(
                    f"({self.host}.{self.device_id}) Read Holding Registers: register = {register}, count = {count}"
                )

                if result.isError():
                    _LOGGER.error(
                        f"({self.host}.{self.device_id}) Failed to read holding registers starting at {register}: {result}"
                    )
                    return None

                self._last_modbus_success = datetime.now(UTC)
                return result.registers
        except asyncio.CancelledError:
            raise  # Never swallow cancellation
        except ConnectionException as e:
            _LOGGER.warning(
                f"({self.host}.{self.device_id}) Connection lost reading holding registers {register}-{register + count - 1}: {e}"
            )
            return None
        except ModbusException as e:
            _LOGGER.error(
                f"({self.host}.{self.device_id}) Modbus error reading holding registers {register}-{register + count - 1}: {e}"
            )
            return None
        except Exception as e:
            _LOGGER.error(
                f"({self.host}.{self.device_id}) Unexpected error reading holding registers {register}-{register + count - 1}: {e}",
                exc_info=True,
            )
            return None

    async def connect(self):
        """Establishes a connection to the Modbus device.

        Uses circuit breaker pattern to prevent repeated connection attempts
        to offline devices. When the circuit is open, connection attempts are
        rejected until the recovery timeout expires.

        Returns:
            bool: True if the connection was successful or already established, False otherwise.
            Returns False immediately if circuit breaker is open.

        Raises:
            Exception: If there is an error during the connection attempt.
        """
        if self.connected():
            return True

        # Check circuit breaker before attempting connection
        if not self.circuit_breaker.can_attempt():
            remaining = self.circuit_breaker.time_until_retry
            if remaining:
                _LOGGER.debug(
                    f"({self.host}.{self.device_id}) Connection blocked by circuit breaker. "
                    f"Retry in {remaining.total_seconds():.0f}s"
                )
            return False

        try:
            await self.client.connect()
            if self.connected():
                _LOGGER.info(f"({self.host}.{self.device_id}) Connected to Modbus device")
                self.connect_failures = 0
                self.circuit_breaker.record_success()

                if self.serial_number is None:
                    _LOGGER.info(f"serial got from device: {self.serial_number}")
                else:
                    _LOGGER.info(f"serial got from cache: {self.serial_number}")

                return True
            else:
                self.connect_failures += 1
                self.circuit_breaker.record_failure()
                _LOGGER.debug(
                    f"({self.connection_id}.{self.device_id}) Connection attempt {self.connect_failures} failed"
                )
                return False
        except asyncio.CancelledError:
            raise  # Never swallow cancellation
        except ConnectionException as e:
            self.connect_failures += 1
            self.circuit_breaker.record_failure()
            _LOGGER.debug(
                f"({self.connection_id}.{self.device_id}) Connection failed (attempt {self.connect_failures}): {e}"
            )
            return False
        except OSError as e:
            # Network-level errors (connection refused, timeout, etc.)
            self.connect_failures += 1
            self.circuit_breaker.record_failure()
            _LOGGER.debug(
                f"({self.connection_id}.{self.device_id}) Network error (attempt {self.connect_failures}): {e}"
            )
            return False
        except Exception as e:
            self.connect_failures += 1
            self.circuit_breaker.record_failure()
            _LOGGER.warning(
                f"({self.connection_id}.{self.device_id}) Unexpected connection error (attempt {self.connect_failures}): {e}",
                exc_info=True,
            )
            return False

    def connected(self):
        """Checks if the Modbus client is currently connected.

        Returns:
            bool: True if the client is connected, False otherwise.
        """
        return self.client.connected if self.client else False

    def disable_connection(self):
        """Disables the Modbus connection.

        This method sets the enabled flag to False, which will cause future
        read/write operations to be skipped.

        Returns:
            None
        """
        self.enabled = False
        _LOGGER.info(f"({self.host}.{self.device_id}) Modbus connection disabled")

    def enable_connection(self):
        """Enables the Modbus connection.

        This method sets the enabled flag to True, allowing read/write operations
        to proceed normally.

        Returns:
            None
        """
        self.enabled = True
        _LOGGER.info(f"({self.host}.{self.device_id}) Modbus connection enabled")

    def close_connection(self):
        """Closes the Modbus connection and releases the client from the manager.

        This method releases the client reference in the ModbusClientManager.
        When all references are released, the manager will close the actual connection.

        Returns:
            None
        """
        manager = ModbusClientManager.get_instance()
        manager.release_client(self.connection_id)
        _LOGGER.info(f"({self.host}.{self.device_id}) Modbus connection closed")

    @property
    def model(self):
        """Returns the inverter model."""
        return self._model

    @property
    def poll_speed(self):
        """Returns a dictionary of poll intervals for different speed categories."""
        return {
            PollSpeed.FAST: self._poll_interval_fast,
            PollSpeed.NORMAL: self._poll_interval_normal,
            PollSpeed.SLOW: self._poll_interval_slow,
        }

    @property
    def sw_version(self):
        """Returns the software version of the inverter."""
        return self._sw_version

    def set_sw_version(self, version: str) -> None:
        """Set the software/protocol version of the inverter."""
        self._sw_version = version

    def set_model(self, model: str) -> None:
        """Set the model description of the inverter."""
        self._model = model

    @property
    def sensor_groups(self):
        """Returns the list of sensor groups."""
        return self._sensor_groups

    @property
    def data_received(self):
        """Returns whether any data has been received from the device."""
        return self._data_received

    def mark_data_received(self):
        """Mark that data has been successfully received from the device."""
        self._data_received = True

    def remove_sensor_groups(self, groups_to_remove: list):
        """Remove sensor groups from the controller.

        Args:
            groups_to_remove: List of SungrowSensorGroup instances to remove.
        """
        self._sensor_groups = [g for g in self._sensor_groups if g not in groups_to_remove]

    @property
    def derived_sensors(self):
        """Returns the list of derived sensors."""
        return self._derived_sensors

    @property
    def sensor_derived_groups(self):
        """Gets the derived sensor groups associated with this controller."""
        return self._derived_sensors

    @property
    def last_modbus_request(self):
        """Gets the timestamp of the last Modbus request.

        Returns:
            float: The timestamp of the last Modbus request (from time.monotonic()).
        """
        return self._last_modbus_request

    @property
    def last_modbus_success(self):
        """Returns the timestamp of the last successful Modbus operation."""
        return self._last_modbus_success

    @property
    def device_serial_number(self):
        """Gets the device serial number."""
        return self.serial_number

    @property
    def device_info(self):
        """Return device info."""
        # Include serial number in device name for unique entity IDs when multiple inverters exist
        name = f"{MANUFACTURER} {self.model} {self.serial_number}"

        return DeviceInfo(
            identifiers={(DOMAIN, self.serial_number)},
            manufacturer=MANUFACTURER,
            model=self.model,
            serial_number=self.serial_number,
            name=name,
            sw_version=self.sw_version,
        )
