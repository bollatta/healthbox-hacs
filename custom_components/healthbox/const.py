"""Constants for the Renson Healthbox integration."""
import voluptuous as vol

from logging import Logger, getLogger
from datetime import timedelta

from homeassistant.const import Platform
from homeassistant.helpers import config_validation as cv

LOGGER: Logger = getLogger(__package__)

NAME = "Healthbox "
DOMAIN = "healthbox"
VERSION = "0.0.1"
MANUFACTURER = "Renson"
ATTRIBUTION = ""
SCAN_INTERVAL = timedelta(seconds=5)

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]

SERVICE_CHANGE_ROOM_PROFILE = "change_room_profile"
SERVICE_CHANGE_ROOM_PROFILE_SCHEMA = vol.Schema(
    {
        vol.Required(cv.CONF_DEVICE_ID): cv.string,
        vol.Required("profile_name"): cv.string
    }
)

SERVICE_START_ROOM_BOOST = "start_room_boost"
SERVICE_START_ROOM_BOOST_SCHEMA = vol.Schema(
    {
        vol.Required(cv.CONF_DEVICE_ID): cv.string,
        vol.Required("boost_level"): vol.All(int, vol.Range(min=10, max=200)),
        vol.Required("boost_timeout"): vol.All(int, vol.Range(min=5, max=720)),
    }
)

SERVICE_STOP_ROOM_BOOST = "stop_room_boost"
SERVICE_STOP_ROOM_BOOST_SCHEMA = vol.Schema(
    {vol.Required("device_id"): cv.string},
)

ALL_SERVICES = [
    SERVICE_START_ROOM_BOOST,
    SERVICE_STOP_ROOM_BOOST,
    SERVICE_CHANGE_ROOM_PROFILE
]
