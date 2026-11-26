"""AMOTA firmware update support for the POBOVi Ring.

Protocol reverse engineered from the vendor app (AmOtaService):

    packet  = [len_lo, len_hi, cmd, payload..., crc32_le(payload)]
              len = payload length + 4
    cmds    1 = HEADER (first 48 bytes of the .bin)
            2 = DATA   (512-byte chunks)
            3 = VERIFY (no payload)
            4 = RESET  (no payload)
    write   chunks of at most 20 bytes to the AMOTA write characteristic,
            one command response per packet on the notify characteristic.

Everything here is deliberately conservative: it refuses to start unless the
link, battery and version checks pass, it never retries on its own, and it
reports what the ring says afterwards instead of assuming success.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from urllib.parse import urlparse

from aiohttp import ClientError
from bleak import BleakError
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .ble import RingConnectionError, _async_connect
from .const import (
    AMOTA_NOTIFY_UUID,
    AMOTA_WRITE_UUID,
    CHAR_BATTERY_UUID,
    DEVINFO_SOFTWARE_UUID,
    FW_ALLOWED_HOSTS,
    FW_INFO_URL,
    OTA_CHUNK_BYTES,
    OTA_CMD_DATA,
    OTA_CMD_HEADER,
    OTA_CMD_RESET,
    OTA_CMD_VERIFY,
    OTA_HEADER_TIMEOUT,
    OTA_MAX_FIRMWARE_BYTES,
    OTA_MIN_BATTERY,
    OTA_MIN_FIRMWARE_BYTES,
    OTA_MIN_RSSI,
    OTA_RESPONSE_TIMEOUT,
    OTA_VERIFY_TIMEOUT,
    OTA_WRITE_BYTES,
    OTA_WRITE_DELAY,
)
from .protocol import (
    FirmwareImage,
    build_ota_packet,
    parse_firmware_image,
    parse_firmware_version,
)

_LOGGER = logging.getLogger(__name__)

StatusCallback = Callable[[str, dict], None]
ProgressCallback = Callable[[int], None]


class OtaError(Exception):
    """Raised when a firmware update cannot be performed safely."""


@dataclass(slots=True)
class FirmwareInfo:
    url: str
    version: str
    note: str


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in FW_ALLOWED_HOSTS:
        raise OtaError(
            f"refusing firmware from {parsed.hostname or 'unknown host'}; "
            f"only {', '.join(FW_ALLOWED_HOSTS)} are allowed"
        )


async def async_fetch_firmware_info(hass: HomeAssistant, url: str | None = None) -> FirmwareInfo:
    """Ask the vendor endpoint for the current firmware, or use an explicit URL."""
    if url:
        _validate_url(url)
        return FirmwareInfo(url=url, version="", note="explicit URL")

    session = async_get_clientsession(hass)
    try:
        async with session.get(FW_INFO_URL, timeout=30) as response:
            response.raise_for_status()
            payload = await response.json(content_type=None)
    except (ClientError, TimeoutError, ValueError) as err:
        raise OtaError(f"could not query the firmware endpoint: {err}") from err

    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict) or not data.get("packageUrl"):
        raise OtaError("firmware endpoint returned no packageUrl")

    _validate_url(data["packageUrl"])
    return FirmwareInfo(
        url=data["packageUrl"],
        version=str(data.get("versions") or ""),
        note=str(data.get("note") or ""),
    )


async def async_download_firmware(hass: HomeAssistant, url: str) -> bytes:
    """Download a firmware image and reject implausible sizes."""
    session = async_get_clientsession(hass)
    try:
        async with session.get(url, timeout=120) as response:
            response.raise_for_status()
            data = await response.read()
    except (ClientError, TimeoutError) as err:
        raise OtaError(f"firmware download failed: {err}") from err

    if not OTA_MIN_FIRMWARE_BYTES <= len(data) <= OTA_MAX_FIRMWARE_BYTES:
        raise OtaError(f"firmware size {len(data)} bytes is out of range")
    return data


async def _read_version(client) -> str | None:
    try:
        raw = await client.read_gatt_char(DEVINFO_SOFTWARE_UUID)
    except (BleakError, TimeoutError, EOFError, OSError):
        return None
    text = raw.rstrip(b"\x00").decode(errors="replace").strip()
    return text if text.startswith("V") else None


async def _read_battery(client) -> int | None:
    try:
        raw = await client.read_gatt_char(CHAR_BATTERY_UUID)
    except (BleakError, TimeoutError, EOFError, OSError):
        return None
    return int(raw[0]) if raw else None


class _AmotaSession:
    """Runs the AMOTA command/response exchange on an open connection."""

    def __init__(self, client) -> None:
        self._client = client
        self._queue: asyncio.Queue[tuple[int, int, bytes]] = asyncio.Queue()

    def _on_notify(self, _char, data: bytearray) -> None:
        raw = bytes(data)
        if len(raw) < 4:
            return
        self._queue.put_nowait((raw[2], raw[3], raw))

    async def _write(self, packet: bytes) -> None:
        for offset in range(0, len(packet), OTA_WRITE_BYTES):
            await self._client.write_gatt_char(
                AMOTA_WRITE_UUID, packet[offset : offset + OTA_WRITE_BYTES], response=False
            )
            await asyncio.sleep(OTA_WRITE_DELAY)

    async def _wait(self, cmd: int, wait_seconds: float) -> bytes:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + wait_seconds
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise OtaError(f"timed out waiting for the ring to acknowledge command {cmd}")
            try:
                got_cmd, status, raw = await asyncio.wait_for(self._queue.get(), remaining)
            except TimeoutError as err:
                raise OtaError(
                    f"timed out waiting for the ring to acknowledge command {cmd}"
                ) from err
            if got_cmd != cmd:
                _LOGGER.debug("Ignoring OTA response for command %s", got_cmd)
                continue
            if status != 0:
                raise OtaError(f"the ring rejected command {cmd} with status {status}")
            return raw

    async def flash(self, image: FirmwareImage, progress: ProgressCallback) -> None:
        await self._client.start_notify(AMOTA_NOTIFY_UUID, self._on_notify)
        await asyncio.sleep(0.2)
        try:
            await self._write(build_ota_packet(OTA_CMD_HEADER, image.header))
            await self._wait(OTA_CMD_HEADER, OTA_HEADER_TIMEOUT)
            _LOGGER.info("OTA: header accepted, sending %s bytes", len(image.payload))

            total = len(image.payload)
            sent = 0
            last_percent = -1
            while sent < total:
                chunk = image.payload[sent : sent + OTA_CHUNK_BYTES]
                await self._write(build_ota_packet(OTA_CMD_DATA, chunk))
                await self._wait(OTA_CMD_DATA, OTA_RESPONSE_TIMEOUT)
                sent += len(chunk)
                percent = int(sent * 100 / total)
                if percent != last_percent and (percent % 2 == 0 or sent == total):
                    last_percent = percent
                    progress(percent)

            await self._write(build_ota_packet(OTA_CMD_VERIFY, b""))
            await self._wait(OTA_CMD_VERIFY, OTA_RESPONSE_TIMEOUT)
            _LOGGER.info("OTA: image verified by the ring, resetting")

            with suppress(OtaError, BleakError, TimeoutError, EOFError, OSError):
                await self._write(build_ota_packet(OTA_CMD_RESET, b""))
                await self._wait(OTA_CMD_RESET, 10)
        finally:
            with suppress(BleakError, TimeoutError, EOFError, OSError):
                await self._client.stop_notify(AMOTA_NOTIFY_UUID)


async def _async_verify_version(
    hass: HomeAssistant, address: str, target: str
) -> tuple[bool, str | None]:
    """Reconnect after the reset and read back the firmware version."""
    deadline = asyncio.get_running_loop().time() + OTA_VERIFY_TIMEOUT
    while asyncio.get_running_loop().time() < deadline:
        await asyncio.sleep(10)
        try:
            client, _proxy, _rssi = await _async_connect(hass, address)
        except RingConnectionError:
            continue
        try:
            reported = await _read_version(client)
        finally:
            with suppress(BleakError, TimeoutError, EOFError, OSError):
                await client.disconnect()
        if reported:
            return reported == target, reported
    return False, None


async def async_flash_firmware(
    hass: HomeAssistant,
    address: str,
    *,
    url: str | None = None,
    expected_version: str | None = None,
    allow_downgrade: bool = False,
    dry_run: bool = True,
    known_version: str | None = None,
    on_status: StatusCallback | None = None,
    on_progress: ProgressCallback | None = None,
) -> dict:
    """Download, validate and flash a firmware image."""

    def status(state: str, payload: dict) -> None:
        if on_status is not None:
            on_status(state, payload)

    def progress(percent: int) -> None:
        if on_progress is not None:
            on_progress(percent)

    status("downloading", {})
    info = await async_fetch_firmware_info(hass, url)
    if expected_version and info.version and expected_version != info.version:
        raise OtaError(
            f"the vendor now offers {info.version}, not the requested {expected_version}"
        )
    data = await async_download_firmware(hass, info.url)
    try:
        image = parse_firmware_image(data)
    except ValueError as err:
        raise OtaError(str(err)) from err
    checks: dict = {
        "source": info.url,
        "target_version": info.version or None,
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "release_note": info.note or None,
    }
    status("downloaded", checks)

    client, proxy, rssi = await _async_connect(hass, address)
    try:
        checks["proxy"] = proxy
        checks["rssi"] = rssi
        if rssi is None or rssi < OTA_MIN_RSSI:
            raise OtaError(
                f"signal is {rssi} dBm; flashing needs better than {OTA_MIN_RSSI} dBm"
            )

        battery = await _read_battery(client)
        checks["battery"] = battery
        if battery is not None and battery < OTA_MIN_BATTERY:
            raise OtaError(f"battery is {battery}%; flashing needs at least {OTA_MIN_BATTERY}%")

        current = await _read_version(client) or known_version
        checks["current_version"] = current
        if info.version and not current and not allow_downgrade:
            raise OtaError(
                "could not read the ring's current firmware version; "
                "refusing to flash without it (allow_downgrade bypasses this)"
            )
        if info.version and current:
            current_key = parse_firmware_version(current)
            target_key = parse_firmware_version(info.version)
            if current_key is not None and target_key is not None:
                if target_key == current_key and not allow_downgrade:
                    raise OtaError(f"the ring is already on {current}")
                if target_key < current_key and not allow_downgrade:
                    raise OtaError(
                        f"refusing to downgrade from {current} to {info.version}"
                    )

        if dry_run:
            status("dry_run", checks)
            return {
                "status": "dry_run",
                "message": "all checks passed; nothing was flashed",
                "checks": checks,
            }

        status("flashing", checks)
        session = _AmotaSession(client)
        await session.flash(image, progress)
        status("verifying", checks)
    finally:
        with suppress(BleakError, TimeoutError, EOFError, OSError):
            await client.disconnect()

    if info.version:
        verified, reported = await _async_verify_version(hass, address, info.version)
        checks["reported_version"] = reported
        checks["verified"] = verified
        if not verified:
            status("unverified", checks)
            return {
                "status": "unverified",
                "message": (
                    f"flash completed but the ring reported {reported or 'no version'}; "
                    f"expected {info.version}"
                ),
                "checks": checks,
            }
    else:
        checks["verified"] = None

    status("done", checks)
    return {
        "status": "success",
        "message": f"firmware {info.version or ''} installed".strip(),
        "checks": checks,
    }
