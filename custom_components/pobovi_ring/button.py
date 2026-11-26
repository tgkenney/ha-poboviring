"""Button platform for the POBOVi Ring integration."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import PoboviRingCoordinator
from .entity import PoboviRingEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up POBOVi Ring buttons."""
    coordinator: PoboviRingCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([PoboviFindRingButton(coordinator)])


class PoboviFindRingButton(PoboviRingEntity, ButtonEntity):
    """Make the ring buzz so it can be found."""

    _attr_translation_key = "find_ring"
    _attr_icon = "mdi:vibrate"

    def __init__(self, coordinator: PoboviRingCoordinator) -> None:
        super().__init__(coordinator, "find_ring")

    @property
    def available(self) -> bool:
        """The action does not depend on cached data being fresh."""
        return True

    async def async_press(self) -> None:
        """Press the button."""
        await self.coordinator.async_find_ring()
