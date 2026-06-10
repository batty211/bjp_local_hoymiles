"""Constants for BJP Local Hoymiles."""

from __future__ import annotations

DOMAIN = "bjp_local_hoymiles"
NAME = "BJP Local Hoymiles"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_BILLING_CYCLE_ENABLED = "billing_cycle_enabled"
CONF_BILLING_CYCLE_MODE = "billing_cycle_mode"
CONF_BILLING_RESET_DAY = "billing_reset_day"
CONF_BILLING_RESET_TIME = "billing_reset_time"
CONF_BILLING_CRON = "billing_cron"

DEFAULT_PORT = 10081
DEFAULT_SCAN_INTERVAL = 35
MIN_SCAN_INTERVAL = 35
MAX_SCAN_INTERVAL = 300
DEFAULT_TIMEOUT = 10
DEFAULT_BILLING_RESET_TIME = "00:00"

BILLING_CYCLE_MODE_SIMPLE_MONTHLY = "simple_monthly"
BILLING_CYCLE_MODE_ADVANCED_CRON = "advanced_cron"
BILLING_RESET_DAY_LAST = "last_day"

ATTR_DTU_SERIAL = "dtu_serial"
ATTR_INVERTER_SERIAL = "inverter_serial"
ATTR_METER_SERIAL = "meter_serial"
ATTR_PORT_NUMBER = "port_number"

MANUFACTURER = "Hoymiles"
MODEL_DTU_PRO_S = "DTU-Pro-S"
MODEL_METER_DDSU666 = "DDSU666"
