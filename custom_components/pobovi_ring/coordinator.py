"""Data coordinator for the POBOVi Ring integration."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import slugify

from .ble import RingConnectionError, RingSnapshot, async_collect
from .ble import async_find_ring as ble_find_ring
from .const import (
    CONF_ADDRESS,
    CONF_BIRTHDATE,
    CONF_COLLECT_SECONDS,
    CONF_CYCLE_DURATION,
    CONF_CYCLE_ENABLED,
    CONF_CYCLE_LENGTH,
    CONF_CYCLE_START,
    CONF_ENABLE_REALTIME,
    CONF_FIND_SECONDS,
    CONF_GENDER,
    CONF_HEIGHT,
    CONF_NAME,
    CONF_POLL_INTERVAL,
    CONF_PROFILE_ENABLED,
    CONF_SPARKY_API_KEY,
    CONF_SPARKY_ENABLED,
    CONF_SPARKY_SOURCE,
    CONF_SPARKY_URL,
    CONF_STRIDE,
    CONF_WEIGHT,
    DEFAULT_COLLECT_SECONDS,
    DEFAULT_ENABLE_REALTIME,
    DEFAULT_FIND_SECONDS,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_SPARKY_SOURCE,
    DOMAIN,
    GENDER_WIRE,
    METRIC_SLEEP,
)
from .models import GENERIC_MODEL, RingModel, detect_model, model_by_key
from .ota import OtaError
from .ota import async_flash_firmware as ota_flash_firmware
from .protocol import RingRecord, decode_record, parse_frame
from .sparky import SparkyClient, SparkyError

_LOGGER = logging.getLogger(__name__)

MAX_TRACKED_KEYS = 5000
MAX_TRACKED_FRAMES = 1000
STORAGE_VERSION = 1
ADVERT_RETRY_GAP = 120
MAX_PENDING = 5000
MAX_STORED_SESSIONS = 50
RECENT_SESSION_LIMIT = 10
PUSH_BATCH = 200


class PoboviRingCoordinator(DataUpdateCoordinator[RingSnapshot]):
    """Poll the ring and forward new records to SparkyFitness."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        options = entry.options
        self.address: str = entry.data[CONF_ADDRESS]
        self.ring_name: str = entry.data.get(CONF_NAME) or "POBOVi Ring"
        self.collect_seconds: int = int(options.get(CONF_COLLECT_SECONDS, DEFAULT_COLLECT_SECONDS))
        self.realtime: bool = bool(options.get(CONF_ENABLE_REALTIME, DEFAULT_ENABLE_REALTIME))
        poll_interval = int(options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL))

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {self.ring_name} ({self.address})",
            update_interval=timedelta(minutes=poll_interval),
        )

        self._store: Store[list[str]] = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}.pushed")
        self._frames_store: Store[list[str]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}.frames"
        )
        self._pending_store: Store[list[dict[str, Any]]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}.pending"
        )
        self._latest_store: Store[dict[str, dict[str, Any]]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}.latest"
        )
        self._model_store: Store[str] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}.model"
        )
        self._device_store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}.device"
        )
        self._sessions_store: Store[list[dict[str, Any]]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}.sleep_sessions"
        )
        self._pushed: set[str] = set()
        self._pending: list[dict[str, Any]] = []
        self._latest: dict[str, dict[str, Any]] = {}
        self._frames: list[str] = []
        self._sessions: list[dict[str, Any]] = []
        self._frames_loaded = False
        self._sessions_loaded = False
        self._pushed_loaded = False
        self._backfilled = False
        self._pending_loaded = False
        self._latest_loaded = False
        self._model_loaded = False
        self.model: RingModel = GENERIC_MODEL
        self._device: dict[str, Any] = {}
        self._device_loaded = False
        self._ota_lock = asyncio.Lock()
        self._ota_in_progress = False
        self._ota: dict[str, Any] = {"status": "idle"}
        self._in_flight = False
        self._last_attempt = 0.0
        self._sparky_push_error: str | None = None
        self._last_push_count = 0
        self._last_push: dict[str, Any] | None = None
        self._sparky_account: dict[str, Any] | None = None
        self._sparky_readback: str | None = None

    @property
    def sparky_push_error(self) -> str | None:
        """Return the last Sparky error, if any."""
        return self._sparky_push_error

    @property
    def sparky_enabled(self) -> bool:
        """Return whether Sparky pushing is configured."""
        return bool(self.entry.options.get(CONF_SPARKY_ENABLED)) and bool(
            self.entry.options.get(CONF_SPARKY_API_KEY)
        )

    @property
    def frame_log(self) -> list[str]:
        """Return the rolling log of raw frames, for verification."""
        return self._frames

    @property
    def last_push(self) -> dict[str, Any] | None:
        """Return a summary of the most recent SparkyFitness upload."""
        return self._last_push

    @property
    def sparky_account(self) -> dict[str, Any] | None:
        """Return the SparkyFitness account the API key belongs to."""
        return self._sparky_account

    @property
    def sparky_readback(self) -> str | None:
        """Return what SparkyFitness stored for today, as read back."""
        return self._sparky_readback

    async def async_find_ring(self) -> None:
        """Ring the ring so it can be located."""
        if self._in_flight:
            _LOGGER.warning("Cannot find the ring while a sync is in progress")
            return
        seconds = int(self.entry.options.get(CONF_FIND_SECONDS, DEFAULT_FIND_SECONDS))
        try:
            await ble_find_ring(self.hass, self.address, seconds)
        except RingConnectionError as err:
            _LOGGER.error("Could not activate find-my-ring: %s", err)
            return
        _LOGGER.info("Ring activated for %s seconds", seconds)

    def _set_ota(self, status: str, payload: dict | None = None) -> None:
        self._ota = {"status": status, **(payload or {})}
        self.hass.bus.async_fire(
            "pobovi_ring_ota",
            {"entry_id": self.entry.entry_id, "ring": self.ring_name, "status": status, **(payload or {})},
        )

    async def async_flash_firmware(
        self,
        *,
        confirm: bool,
        dry_run: bool = True,
        url: str | None = None,
        expected_version: str | None = None,
        allow_downgrade: bool = False,
    ) -> dict[str, Any]:
        """Validate checks, then flash a firmware image to this ring."""
        if not confirm:
            raise OtaError("confirm must be true to start a firmware update")
        if self._ota_lock.locked():
            raise OtaError("a firmware update is already running")
        if self._in_flight:
            raise OtaError("a sync is in progress; retry the update in a moment")

        async with self._ota_lock:
            # Set the flag first, then re-check: a poll that started between the
            # check above and here is caught, and one that starts later sees the
            # flag and skips its update.
            self._ota_in_progress = True
            if self._in_flight:
                self._ota_in_progress = False
                raise OtaError("a sync is in progress; retry the update in a moment")
            last_progress = -1

            def on_status(state: str, payload: dict) -> None:
                self._set_ota(state, payload)

            def on_progress(percent: int) -> None:
                nonlocal last_progress
                if percent != last_progress and percent % 2 == 0:
                    last_progress = percent
                    self._set_ota("flashing", {"progress": percent})

            try:
                result = await ota_flash_firmware(
                    self.hass,
                    self.address,
                    url=url,
                    expected_version=expected_version,
                    allow_downgrade=allow_downgrade,
                    dry_run=dry_run,
                    known_version=self.device_firmware,
                    on_status=on_status,
                    on_progress=on_progress,
                )
            except OtaError as err:
                self._set_ota("error", {"message": str(err)})
                raise
            except Exception as err:
                self._set_ota("error", {"message": f"{type(err).__name__}: {err}"})
                raise OtaError(f"firmware update failed: {type(err).__name__}: {err}") from err
            finally:
                self._ota_in_progress = False

            self._set_ota(result.get("status", "done"), result.get("checks") or {})
            if not dry_run:
                await self._async_remember_device(
                    RingSnapshot(
                        device_info={"software": (result.get("checks") or {}).get("reported_version")}
                        if (result.get("checks") or {}).get("reported_version")
                        else {},
                    )
                )
            self.hass.async_create_task(self.async_request_refresh())
            return result

    def _profile_from_options(self) -> dict[str, Any] | None:
        """Build the ring profile payload from the config options."""
        if not self.entry.options.get(CONF_PROFILE_ENABLED):
            return None
        birthdate = str(self.entry.options.get(CONF_BIRTHDATE, "1990-01-01"))
        try:
            year, month, day = (int(part) for part in birthdate.split("-"))
        except ValueError:
            _LOGGER.warning("Ignoring ring profile: invalid birthdate %r", birthdate)
            return None
        profile: dict[str, Any] = {
            "age": max(0, datetime.now().year - year),
            "gender": GENDER_WIRE.get(str(self.entry.options.get(CONF_GENDER)), 0),
            "height_cm": float(self.entry.options.get(CONF_HEIGHT, 175)),
            "weight_kg": float(self.entry.options.get(CONF_WEIGHT, 75)),
            "stride_cm": float(self.entry.options.get(CONF_STRIDE, 0)),
            "birth_year": year,
            "birth_month": month,
            "birth_day": day,
        }
        cycle = self._cycle_from_options()
        if cycle is not None:
            profile["women_year"] = cycle["last_year"] - 1900
            profile["women_month"] = cycle["last_month"]
            profile["women_day"] = cycle["last_day"]
            profile["women_duration"] = cycle["duration"]
            profile["women_cycle"] = cycle["cycle"]
        return profile

    def _cycle_from_options(self) -> dict[str, Any] | None:
        """Build the cycle-tracking payload when enabled and configured."""
        if not self.entry.options.get(CONF_CYCLE_ENABLED):
            return None
        start = str(self.entry.options.get(CONF_CYCLE_START, ""))
        try:
            year, month, day = (int(part) for part in start.split("-"))
        except ValueError:
            _LOGGER.warning("Ignoring cycle settings: invalid start date %r", start)
            return None
        return {
            "last_year": year,
            "last_month": month,
            "last_day": day,
            "duration": int(self.entry.options.get(CONF_CYCLE_DURATION, 5)),
            "cycle": int(self.entry.options.get(CONF_CYCLE_LENGTH, 28)),
        }

    async def _async_validate_sparky(self, client: SparkyClient) -> None:
        """Confirm the destination account and read today's stored values back."""
        identity = await client.async_get("/api/identity/user")
        if isinstance(identity, dict):
            self._sparky_account = {
                "name": identity.get("activeUserFullName")
                or identity.get("authenticatedUserEmail"),
                "id": identity.get("activeUserId")
                or identity.get("authenticatedUserId"),
            }
        today = datetime.now().astimezone().date().isoformat()
        checkin = await client.async_get(f"/api/measurements/check-in/{today}")
        if checkin is not None:
            self._sparky_readback = json.dumps(checkin, default=str)[:1500]

    @property
    def pending_count(self) -> int:
        """Return how many records are waiting to be uploaded."""
        return len(self._pending)

    async def async_load_latest(self) -> None:
        """Load the last known value for each metric."""
        if self._latest_loaded:
            return
        stored = await self._latest_store.async_load()
        if stored:
            self._latest = dict(stored)
        self._latest_loaded = True

    async def async_load_model(self) -> None:
        """Load the detected ring model."""
        if self._model_loaded:
            return
        self.model = model_by_key(await self._model_store.async_load())
        self._model_loaded = True

    async def async_load_device(self) -> None:
        """Load the last known device details."""
        if self._device_loaded:
            return
        stored = await self._device_store.async_load()
        if stored:
            self._device = dict(stored)
        self._device_loaded = True

    @property
    def ota_state(self) -> dict[str, Any]:
        """Return the state of the last firmware update."""
        return self._ota

    @property
    def device_firmware(self) -> str | None:
        """Return the firmware/software string reported by the ring."""
        return self._device.get("firmware")

    @property
    def device_proxy(self) -> str | None:
        """Return the Bluetooth proxy used for the last successful sync."""
        return self._device.get("proxy")

    @property
    def device_battery(self) -> int | None:
        """Return the last battery level the ring reported."""
        value = self._device.get("battery")
        return int(value) if isinstance(value, (int, float)) else None

    @property
    def device_last_sync(self) -> datetime | None:
        """Return the last successful sync time."""
        value = self._device.get("last_sync")
        if not isinstance(value, str):
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    @property
    def device_rssi(self) -> int | None:
        """Return the RSSI of the last successful connection."""
        value = self._device.get("rssi")
        return int(value) if isinstance(value, (int, float)) else None

    async def _async_remember_device(self, snapshot: RingSnapshot) -> None:
        """Persist firmware, proxy and signal strength for diagnostics and the UI."""
        firmware = snapshot.device_info.get("software") or self._device.get("firmware")
        updated = {
            "firmware": firmware,
            "proxy": snapshot.proxy or self._device.get("proxy"),
            "rssi": snapshot.rssi if snapshot.rssi is not None else self._device.get("rssi"),
            "battery": snapshot.battery
            if snapshot.battery is not None
            else self._device.get("battery"),
            "last_sync": snapshot.last_sync.isoformat(),
        }
        if updated == self._device:
            return
        self._device = updated
        await self._device_store.async_save(updated)

    async def _async_update_model(self, device_info: dict[str, str]) -> None:
        """Detect the firmware variant from the device-info reply."""
        software = device_info.get("software")
        if not software:
            return
        model = detect_model(software)
        if model.key == self.model.key:
            return
        self.model = model
        await self._model_store.async_save(model.key)
        _LOGGER.info(
            "Detected %s (firmware %s); clock commands: %s",
            model.name,
            software,
            ", ".join(model.time_commands),
        )

    async def _async_remember(self, records: list[RingRecord]) -> None:
        """Keep the newest value per metric so sparse deltas do not blank sensors."""
        if not records:
            return
        await self.async_load_latest()
        await self.async_load_sessions()
        changed = False
        sessions_changed = False
        for record in records:
            # Session history keeps every distinct sleep start, so it must not
            # be filtered by the newest-value check below.
            if record.metric == METRIC_SLEEP and self._remember_session(record):
                sessions_changed = True

            current = self._latest.get(record.metric)
            if current is not None:
                try:
                    if datetime.fromisoformat(current["timestamp"]) > record.timestamp:
                        continue
                except (KeyError, ValueError, TypeError):
                    pass
            self._latest[record.metric] = {
                "value": record.value,
                "timestamp": record.timestamp.isoformat(),
                "extra": record.extra,
            }
            changed = True
        if changed:
            await self._latest_store.async_save(self._latest)
        if sessions_changed:
            await self._sessions_store.async_save(self._sessions)

    @callback
    def latest_record(self, metric: str) -> RingRecord | None:
        """Return the last known record for a metric."""
        item = self._latest.get(metric)
        if item is None:
            return None
        try:
            timestamp = datetime.fromisoformat(item["timestamp"])
        except (KeyError, ValueError, TypeError):
            return None
        return RingRecord(metric, item.get("value", 0), timestamp, "", dict(item.get("extra") or {}))

    async def async_load_sessions(self) -> None:
        """Load the retained sleep-session history."""
        if self._sessions_loaded:
            return
        stored = await self._sessions_store.async_load()
        if stored:
            self._sessions = [dict(item) for item in stored if isinstance(item, dict)]
        self._sessions_loaded = True

    def recent_sessions(self, limit: int = RECENT_SESSION_LIMIT) -> list[dict[str, Any]]:
        """Return the newest sleep sessions first."""
        return [dict(item) for item in reversed(self._sessions[-limit:])]

    def _remember_session(self, record: RingRecord) -> bool:
        """Upsert one sleep session into the retained history."""
        minutes = {0: 0, 1: 0, 2: 0, 3: 0}
        for item in str(record.extra.get("stages") or "").split(","):
            try:
                kind, length = (int(part) for part in item.split(":"))
            except ValueError:
                continue
            if kind in minutes:
                minutes[kind] += length
        entry = {
            "start": record.timestamp.isoformat(),
            "end": record.extra.get("end"),
            "minutes": int(record.value),
            "score": record.extra.get("score"),
            "pauses": record.extra.get("pauses"),
            "deep": minutes[0],
            "light": minutes[1],
            "rem": minutes[2],
            "awake": minutes[3],
        }
        for index, existing in enumerate(self._sessions):
            if existing.get("start") == entry["start"]:
                if existing == entry:
                    return False
                self._sessions[index] = entry
                break
        else:
            self._sessions.append(entry)
        self._sessions.sort(key=lambda item: str(item.get("start") or ""))
        if len(self._sessions) > MAX_STORED_SESSIONS:
            self._sessions = self._sessions[-MAX_STORED_SESSIONS:]
        return True

    async def _async_load_frames(self) -> None:
        if self._frames_loaded:
            return
        stored = await self._frames_store.async_load()
        if stored:
            self._frames = list(stored)
        self._frames_loaded = True

    async def _async_append_frames(self, frames: list[str]) -> None:
        await self._async_load_frames()
        self._frames.extend(frames)
        if len(self._frames) > MAX_TRACKED_FRAMES:
            self._frames = self._frames[-MAX_TRACKED_FRAMES:]
        await self._frames_store.async_save(self._frames)

    async def _async_load_pushed(self) -> None:
        if self._pushed_loaded:
            return
        stored = await self._store.async_load()
        if stored:
            self._pushed = set(stored)
        self._pushed_loaded = True

    async def _async_save_pushed(self) -> None:
        if len(self._pushed) > MAX_TRACKED_KEYS:
            ordered = sorted(self._pushed, key=lambda key: key.rsplit("|", 1)[-1])
            self._pushed = set(ordered[-MAX_TRACKED_KEYS:])
        await self._store.async_save(sorted(self._pushed))

    def _record_key(self, record: RingRecord) -> str:
        key = f"{record.metric}|{record.timestamp.isoformat()}"
        if record.metric == METRIC_SLEEP and (end := record.extra.get("end")):
            key = f"{key}|{end}"
        return key

    @staticmethod
    def _collapse_sleep(records: list[RingRecord]) -> list[RingRecord]:
        """Keep one copy of each sleep session per sync.

        The ring replays the same session more than once with different end
        times and can revise it (sometimes downward), so the last copy seen
        for a given start is the ring's current view. Other metrics pass
        through untouched.
        """
        index_by_start: dict[datetime, int] = {}
        collapsed: list[RingRecord] = []
        for record in records:
            if record.metric != METRIC_SLEEP:
                collapsed.append(record)
                continue
            index = index_by_start.get(record.timestamp)
            if index is None:
                index_by_start[record.timestamp] = len(collapsed)
                collapsed.append(record)
            else:
                collapsed[index] = record
        return collapsed

    async def _async_load_pending(self) -> None:
        if self._pending_loaded:
            return
        stored = await self._pending_store.async_load()
        if stored:
            self._pending = list(stored)
        self._pending_loaded = True

    async def _async_save_pending(self) -> None:
        if len(self._pending) > MAX_PENDING:
            dropped = len(self._pending) - MAX_PENDING
            self._pending = self._pending[-MAX_PENDING:]
            _LOGGER.warning(
                "SparkyFitness queue is full, dropping %s oldest unsent record(s)", dropped
            )
        await self._pending_store.async_save(self._pending)

    async def _async_enqueue(self, records: list[RingRecord]) -> None:
        """Queue records that SparkyFitness has not accepted yet.

        The ring hands records over exactly once, so anything collected while
        SparkyFitness is disabled, unreachable or misconfigured has to survive
        in the queue or it is lost forever.
        """
        await self._async_load_pushed()
        await self._async_load_pending()
        queued = {item["key"] for item in self._pending}
        source = (
            self.entry.options.get(CONF_SPARKY_SOURCE)
            or slugify(self.ring_name)
            or DEFAULT_SPARKY_SOURCE
        )
        added = 0
        for record in records:
            key = self._record_key(record)
            if key in self._pushed or key in queued:
                continue
            payload = record.as_sparky(source)
            if payload is None:
                continue
            self._pending.append({"key": key, "payload": payload})
            queued.add(key)
            added += 1
        if added:
            await self._async_save_pending()

    async def _async_flush(self) -> None:
        """Upload queued records in batches, keeping anything that fails."""
        await self._async_load_pending()
        if not self._pending:
            self._last_push_count = 0
            return

        url = self.entry.options.get(CONF_SPARKY_URL, "")
        api_key = self.entry.options.get(CONF_SPARKY_API_KEY, "")
        if not url or not api_key:
            self._sparky_push_error = "SparkyFitness URL or API key is missing"
            self._last_push_count = 0
            return

        client = SparkyClient(async_get_clientsession(self.hass), url, api_key)
        pushed = 0
        accepted = 0
        rejected = 0
        skipped = 0
        pushed_types: set[str] = set()
        reject_messages: list[str] = []
        while self._pending:
            batch = self._pending[:PUSH_BATCH]
            try:
                result = await client.async_push_payloads([item["payload"] for item in batch])
            except SparkyError as err:
                self._sparky_push_error = str(err)
                _LOGGER.warning(
                    "SparkyFitness upload failed, %s record(s) kept for retry: %s",
                    len(self._pending),
                    err,
                )
                break
            self._sparky_push_error = None
            summary = result if isinstance(result, dict) else {}
            accepted += len(summary.get("processed") or [])
            rejected += len(summary.get("errors") or [])
            skipped += len(summary.get("skipped") or [])
            for message in summary.get("errors") or []:
                if len(reject_messages) < 5:
                    reject_messages.append(str(message)[:200])
            for item in batch:
                pushed_types.add(str(item["payload"].get("type")))
            for item in batch:
                self._pushed.add(item["key"])
            self._pending = self._pending[len(batch) :]
            pushed += len(batch)
            await self._async_save_pending()

        self._last_push_count = pushed
        if pushed:
            await self._async_save_pushed()
            _LOGGER.debug("Pushed %s record(s) to SparkyFitness", pushed)
            self._last_push = {
                "at": datetime.now(UTC).isoformat(),
                "endpoint": client.endpoint,
                "records": pushed,
                "accepted": accepted,
                "rejected": rejected,
                "skipped": skipped,
                "types": sorted(pushed_types),
                "rejections": reject_messages,
            }
            await self._async_validate_sparky(client)
            if rejected or skipped:
                _LOGGER.warning(
                    "SparkyFitness accepted %s, rejected %s, skipped %s record(s): %s",
                    accepted,
                    rejected,
                    skipped,
                    reject_messages[:2],
                )

    async def async_backfill_frames(self) -> None:
        """Re-decode persisted frames so records an older build dropped recover.

        Frames are saved before decoding, so this is a no-op for records that
        already reached the stores: the SparkyFitness keys deduplicate them.
        """
        if self._backfilled:
            return
        self._backfilled = True
        await self._async_load_frames()
        records: list[RingRecord] = []
        for item in self._frames:
            try:
                frame = parse_frame(bytes.fromhex(item))
            except ValueError:
                continue
            if frame is None:
                continue
            record = decode_record(frame)
            if record is not None:
                records.append(record)
        if not records:
            return
        records = self._collapse_sleep(records)
        await self._async_remember(records)
        await self._async_enqueue(records)
        _LOGGER.info("Backfilled %s record(s) from %s stored frame(s)", len(records), len(self._frames))
        if self.sparky_enabled:
            await self._async_flush()

    async def _async_update_data(self) -> RingSnapshot:
        if self._ota_in_progress:
            return self.data or RingSnapshot()
        self._in_flight = True
        self._last_attempt = time.monotonic()
        try:
            try:
                snapshot = await async_collect(
                    self.hass,
                    self.address,
                    collect_seconds=self.collect_seconds,
                    realtime=self.realtime,
                    profile=self._profile_from_options(),
                    cycle=self._cycle_from_options(),
                    time_commands=self.model.time_commands,
                )
            except RingConnectionError as err:
                raise UpdateFailed(str(err)) from err

            if snapshot.raw_frames:
                await self._async_append_frames(snapshot.raw_frames)

            await self._async_update_model(snapshot.device_info)
            await self._async_remember_device(snapshot)
            records = self._collapse_sleep(snapshot.records)
            await self._async_remember(records)

            if records:
                await self._async_enqueue(records)
            if self.sparky_enabled:
                await self._async_flush()

            return snapshot
        finally:
            self._in_flight = False

    @callback
    def notify_advertisement(self) -> None:
        """Retry promptly when a proxy hears the ring after a failed attempt.

        The ring advertises rarely and weakly, so waiting for the next scheduled
        poll can miss it entirely. Reacting to a fresh advertisement connects
        while a scanner still holds the device.
        """
        if self.last_update_success or self._in_flight or self._ota_in_progress:
            return
        if time.monotonic() - self._last_attempt < ADVERT_RETRY_GAP:
            return
        self.hass.async_create_task(self.async_request_refresh())
