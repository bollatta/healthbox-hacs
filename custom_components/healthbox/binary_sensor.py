"""Sensor platform for healthbox."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from pyhealthbox3.models import Healthbox3Room

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

from .const import DOMAIN
from .coordinator import HealthboxDataUpdateCoordinator
from .entity import HealthboxRoomEntity


@dataclass
class HealthboxRoomEntityDescriptionMixin:
    """Mixin values for Healthbox Room entities."""

    room: Healthbox3Room
    is_on: bool


@dataclass
class HealthboxRoomBinarySensorEntityDescription(
    BinarySensorEntityDescription, HealthboxRoomEntityDescriptionMixin
):
    """Class describing Healthbox Room binary sensor entities."""


def generate_binary_room_sensors_for_healthbox(
    coordinator: HealthboxDataUpdateCoordinator,
) -> list[HealthboxRoomBinarySensorEntityDescription]:
    """Generate binary sensors for each room."""
    room_binary_sensors: list[HealthboxRoomBinarySensorEntityDescription] = []

    for room in coordinator.api.rooms:
        if room.boost is not None:
            room_binary_sensors.append(
                HealthboxRoomBinarySensorEntityDescription(
                    key=f"{room.room_id}_boost_status",
                    name=f"{room.name} Boost Status",
                    room=room,
                    is_on=lambda x: x.boost.enabled
                )
            )

    return room_binary_sensors


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator: HealthboxDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    room_binary_sensors = generate_binary_room_sensors_for_healthbox(
        coordinator=coordinator)

    entities = []

    for description in room_binary_sensors:
        entities.append(HealthboxRoomBinarySensor(coordinator, description))

    async_add_entities(entities)


class HealthboxRoomBinarySensor(HealthboxRoomEntity, BinarySensorEntity):
    """Representation of a Healthbox Room Sensor."""

    entity_description: HealthboxRoomBinarySensorEntityDescription

    @property
    def is_on(self) -> bool | None:
        """Binary Sensor native value."""
        if (room := self._room) is None:
            return None
        return self.entity_description.is_on(room)
