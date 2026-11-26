"""Sensor platform for the POBOVi Ring integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import (
    DOMAIN,
    METRIC_ACTIVE_MINUTES,
    METRIC_CALORIES,
    METRIC_HEART_RATE,
    METRIC_HRV,
    METRIC_RESPIRATORY,
    METRIC_SLEEP,
    METRIC_SPO2,
    METRIC_STEPS,
    METRIC_STRESS,
    METRIC_TEMPERATURE,
)
from .coordinator import PoboviRingCoordinator
from .entity import PoboviRingEntity


def _metric_value(metric: str) -> Callable[[PoboviRingCoordinator], StateType]:
    def value(coordinator: PoboviRingCoordinator) -> StateType:
        record = coordinator.latest_record(metric)
        return record.value if record is not None else None

    return value


def _battery(coordinator: PoboviRingCoordinator) -> StateType:
    return coordinator.device_battery


def _firmware(coordinator: PoboviRingCoordinator) -> str | None:
    return coordinator.device_firmware


def _rssi(coordinator: PoboviRingCoordinator) -> int | None:
    return coordinator.device_rssi


def _last_sync(coordinator: PoboviRingCoordinator) -> datetime | None:
    return coordinator.device_last_sync


def _sleep_score(coordinator: PoboviRingCoordinator) -> StateType:
    record = coordinator.latest_record(METRIC_SLEEP)
    if record is None:
        return None
    score = record.extra.get("score")
    return int(score) if isinstance(score, (int, float)) else None


def _sparky_status(coordinator: PoboviRingCoordinator) -> str:
    if not coordinator.sparky_enabled:
        return "disabled"
    return "error" if coordinator.sparky_push_error else "ok"


@dataclass(frozen=True, kw_only=True)
class PoboviSensorDescription(SensorEntityDescription):
    """Describes a POBOVi Ring sensor."""

    value_fn: Callable[[PoboviRingCoordinator], Any]


SENSORS: tuple[PoboviSensorDescription, ...] = (
    PoboviSensorDescription(
        key="battery",
        translation_key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_battery,
    ),
    PoboviSensorDescription(
        key=METRIC_HEART_RATE,
        translation_key="heart_rate",
        native_unit_of_measurement="bpm",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:heart-pulse",
        value_fn=_metric_value(METRIC_HEART_RATE),
    ),
    PoboviSensorDescription(
        key=METRIC_HRV,
        translation_key="hrv",
        native_unit_of_measurement="ms",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:chart-timeline-variant",
        value_fn=_metric_value(METRIC_HRV),
    ),
    PoboviSensorDescription(
        key=METRIC_SPO2,
        translation_key="spo2",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:lungs",
        value_fn=_metric_value(METRIC_SPO2),
    ),
    PoboviSensorDescription(
        key=METRIC_RESPIRATORY,
        translation_key="respiratory_rate",
        native_unit_of_measurement="breaths/min",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:weather-windy",
        value_fn=_metric_value(METRIC_RESPIRATORY),
    ),
    PoboviSensorDescription(
        key=METRIC_STEPS,
        translation_key="steps",
        native_unit_of_measurement="steps",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:walk",
        value_fn=_metric_value(METRIC_STEPS),
    ),
    PoboviSensorDescription(
        key=METRIC_CALORIES,
        translation_key="calories",
        native_unit_of_measurement="kcal",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:fire",
        value_fn=_metric_value(METRIC_CALORIES),
    ),
    PoboviSensorDescription(
        key=METRIC_ACTIVE_MINUTES,
        translation_key="active_minutes",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:run",
        value_fn=_metric_value(METRIC_ACTIVE_MINUTES),
    ),
    PoboviSensorDescription(
        key=METRIC_STRESS,
        translation_key="stress",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:brain",
        value_fn=_metric_value(METRIC_STRESS),
    ),
    PoboviSensorDescription(
        key=METRIC_TEMPERATURE,
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_metric_value(METRIC_TEMPERATURE),
    ),
    PoboviSensorDescription(
        key=METRIC_SLEEP,
        translation_key="sleep",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:sleep",
        value_fn=_metric_value(METRIC_SLEEP),
    ),
    PoboviSensorDescription(
        key="sleep_score",
        translation_key="sleep_score",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:chart-donut",
        value_fn=_sleep_score,
    ),
    PoboviSensorDescription(
        key="firmware",
        translation_key="firmware",
        icon="mdi:chip",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_firmware,
    ),
    PoboviSensorDescription(
        key="signal_strength",
        translation_key="signal_strength",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement="dBm",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_rssi,
    ),
    PoboviSensorDescription(
        key="last_sync",
        translation_key="last_sync",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_last_sync,
    ),
    PoboviSensorDescription(
        key="sparky_status",
        translation_key="sparky_status",
        device_class=SensorDeviceClass.ENUM,
        options=["ok", "error", "disabled"],
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:cloud-upload",
        value_fn=_sparky_status,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up POBOVi Ring sensors."""
    coordinator: PoboviRingCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(PoboviRingSensor(coordinator, description) for description in SENSORS)


class PoboviRingSensor(PoboviRingEntity, SensorEntity):
    """A sensor backed by a POBOVi Ring metric."""

    entity_description: PoboviSensorDescription

    def __init__(
        self,
        coordinator: PoboviRingCoordinator,
        description: PoboviSensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    async def async_update(self) -> None:
        """Force a poll when homeassistant.update_entity is called."""
        await self.coordinator.async_request_refresh()

    @property
    def native_value(self) -> StateType | datetime:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator)

    @property
    def available(self) -> bool:
        """Keep showing the last known value while the ring is out of range.

        These rings connect only intermittently, so going unavailable on every
        failed poll would blank the dashboard. Freshness is reported by the
        Last sync sensor instead.
        """
        if self.entity_description.key in (
            "sparky_status",
            "firmware",
            "signal_strength",
            "last_sync",
        ):
            return True
        return self.native_value is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Expose connection details and the full sleep-stage breakdown."""
        key = self.entity_description.key
        if key == "signal_strength":
            if self.coordinator.device_proxy is None:
                return None
            return {"proxy": self.coordinator.device_proxy}
        if key != METRIC_SLEEP:
            return None
        record = self.coordinator.latest_record(METRIC_SLEEP)
        if record is None:
            return None
        minutes = {0: 0, 1: 0, 2: 0, 3: 0}
        for item in str(record.extra.get("stages") or "").split(","):
            try:
                kind, length = (int(part) for part in item.split(":"))
            except ValueError:
                continue
            if kind in minutes:
                minutes[kind] += length
        return {
            "bedtime": record.timestamp.isoformat(),
            "wake_time": record.extra.get("end"),
            "score": record.extra.get("score"),
            "pauses": record.extra.get("pauses"),
            "segments": record.extra.get("segments"),
            "deep_minutes": minutes[0],
            "light_minutes": minutes[1],
            "rem_minutes": minutes[2],
            "awake_minutes": minutes[3],
            "sessions": self.coordinator.recent_sessions(),
        }

