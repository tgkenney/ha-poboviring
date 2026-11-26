"""Ring model detection tests."""

from __future__ import annotations

from custom_components.pobovi_ring import models


def test_2026_firmware_uses_zone_time_only() -> None:
    model = models.detect_model("V1.2-2026061312")
    assert model.key == "pobo-2026"
    assert model.time_commands == ("zone",)


def test_2025_firmware_sends_legacy_and_zone_time() -> None:
    model = models.detect_model("V1.2-2025092301")
    assert model.key == "pobo-2025"
    assert model.time_commands == ("legacy", "zone")


def test_unknown_firmware_falls_back_to_generic() -> None:
    assert models.detect_model("V9.9-2099010100").key == "generic"
    assert models.detect_model(None).key == "generic"


def test_model_by_key_round_trip() -> None:
    assert models.model_by_key("pobo-2025").key == "pobo-2025"
    assert models.model_by_key("nope").key == "generic"
    assert models.model_by_key(None).key == "generic"
