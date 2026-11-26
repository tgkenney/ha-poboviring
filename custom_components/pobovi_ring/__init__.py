"""Setup for the POBOVi Ring integration."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.components.bluetooth import (
    BluetoothCallbackMatcher,
    BluetoothChange,
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
    async_register_callback,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, SupportsResponse, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .coordinator import PoboviRingCoordinator
from .ota import OtaError

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]

SERVICE_FLASH_FIRMWARE = "flash_firmware"

STORE_SUFFIXES = (
    "pushed",
    "frames",
    "pending",
    "latest",
    "model",
    "device",
    "sleep_sessions",
)

FLASH_FIRMWARE_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("confirm"): cv.boolean,
        vol.Optional("dry_run", default=True): cv.boolean,
        vol.Optional("url"): cv.url,
        vol.Optional("version"): cv.string,
        vol.Optional("allow_downgrade", default=False): cv.boolean,
    }
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register the firmware update service."""

    async def _async_flash_firmware(call) -> dict:
        entity_id = call.data["entity_id"]
        registry = er.async_get(hass)
        registry_entry = registry.async_get(entity_id)
        if registry_entry is None or registry_entry.config_entry_id is None:
            raise ServiceValidationError(
                f"{entity_id} is not an entity of a POBOVi Ring config entry"
            )
        coordinator = hass.data.get(DOMAIN, {}).get(registry_entry.config_entry_id)
        if not isinstance(coordinator, PoboviRingCoordinator):
            raise ServiceValidationError("that ring is not set up")

        try:
            return await coordinator.async_flash_firmware(
                confirm=call.data["confirm"],
                dry_run=call.data["dry_run"],
                url=call.data.get("url"),
                expected_version=call.data.get("version"),
                allow_downgrade=call.data["allow_downgrade"],
            )
        except OtaError as err:
            raise ServiceValidationError(str(err)) from err

    if not hass.data.get(DOMAIN, {}).get("_services_registered"):
        hass.data.setdefault(DOMAIN, {})["_services_registered"] = True
        hass.services.async_register(
            DOMAIN,
            SERVICE_FLASH_FIRMWARE,
            _async_flash_firmware,
            schema=FLASH_FIRMWARE_SCHEMA,
            supports_response=SupportsResponse.OPTIONAL,
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up POBOVi Ring from a config entry."""
    coordinator = PoboviRingCoordinator(hass, entry)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await coordinator.async_load_latest()
    await coordinator.async_load_sessions()
    await coordinator.async_load_model()
    await coordinator.async_load_device()

    # The ring is often asleep or out of range, so never block startup on a
    # connection. Entities are created unavailable and fill in when it syncs.
    async def _async_initial_sync() -> None:
        await coordinator.async_backfill_frames()
        await coordinator.async_refresh()

    entry.async_create_background_task(
        hass, _async_initial_sync(), "pobovi_ring initial sync"
    )

    @callback
    def _handle_advertisement(
        service_info: BluetoothServiceInfoBleak, change: BluetoothChange
    ) -> None:
        coordinator.notify_advertisement()

    entry.async_on_unload(
        async_register_callback(
            hass,
            _handle_advertisement,
            BluetoothCallbackMatcher(address=coordinator.address, connectable=True),
            BluetoothScanningMode.ACTIVE,
        )
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_options))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def _async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Delete the integration's cached stores when the entry is removed."""
    for suffix in STORE_SUFFIXES:
        store = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}.{suffix}")
        await store.async_remove()
