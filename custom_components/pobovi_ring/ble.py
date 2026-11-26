"""BLE session handling for the POBOVi Ring."""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime

from bleak import BleakClient, BleakError
from bleak_retry_connector import (
    BleakClientWithServiceCache,
    BleakNotFoundError,
    BleakOutOfConnectionSlotsError,
    establish_connection,
)
from homeassistant.components.bluetooth import (
    BluetoothReachabilityIntent,
    async_address_reachability_diagnostics,
    async_last_service_info,
    async_scanner_devices_by_address,
)
from homeassistant.core import HomeAssistant

from .const import (
    CHAR_BATTERY_UUID,
    CHAR_NOTIFY_UUID,
    CHAR_WRITE_UUID,
    CMD_DEVICE_INFO,
    CMD_FIND_RING,
    DEFAULT_COLLECT_SECONDS,
    DEVINFO_FIRMWARE_UUID,
    DEVINFO_HARDWARE_UUID,
    DEVINFO_MANUFACTURER_UUID,
    DEVINFO_MODEL_UUID,
    DEVINFO_SERIAL_UUID,
    DEVINFO_SOFTWARE_UUID,
    FRAME_DIR_ACK,
    FRAME_HEADER,
    GCTL_STRESS,
    METRIC_HRV,
    METRIC_SPO2,
    METRIC_TEMPERATURE,
    PPG_FUNC_HR,
)
from .protocol import (
    RingFrame,
    RingRecord,
    build_ack,
    build_connection_priority,
    build_device_info_request,
    build_find_ring,
    build_gctl,
    build_ppg,
    build_time_sync,
    build_user_info,
    build_women_health,
    build_zone_time,
    decode_device_info,
    decode_record,
    parse_frame,
    ppg_function,
)

_LOGGER = logging.getLogger(__name__)

EXTRA_REALTIME_METRICS = (METRIC_HRV, METRIC_SPO2, METRIC_TEMPERATURE)

ATTEMPT_TIMEOUT = 15
TOTAL_BUDGET = 90
ROUND_DELAY = 4

CANCELLED_HINT = (
    "The proxy cancelled the connection. The ring advertises only every "
    "30-80 seconds and accepts a single connection: if the phone app is "
    "connected or the ring is asleep, every attempt fails. Move the ring near "
    "a proxy with 'bluetooth_proxy: active: true' and make sure the vendor app "
    "is closed."
)

NO_CANDIDATES_HINT = (
    "No connectable proxy reported the ring during the attempt. Home Assistant "
    "drops advertisements after about 3 minutes, and ESP32 proxies listen for "
    "only ~9% of the time by default. Widen the scan window on your proxies "
    "(esp32_ble_tracker: scan_parameters: interval: 320ms, window: 300ms) and "
    "put a connectable proxy in the same room as the ring - these rings "
    "transmit very weakly."
)


class RingConnectionError(Exception):
    """Raised when the ring cannot be reached."""


@dataclass(slots=True)
class RingSnapshot:
    """Result of one synchronisation session."""

    battery: int | None = None
    records: list[RingRecord] = field(default_factory=list)
    device_info: dict[str, str] = field(default_factory=dict)
    frames_seen: int = 0
    proxy: str | None = None
    rssi: int | None = None
    command_counts: dict[int, int] = field(default_factory=dict)
    raw_frames: list[str] = field(default_factory=list)
    connected_via: str | None = None
    last_sync: datetime = field(default_factory=lambda: datetime.now(UTC))


async def _read_battery(client: BleakClient) -> int | None:
    try:
        data = await client.read_gatt_char(CHAR_BATTERY_UUID)
    except (BleakError, TimeoutError, EOFError, OSError) as err:
        _LOGGER.debug("Battery read failed: %s", err)
        return None
    if not data:
        return None
    return int(data[0])


async def _read_device_info(client: BleakClient) -> dict[str, str]:
    info: dict[str, str] = {}
    for key, uuid in (
        ("model", DEVINFO_MODEL_UUID),
        ("serial", DEVINFO_SERIAL_UUID),
        ("manufacturer", DEVINFO_MANUFACTURER_UUID),
        ("firmware", DEVINFO_FIRMWARE_UUID),
        ("hardware", DEVINFO_HARDWARE_UUID),
        ("software", DEVINFO_SOFTWARE_UUID),
    ):
        try:
            raw = await client.read_gatt_char(uuid)
        except (BleakError, TimeoutError, EOFError, OSError):
            continue
        text = raw.rstrip(b"\x00").decode(errors="replace").strip()
        if text:
            info[key] = text
    return info


def _candidates(hass: HomeAssistant, address: str) -> list[tuple[object, int, str]]:
    """Return connectable devices for the ring, strongest signal first."""
    result: list[tuple[object, int, str]] = []
    for entry in async_scanner_devices_by_address(hass, address, connectable=True):
        device = getattr(entry, "device", None)
        if device is None:
            continue
        advertisement = getattr(entry, "advertisement", None)
        rssi = getattr(advertisement, "rssi", None)
        scanner = getattr(entry, "scanner", None)
        name = getattr(scanner, "name", None) or address
        result.append((device, rssi if isinstance(rssi, int) else -999, str(name)))

    if not result:
        # The per-scanner lookup can miss a device that is still in the
        # manager's connectable history, so fall back to that.
        info = async_last_service_info(hass, address, connectable=True)
        if info is not None:
            rssi = getattr(info, "rssi", None)
            result.append(
                (
                    info.device,
                    rssi if isinstance(rssi, int) else -999,
                    f"{info.source} (history)",
                )
            )

    result.sort(key=lambda item: item[1], reverse=True)
    return result


async def _async_connect(hass: HomeAssistant, address: str) -> tuple[BleakClient, str, int | None]:
    """Connect to the ring, retrying across proxies within a time budget."""
    deadline = time.monotonic() + TOTAL_BUDGET
    last_error = "no connectable proxy has seen the ring"
    slots_exhausted = False
    saw_candidate = False
    explained = False

    while time.monotonic() < deadline:
        candidates = _candidates(hass, address)
        if not candidates:
            if not explained:
                explained = True
                _LOGGER.debug(
                    "No connectable candidate for %s: %s",
                    address,
                    async_address_reachability_diagnostics(
                        hass, address, BluetoothReachabilityIntent.CONNECTION
                    ),
                )
            _LOGGER.debug("No connectable scanner has seen %s yet, waiting", address)
            await asyncio.sleep(ROUND_DELAY)
            continue
        saw_candidate = True
        for device, rssi, scanner_name in candidates:
            remaining = int(deadline - time.monotonic())
            if remaining <= 1:
                break
            try:
                client = await establish_connection(
                    BleakClientWithServiceCache,
                    device,
                    address,
                    max_attempts=2,
                    use_services_cache=True,
                    timeout=min(ATTEMPT_TIMEOUT, remaining),
                )
            except BleakOutOfConnectionSlotsError:
                slots_exhausted = True
                last_error = f"{scanner_name}: proxy has no free connection slot"
                continue
            except BleakNotFoundError as err:
                last_error = f"{scanner_name}: {err}"
                continue
            except (BleakError, TimeoutError, EOFError, OSError) as err:
                last_error = f"{scanner_name} ({rssi} dBm): {type(err).__name__}: {err}"
                _LOGGER.debug("Connect via %s failed: %s", scanner_name, last_error)
                continue
            _LOGGER.debug("Connected to %s via %s (%s dBm)", address, scanner_name, rssi)
            return client, scanner_name, (rssi if rssi > -200 else None)
        await asyncio.sleep(ROUND_DELAY)

    if not saw_candidate:
        raise RingConnectionError(f"Could not connect. {NO_CANDIDATES_HINT}")
    if slots_exhausted:
        raise RingConnectionError(
            f"Could not connect. {last_error}. Raise 'connection_slots' on the "
            "nearest bluetooth_proxy or add another proxy near the ring."
        )
    if "cancel" in last_error.lower():
        last_error = f"{last_error}. {CANCELLED_HINT}"
    raise RingConnectionError(f"Could not connect. {last_error}")


async def async_find_ring(hass: HomeAssistant, address: str, seconds: int) -> None:
    """Ask the ring to buzz, mirroring the app's notified, retried write.

    The vendor app enables notifications and expects the ring to acknowledge
    the find command (55 BB D0); a single unacknowledged write after connect is
    ignored by the firmware in practice.
    """
    client, _proxy, _rssi = await _async_connect(hass, address)
    acked = asyncio.Event()

    def on_notify(_char, data: bytearray) -> None:
        raw = bytes(data)
        if (
            len(raw) >= 3
            and raw[0] == FRAME_HEADER
            and raw[1] == FRAME_DIR_ACK
            and raw[2] == CMD_FIND_RING
        ):
            acked.set()

    try:
        await client.start_notify(CHAR_NOTIFY_UUID, on_notify)
        await asyncio.sleep(0.2)
        try:
            characteristic = client.services.get_characteristic(CHAR_WRITE_UUID)
            _LOGGER.debug("Find write characteristic properties: %s", characteristic.properties)
        except (AttributeError, KeyError):
            pass

        packet = build_find_ring(seconds)
        for _attempt in range(3):
            try:
                await client.write_gatt_char(CHAR_WRITE_UUID, packet, response=True)
            except (BleakError, ValueError, TypeError):
                await client.write_gatt_char(CHAR_WRITE_UUID, packet, response=False)
            try:
                await asyncio.wait_for(acked.wait(), 1.2)
                break
            except TimeoutError:
                continue
        else:
            raise RingConnectionError("the ring did not acknowledge the find command")
        await asyncio.sleep(0.8)
    except (BleakError, TimeoutError, EOFError, OSError) as err:
        raise RingConnectionError(str(err)) from err
    finally:
        with suppress(BleakError, TimeoutError, EOFError, OSError):
            await client.stop_notify(CHAR_NOTIFY_UUID)
        with suppress(BleakError, TimeoutError, EOFError, OSError):
            await client.disconnect()


async def async_collect(
    hass: HomeAssistant,
    address: str,
    collect_seconds: int = DEFAULT_COLLECT_SECONDS,
    realtime: bool = False,
    profile: dict | None = None,
    cycle: dict | None = None,
    time_commands: tuple[str, ...] = ("legacy", "zone"),
) -> RingSnapshot:
    """Connect to the ring, gather data, and disconnect."""
    snapshot = RingSnapshot()
    records: dict[tuple[str, str], RingRecord] = {}
    ack_queue: asyncio.Queue[int] = asyncio.Queue()
    stop_ack = asyncio.Event()

    def on_notify(_char, data: bytearray) -> None:
        raw = bytes(data)
        # The device-info reply arrives in the ACK direction but carries a
        # payload, so it would otherwise be discarded as a plain ACK.
        if len(raw) >= 4 and raw[0] == 0x55 and raw[1] == FRAME_DIR_ACK:
            if raw[2] == CMD_DEVICE_INFO:
                snapshot.device_info.update(
                    decode_device_info(RingFrame(cmd=raw[2], payload=raw[4 : 4 + raw[3]]))
                )
            return
        frame: RingFrame | None = parse_frame(raw)
        if frame is None:
            return
        snapshot.frames_seen += 1
        snapshot.command_counts[frame.cmd] = snapshot.command_counts.get(frame.cmd, 0) + 1
        if len(snapshot.raw_frames) < 200:
            snapshot.raw_frames.append(frame.hex)
        ack_queue.put_nowait(frame.cmd)
        record = decode_record(frame)
        if record is not None:
            records[(record.metric, record.timestamp.isoformat())] = record
        elif frame.cmd == CMD_DEVICE_INFO:
            snapshot.device_info.update(decode_device_info(frame))

    async def ack_worker(client: BleakClient) -> None:
        while not stop_ack.is_set():
            try:
                cmd = await asyncio.wait_for(ack_queue.get(), timeout=0.5)
            except TimeoutError:
                continue
            try:
                await client.write_gatt_char(CHAR_WRITE_UUID, build_ack(cmd), response=False)
            except (BleakError, TimeoutError, EOFError, OSError) as err:
                _LOGGER.debug("ACK 0x%02X failed: %s", cmd, err)

    client, snapshot.proxy, snapshot.rssi = await _async_connect(hass, address)
    snapshot.connected_via = (
        f"{snapshot.proxy} ({snapshot.rssi} dBm)" if snapshot.rssi is not None else snapshot.proxy
    )
    try:
        await client.start_notify(CHAR_NOTIFY_UUID, on_notify)
        ack_task = asyncio.create_task(ack_worker(client))
        try:
            snapshot.battery = await _read_battery(client)

            # Clock sync also releases buffered records. Which command does that
            # depends on the firmware variant, so follow the model's list.
            for time_command in time_commands:
                frame = build_zone_time() if time_command == "zone" else build_time_sync()
                await client.write_gatt_char(CHAR_WRITE_UUID, frame, response=False)
                await asyncio.sleep(0.5 if time_command == "legacy" else 0.8)
            if profile:
                try:
                    await client.write_gatt_char(
                        CHAR_WRITE_UUID, build_user_info(**profile), response=False
                    )
                    await asyncio.sleep(0.4)
                except (BleakError, TimeoutError, EOFError, OSError) as err:
                    _LOGGER.warning("Could not write ring profile: %s", err)
            if cycle:
                try:
                    await client.write_gatt_char(
                        CHAR_WRITE_UUID, build_women_health(**cycle), response=False
                    )
                    await asyncio.sleep(0.3)
                except (BleakError, TimeoutError, EOFError, OSError) as err:
                    _LOGGER.warning("Could not write cycle settings: %s", err)
            await client.write_gatt_char(CHAR_WRITE_UUID, build_device_info_request(), response=False)
            await asyncio.sleep(0.4)
            await client.write_gatt_char(CHAR_WRITE_UUID, build_connection_priority(True), response=False)

            # The ring only releases data after a measurement is requested.
            # Heart rate is always requested so every poll actually syncs.
            if realtime:
                with suppress(BleakError, TimeoutError, EOFError, OSError):
                    await client.write_gatt_char(
                        CHAR_WRITE_UUID, build_gctl(GCTL_STRESS, True), response=False
                    )
                    await asyncio.sleep(0.3)

            active_ppg = [PPG_FUNC_HR]
            if realtime:
                for metric in EXTRA_REALTIME_METRICS:
                    func = ppg_function(metric)
                    if func is not None:
                        active_ppg.append(func)
            for func in active_ppg:
                await client.write_gatt_char(CHAR_WRITE_UUID, build_ppg(func, True), response=False)
                await asyncio.sleep(0.3)

            await asyncio.sleep(collect_seconds)

            for func in active_ppg:
                with suppress(BleakError, TimeoutError, EOFError, OSError):
                    await client.write_gatt_char(CHAR_WRITE_UUID, build_ppg(func, False), response=False)

            if realtime:
                with suppress(BleakError, TimeoutError, EOFError, OSError):
                    await client.write_gatt_char(
                        CHAR_WRITE_UUID, build_gctl(GCTL_STRESS, False), response=False
                    )

            for key, value in (await _read_device_info(client)).items():
                snapshot.device_info.setdefault(key, value)
        finally:
            stop_ack.set()
            ack_task.cancel()
            with suppress(asyncio.CancelledError):
                await ack_task
            with suppress(BleakError, TimeoutError, EOFError, OSError):
                await client.stop_notify(CHAR_NOTIFY_UUID)
    except (BleakError, TimeoutError, EOFError, OSError) as err:
        raise RingConnectionError(str(err)) from err
    finally:
        with suppress(BleakError, TimeoutError, EOFError, OSError):
            await client.disconnect()

    snapshot.records = sorted(records.values(), key=lambda record: record.timestamp)
    snapshot.last_sync = datetime.now(UTC)
    return snapshot
