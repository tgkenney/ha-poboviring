"""Ring model / firmware variants.

The ring family is not uniform: two rings that look identical can run different
firmware with different capabilities. Rather than scattering version checks
through the codec, each variant is described once here and selected by the
firmware string the ring reports in its device-info reply.

To support a new variant:
  1. Add a RingModel entry with a firmware prefix and the capabilities it needs.
  2. Use the capability flags in ble.py / protocol.py.
  3. Unknown firmware automatically gets the most compatible behaviour.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RingModel:
    """Capabilities of one ring firmware variant."""

    key: str
    name: str
    firmware_prefixes: tuple[str, ...]
    time_commands: tuple[str, ...]
    notes: str = ""


# Clock sync command names understood by ble.async_collect:
#   "legacy" -> 0x30 (offset in hours), "zone" -> 0x51 (offset in minutes, DST aware)

MODELS: tuple[RingModel, ...] = (
    RingModel(
        key="pobo-2026",
        name="POBOVi Ring (2026 firmware)",
        firmware_prefixes=("V1.2-2026",),
        time_commands=("zone",),
        notes="Current firmware; releases the buffer on the zone-time command (0x51).",
    ),
    RingModel(
        key="pobo-2025",
        name="POBOVi Ring (2025 firmware)",
        firmware_prefixes=("V1.2-2025",),
        time_commands=("legacy", "zone"),
        notes=(
            "Older firmware: the new zone-time command alone does not set the "
            "clock, so the legacy RTC command (0x30) is sent as well. HRV "
            "readings also look much larger than on 2026 firmware (158-212 vs "
            "24-72), which suggests a different HRV metric (SDNN-like) - do not "
            "compare HRV across variants without checking."
        ),
    ),
)

# Used before the firmware is known and for any firmware we have not catalogued.
# Sending every clock command is idempotent and safe on all known variants.
GENERIC_MODEL = RingModel(
    key="generic",
    name="POBOVi Ring (unrecognised firmware)",
    firmware_prefixes=(),
    time_commands=("legacy", "zone"),
    notes="Fallback: uses the union of known-safe commands.",
)


def detect_model(software: str | None) -> RingModel:
    """Return the model matching a firmware/software string."""
    if software:
        for model in MODELS:
            if any(software.startswith(prefix) for prefix in model.firmware_prefixes):
                return model
    return GENERIC_MODEL


def model_by_key(key: str | None) -> RingModel:
    """Return the model for a stored key, falling back to the generic model."""
    if key:
        for model in MODELS:
            if model.key == key:
                return model
    return GENERIC_MODEL
