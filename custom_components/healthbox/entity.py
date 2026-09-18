"""Base entity for Healthbox room entities."""
from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo, EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, LOGGER, HealthboxRoom
from .coordinator import HealthboxDataUpdateCoordinator


class HealthboxRoomEntity(CoordinatorEntity[HealthboxDataUpdateCoordinator]):
    """Base class for entities that belong to a Healthbox room.

    Subclasses must use an entity description that has a ``room`` attribute.
    """

    def __init__(
        self,
        coordinator: HealthboxDataUpdateCoordinator,
        description: EntityDescription,
    ) -> None:
        """Initialize the room entity."""
        super().__init__(coordinator)

        self.entity_description = description
        room_id = description.room.room_id
        self._room_missing_logged = False
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}-{room_id}-{description.key}"
        )
        self._attr_name = f"{description.name}"
        self._attr_device_info = DeviceInfo(
            name=description.room.name,
            identifiers={(DOMAIN, f"{coordinator.config_entry.unique_id}_{room_id}")},
            manufacturer="Renson",
            model="Healthbox Room",
        )

    @property
    def _room(self) -> HealthboxRoom | None:
        """Return this entity's room from the latest data, or None if it is gone.

        A missing room is logged once when it disappears and once when it
        comes back, not on every poll.
        """
        room_id = int(self.entity_description.room.room_id)
        matching_rooms = [
            room for room in self.coordinator.api.rooms if int(room.room_id) == room_id
        ]

        if len(matching_rooms) != 1:
            if not self._room_missing_logged:
                LOGGER.warning("No matching room found for id %s", room_id)
                self._room_missing_logged = True
            return None

        if self._room_missing_logged:
            LOGGER.info("Room %s is available again", room_id)
            self._room_missing_logged = False
        return matching_rooms[0]

    @property
    def available(self) -> bool:
        """Return False while the room is missing from the API response."""
        return super().available and self._room is not None
