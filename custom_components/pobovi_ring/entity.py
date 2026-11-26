"""Shared entity helpers for the POBOVi Ring integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import PoboviRingCoordinator


class PoboviRingEntity(CoordinatorEntity[PoboviRingCoordinator]):
    """Base entity for POBOVi Ring sensors."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PoboviRingCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.address)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=coordinator.ring_name,
            serial_number=coordinator.data.device_info.get("serial") if coordinator.data else None,
            sw_version=coordinator.data.device_info.get("software") if coordinator.data else None,
            hw_version=coordinator.data.device_info.get("hardware") if coordinator.data else None,
        )
