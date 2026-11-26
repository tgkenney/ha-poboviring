"""Diagnostics for the POBOVi Ring integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import CONF_SPARKY_API_KEY, DOMAIN
from .coordinator import PoboviRingCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: PoboviRingCoordinator = hass.data[DOMAIN][entry.entry_id]
    snapshot = coordinator.data
    integration = await async_get_integration(hass, DOMAIN)

    options = dict(entry.options)
    if options.get(CONF_SPARKY_API_KEY):
        options[CONF_SPARKY_API_KEY] = "**redacted**"

    return {
        "version": integration.version,
        "entry": {
            "data": dict(entry.data),
            "options": options,
        },
        "address": coordinator.address,
        "model": coordinator.model.key,
        "model_name": coordinator.model.name,
        "model_notes": coordinator.model.notes,
        "clock_commands": list(coordinator.model.time_commands),
        "sparky_enabled": coordinator.sparky_enabled,
        "sparky_error": coordinator.sparky_push_error,
        "pending_sparky_records": coordinator.pending_count,
        "ota": coordinator.ota_state,
        "sparky_last_push": coordinator.last_push,
        "sparky_account": coordinator.sparky_account,
        "command_counts": None
        if snapshot is None
        else {f"0x{cmd:02X}": count for cmd, count in sorted(snapshot.command_counts.items())},
        "last_update_success": coordinator.last_update_success,
        "frame_log_count": len(coordinator.frame_log),
        "frame_log": coordinator.frame_log[-300:],
        "snapshot": None
        if snapshot is None
        else {
            "battery": snapshot.battery,
            "last_sync": snapshot.last_sync.isoformat(),
            "connected_via": snapshot.connected_via,
            "frames_seen": snapshot.frames_seen,
            "device_info": snapshot.device_info,
            "record_count": len(snapshot.records),
            "raw_frames": snapshot.raw_frames,
        },
    }
