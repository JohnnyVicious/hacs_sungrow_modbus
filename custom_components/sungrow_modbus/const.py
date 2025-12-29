DOMAIN = "sungrow_modbus"
CONTROLLER = "modbus_controller"
SLAVE = "modbus_controller_slave"
MANUFACTURER = "Sungrow"

VALUES = "values"
VALUE = "value"
REGISTER = "register"
REGISTER_CACHE = "register_cache"
SENSOR_ENTITIES = "sensor_entities"
TIME_ENTITIES = "time_entities"
SWITCH_ENTITIES = "switch_entities"
NUMBER_ENTITIES = "number_entities"
SENSOR_DERIVED_ENTITIES = "sensor_derived_entities"
DRIFT_COUNTER = "drift_counter"
ENTITIES = "entities"

# Connection types
CONN_TYPE_TCP = "tcp"
CONN_TYPE_SERIAL = "serial"

# Serial connection parameters
CONF_SERIAL_PORT = "serial_port"
CONF_BAUDRATE = "baudrate"
CONF_BYTESIZE = "bytesize"
CONF_PARITY = "parity"
CONF_STOPBITS = "stopbits"
CONF_CONNECTION_TYPE = "connection_type"
CONF_INVERTER_SERIAL = "inverter_serial"

# Default serial values (standard for Sungrow inverters)
DEFAULT_BAUDRATE = 9600
DEFAULT_BYTESIZE = 8
DEFAULT_PARITY = "N"
DEFAULT_STOPBITS = 1

# Multi-battery support
CONF_MULTI_BATTERY = "multi_battery"
BATTERY_SLAVE_BASE = 200  # Battery stacks use slave IDs 200, 201, 202, 203
MAX_BATTERY_STACKS = 4
BATTERY_ENTITIES = "battery_entities"
BATTERY_SENSORS = "battery_sensors"
BATTERY_CONTROLLER = "battery_controller"
