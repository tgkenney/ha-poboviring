"""Constants for the POBOVi Ring integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "pobovi_ring"
MANUFACTURER: Final = "Shenzhen Pengbo Microelectronics"
MODEL: Final = "POBOVi Ring"

SERVICE_UUID: Final = "a6ed0201-d344-460a-8075-b9e8ec90d71b"
CHAR_WRITE_UUID: Final = "00000061-0000-1000-8000-00805f9b34fb"
CHAR_NOTIFY_UUID: Final = "00000060-0000-1000-8000-00805f9b34fb"
CHAR_BATTERY_UUID: Final = "00002a19-0000-1000-8000-00805f9b34fb"

AMOTA_SERVICE_UUID: Final = "00002760-08c2-11e1-9073-0e8ac72e1001"
AMOTA_WRITE_UUID: Final = "00002760-08c2-11e1-9073-0e8ac72e0001"
AMOTA_NOTIFY_UUID: Final = "00002760-08c2-11e1-9073-0e8ac72e0002"

OTA_CMD_HEADER: Final = 1
OTA_CMD_DATA: Final = 2
OTA_CMD_VERIFY: Final = 3
OTA_CMD_RESET: Final = 4

OTA_HEADER_BYTES: Final = 48
OTA_CHUNK_BYTES: Final = 512
OTA_WRITE_BYTES: Final = 20
OTA_WRITE_DELAY: Final = 0.005
OTA_RESPONSE_TIMEOUT: Final = 20
OTA_HEADER_TIMEOUT: Final = 25
OTA_MIN_RSSI: Final = -80
OTA_MIN_BATTERY: Final = 50
OTA_MAX_FIRMWARE_BYTES: Final = 2 * 1024 * 1024
OTA_MIN_FIRMWARE_BYTES: Final = 4096
OTA_VERIFY_TIMEOUT: Final = 90

FW_INFO_URL: Final = (
    "https://app.pobovielectronics.com/api/client/commonMsg/getNewestVersion"
    "?packageType=bluetooth_ring"
)
FW_ALLOWED_HOSTS: Final = ("fl.pobovielectronics.com", "app.pobovielectronics.com")

DEVINFO_SERVICE_UUID: Final = "0000180a-0000-1000-8000-00805f9b34fb"
DEVINFO_MODEL_UUID: Final = "00002a24-0000-1000-8000-00805f9b34fb"
DEVINFO_SERIAL_UUID: Final = "00002a25-0000-1000-8000-00805f9b34fb"
DEVINFO_FIRMWARE_UUID: Final = "00002a26-0000-1000-8000-00805f9b34fb"
DEVINFO_HARDWARE_UUID: Final = "00002a27-0000-1000-8000-00805f9b34fb"
DEVINFO_SOFTWARE_UUID: Final = "00002a28-0000-1000-8000-00805f9b34fb"
DEVINFO_MANUFACTURER_UUID: Final = "00002a29-0000-1000-8000-00805f9b34fb"

FRAME_HEADER: Final = 0x55
FRAME_DIR_DATA: Final = 0xAA
FRAME_DIR_ACK: Final = 0xBB

CMD_RR: Final = 0x6E
CMD_STEPS: Final = 0x10
CMD_CALORIES: Final = 0x11
CMD_ACTIVE_TIME: Final = 0x12
CMD_SLEEP: Final = 0x13
CMD_STRESS: Final = 0x14
CMD_PHYSIOLOGY: Final = 0x16
CMD_TEMPERATURE: Final = 0x17
CMD_GCTL: Final = 0x09
CMD_WOMENS_HEALTH: Final = 0x15
CMD_PPG_HR: Final = 0x21
CMD_PPG_SPO2: Final = 0x22
CMD_PPG_HRV: Final = 0x23
CMD_TEST_ERROR: Final = 0x24
CMD_PPG_SWITCH: Final = 0x20
CMD_SYSTEM_TIME: Final = 0x30
CMD_USER_INFO: Final = 0x31
CMD_DEVICE_INFO: Final = 0x32
CMD_CONNECTION_PRIORITY: Final = 0x34
CMD_SYSTEM_TIME_ZONE: Final = 0x51
CMD_SEDENTARY: Final = 0x5D
CMD_SPORT_SESSION: Final = 0x69
CMD_SLEEP_END: Final = 0x6B
CMD_SEDENTARY_ACK: Final = 0xC8
CMD_FIND_RING: Final = 0xD0
CMD_TEST_DATA: Final = 0xE2
CMD_ROTATE_SWITCH: Final = 0xEA
CMD_ROTATE_EVENT: Final = 0xEB
CMD_DATA_SEND_END: Final = 0xEC

GCTL_CALORIE: Final = 17
GCTL_STRESS: Final = 20

PPG_FUNC_HR: Final = 1
PPG_FUNC_HRV: Final = 2
PPG_FUNC_SPO2: Final = 6
PPG_FUNC_TEMPERATURE: Final = 10

PRIORITY_LOW_POWER: Final = 0x11
PRIORITY_HIGH: Final = 0x22

CONF_ADDRESS: Final = "address"
CONF_NAME: Final = "name"
CONF_POLL_INTERVAL: Final = "poll_interval"
CONF_COLLECT_SECONDS: Final = "collect_seconds"
CONF_ENABLE_REALTIME: Final = "enable_realtime"
CONF_SPARKY_ENABLED: Final = "sparky_enabled"
CONF_SPARKY_URL: Final = "sparky_url"
CONF_SPARKY_API_KEY: Final = "sparky_api_key"
CONF_SPARKY_SOURCE: Final = "sparky_source"

CONF_PROFILE_ENABLED: Final = "ring_profile_enabled"
CONF_GENDER: Final = "ring_gender"
CONF_BIRTHDATE: Final = "ring_birthdate"
CONF_HEIGHT: Final = "ring_height_cm"
CONF_WEIGHT: Final = "ring_weight_kg"
CONF_STRIDE: Final = "ring_stride_cm"

CONF_CYCLE_ENABLED: Final = "ring_cycle_enabled"
CONF_CYCLE_START: Final = "ring_cycle_start"
CONF_CYCLE_DURATION: Final = "ring_cycle_duration"
CONF_CYCLE_LENGTH: Final = "ring_cycle_length"

CONF_FIND_SECONDS: Final = "find_ring_seconds"

GENDER_WIRE = {"unspecified": 0, "male": 1}

DEFAULT_FIND_SECONDS: Final = 120
MIN_FIND_SECONDS: Final = 5
MAX_FIND_SECONDS: Final = 255

DEFAULT_POLL_INTERVAL: Final = 30
DEFAULT_COLLECT_SECONDS: Final = 20
DEFAULT_ENABLE_REALTIME: Final = False
DEFAULT_SPARKY_ENABLED: Final = False
DEFAULT_SPARKY_URL: Final = ""
DEFAULT_SPARKY_SOURCE: Final = "pobovi_ring"

MIN_POLL_INTERVAL: Final = 5
MAX_POLL_INTERVAL: Final = 1440
MIN_COLLECT_SECONDS: Final = 5
MAX_COLLECT_SECONDS: Final = 120

CONNECT_TIMEOUT: Final = 40
DISCONNECT_TIMEOUT: Final = 10
RETRY_AFTER_FAILURE: Final = timedelta(minutes=5)

SPARKY_ENDPOINT_PATH: Final = "/api/health-data"

METRIC_STEPS: Final = "steps"
METRIC_CALORIES: Final = "calories"
METRIC_ACTIVE_MINUTES: Final = "active_minutes"
METRIC_HEART_RATE: Final = "heart_rate"
METRIC_HRV: Final = "hrv"
METRIC_SPO2: Final = "spo2"
METRIC_STRESS: Final = "stress"
METRIC_TEMPERATURE: Final = "temperature"
METRIC_SLEEP: Final = "sleep"
METRIC_RESPIRATORY: Final = "respiratory_rate"
METRIC_BATTERY: Final = "battery"
METRIC_SIGNAL_STRENGTH: Final = "signal_strength"
METRIC_LAST_SYNC: Final = "last_sync"
