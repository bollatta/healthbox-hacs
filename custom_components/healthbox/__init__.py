"""The Renson Healthbox integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_HOST
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
    ServiceValidationError,
)
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from pyhealthbox3.healthbox3 import (
    Healthbox3,
    Healthbox3ApiClientAuthenticationError,
    Healthbox3ApiClientCommunicationError,
)

from .const import (
    ALL_SERVICES,
    DOMAIN,
    SERVICE_CHANGE_ROOM_PROFILE,
    SERVICE_CHANGE_ROOM_PROFILE_SCHEMA,
    SERVICE_START_ROOM_BOOST,
    SERVICE_START_ROOM_BOOST_SCHEMA,
    SERVICE_STOP_ROOM_BOOST,
    SERVICE_STOP_ROOM_BOOST_SCHEMA,
    PLATFORMS,
)

from .coordinator import HealthboxDataUpdateCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Renson Healthbox from a config entry."""
    api_key = None

    if CONF_API_KEY in entry.data:
        api_key = entry.data[CONF_API_KEY]

    # if CONF_API_KEY in entry.options:
    #     api_key = entry.options[CONF_API_KEY]

    api: Healthbox3 = Healthbox3(
        host=entry.data[CONF_HOST],
        api_key=api_key,
        session=async_get_clientsession(hass),
    )
    if api_key:
        try:
            await api.async_enable_advanced_api_features()
        except Healthbox3ApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except Healthbox3ApiClientCommunicationError as exception:
            raise ConfigEntryNotReady(exception) from exception

    coordinator = HealthboxDataUpdateCoordinator(
        hass=hass, entry=entry, api=api)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _async_register_services(hass)
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    return True


def _async_get_room_target(
    hass: HomeAssistant, device_id: str
) -> tuple[HealthboxDataUpdateCoordinator, int]:
    """Resolve a room device to the coordinator of its entry and its room id."""
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        raise ServiceValidationError(f"Device {device_id} not found")

    coordinators: dict[str, HealthboxDataUpdateCoordinator] = hass.data.get(
        DOMAIN, {})
    for entry_id in device.config_entries:
        if (coordinator := coordinators.get(entry_id)) is None:
            continue
        prefix = f"{coordinator.config_entry.unique_id}_"
        for domain, identifier in device.identifiers:
            if domain != DOMAIN or not identifier.startswith(prefix):
                continue
            room_id = identifier.removeprefix(prefix)
            if room_id.isdigit():
                return coordinator, int(room_id)

    raise ServiceValidationError(
        f"Device {device_id} is not a room of a loaded Healthbox"
    )


def _async_register_services(hass: HomeAssistant) -> None:
    """Register the integration services once, shared by all config entries."""
    if hass.services.has_service(DOMAIN, SERVICE_START_ROOM_BOOST):
        return

    async def change_room_profile(call: ServiceCall) -> None:
        """Service to change the HB3 Room Profile."""
        coordinator, room_id = _async_get_room_target(
            hass, call.data["device_id"])
        await coordinator.change_room_profile(
            room_id=room_id,
            profile_name=call.data["profile_name"]
        )

    async def start_room_boost(call: ServiceCall) -> None:
        """Service call to start boosting fans in a room."""
        coordinator, room_id = _async_get_room_target(
            hass, call.data["device_id"])
        await coordinator.start_room_boost(
            room_id=room_id,
            boost_level=call.data["boost_level"],
            boost_timeout=call.data["boost_timeout"] * 60,
        )

    async def stop_room_boost(call: ServiceCall) -> None:
        """Service call to stop boosting fans in a room."""
        coordinator, room_id = _async_get_room_target(
            hass, call.data["device_id"])
        await coordinator.stop_room_boost(room_id=room_id)

    hass.services.async_register(
        DOMAIN,
        SERVICE_START_ROOM_BOOST,
        start_room_boost,
        SERVICE_START_ROOM_BOOST_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_STOP_ROOM_BOOST, stop_room_boost, SERVICE_STOP_ROOM_BOOST_SCHEMA
    )
    hass.services.async_register(DOMAIN, SERVICE_CHANGE_ROOM_PROFILE,
                                 change_room_profile, SERVICE_CHANGE_ROOM_PROFILE_SCHEMA)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            del hass.data[DOMAIN]
            # Services are shared by all entries; drop them with the last one.
            for service in ALL_SERVICES:
                hass.services.async_remove(DOMAIN, service)

    return unload_ok


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry):
    """Reload entry if options change."""
    await hass.config_entries.async_reload(entry.entry_id)
