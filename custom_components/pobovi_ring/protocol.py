"""Codec for the POBOVi Ring BLE protocol.

Wire format (reverse engineered from POBOVi Ring V1.2.63):

    host -> ring : 55 AA <cmd> <len> <payload...>
    ring -> host : 55 AA <cmd> <len> <payload...>
    host ack     : 55 BB <cmd> 00

History and realtime records carry a little-endian uint32 Unix timestamp as
the first four payload bytes, followed by the metric values.
"""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Final
from zlib import crc32

from .const import (
    CMD_ACTIVE_TIME,
    CMD_CALORIES,
    CMD_CONNECTION_PRIORITY,
    CMD_DEVICE_INFO,
    CMD_FIND_RING,
    CMD_GCTL,
    CMD_PPG_HR,
    CMD_PPG_HRV,
    CMD_PPG_SPO2,
    CMD_PPG_SWITCH,
    CMD_RR,
    CMD_SLEEP,
    CMD_STEPS,
    CMD_STRESS,
    CMD_SYSTEM_TIME,
    CMD_SYSTEM_TIME_ZONE,
    CMD_TEMPERATURE,
    CMD_USER_INFO,
    CMD_WOMENS_HEALTH,
    FRAME_DIR_ACK,
    FRAME_DIR_DATA,
    FRAME_HEADER,
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
    OTA_HEADER_BYTES,
    PPG_FUNC_HR,
    PPG_FUNC_HRV,
    PPG_FUNC_SPO2,
    PPG_FUNC_TEMPERATURE,
)

MIN_PLAUSIBLE_TIMESTAMP: Final = 1577836800
MAX_PLAUSIBLE_TIMESTAMP: Final = 4102444800

SPARKY_TYPES: Final[dict[str, str]] = {
    METRIC_STEPS: "ring_steps",
    METRIC_CALORIES: "ring_calories",
    METRIC_ACTIVE_MINUTES: "active_minutes",
    METRIC_HEART_RATE: "heart_rate",
    METRIC_HRV: "HRV",
    METRIC_SPO2: "oxygen_saturation",
    METRIC_STRESS: "Stress",
    METRIC_RESPIRATORY: "ring_respiration",
}

SPARKY_UNITS: Final[dict[str, str]] = {
    METRIC_STEPS: "steps",
    METRIC_CALORIES: "kcal",
    METRIC_RESPIRATORY: "breaths/min",
}


@dataclass(slots=True)
class RingFrame:
    """A single decoded frame from the ring."""

    cmd: int
    payload: bytes

    @property
    def hex(self) -> str:
        """Return the full frame as hex for diagnostics."""
        return (bytes([FRAME_HEADER, FRAME_DIR_DATA, self.cmd, len(self.payload)]) + self.payload).hex(" ")


@dataclass(slots=True)
class RingRecord:
    """One time-stamped metric sample."""

    metric: str
    value: float
    timestamp: datetime
    raw: str
    extra: dict[str, float | int | str] = field(default_factory=dict)

    def _sleep_stage_events(self) -> list[dict[str, object]]:
        """Expand the stage summary into SparkyFitness stage events.

        Stage types, from the app's SleepState enum: 0 deep, 1 light,
        2 REM, 3 awake. The ring lists consecutive stages from bedtime.
        """
        names = {0: "deep", 1: "light", 2: "rem", 3: "awake"}
        cursor = self.timestamp
        events: list[dict[str, object]] = []
        for item in str(self.extra.get("stages") or "").split(","):
            if not item:
                continue
            try:
                kind, minutes = (int(part) for part in item.split(":"))
            except ValueError:
                continue
            if kind not in names or minutes <= 0:
                continue
            end = cursor + timedelta(minutes=minutes)
            events.append(
                {
                    "stage_type": names[kind],
                    "start_time": cursor.isoformat(),
                    "end_time": end.isoformat(),
                    "duration_in_seconds": minutes * 60,
                }
            )
            cursor = end
        return events

    def as_sparky(self, source: str) -> dict[str, object] | None:
        """Return the record in SparkyFitness health-data form.

        Metrics whose decoding is not yet verified are deliberately not pushed,
        so unconfirmed values never reach SparkyFitness.
        """
        if self.metric == METRIC_SLEEP:
            payload: dict[str, object] = {
                "type": "SleepSession",
                "timestamp": self.timestamp.isoformat(),
                "bedtime": self.timestamp.isoformat(),
                "wake_time": self.extra.get("end"),
                "duration_in_seconds": self.extra.get("duration_seconds"),
                "sleep_score": self.extra.get("score", 0),
                "source": source,
            }
            if events := self._sleep_stage_events():
                payload["stage_events"] = events
            return payload
        sparky_type = SPARKY_TYPES.get(self.metric)
        if sparky_type is None:
            return None
        payload: dict[str, object] = {
            "type": sparky_type,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "source": source,
        }
        if (unit := SPARKY_UNITS.get(self.metric)) is not None:
            payload["unit"] = unit
        return payload


@dataclass(slots=True)
class FirmwareImage:
    """A validated AMOTA firmware container."""

    data: bytes
    header: bytes
    payload: bytes
    declared_size: int


def build_ota_packet(cmd: int, payload: bytes) -> bytes:
    """Build one AMOTA command packet.

    Layout mirrors the vendor app's AmOtaService: a 3-byte header (length,
    command), the payload, then a little-endian CRC-32 of the payload.
    """
    length = len(payload) + 4
    checksum = crc32(payload) & 0xFFFFFFFF
    return (
        bytes([length & 0xFF, (length >> 8) & 0xFF, cmd])
        + payload
        + checksum.to_bytes(4, "little")
    )


def parse_firmware_image(data: bytes) -> FirmwareImage:
    """Validate an AMOTA container and split it into header and payload."""
    if len(data) <= OTA_HEADER_BYTES:
        raise ValueError("firmware file is too small to contain an AMOTA header")
    header = data[:OTA_HEADER_BYTES]
    payload = data[OTA_HEADER_BYTES:]
    declared = int.from_bytes(header[8:12], "little")
    if declared != len(payload):
        raise ValueError(
            f"firmware header declares {declared} payload bytes but the file holds {len(payload)}"
        )
    return FirmwareImage(data=data, header=header, payload=payload, declared_size=declared)


def parse_firmware_version(text: str | None) -> int | None:
    """Extract the trailing build number from a firmware version string."""
    if not text:
        return None
    match = re.search(r"-(\d{6,})$", text.strip())
    return int(match.group(1)) if match else None


def build_frame(cmd: int, payload: bytes = b"") -> bytes:
    """Build a host -> ring frame."""
    return bytes([FRAME_HEADER, FRAME_DIR_DATA, cmd, len(payload)]) + payload


def build_ack(cmd: int) -> bytes:
    """Build the acknowledgement for a ring frame."""
    return bytes([FRAME_HEADER, FRAME_DIR_ACK, cmd, 0x00])


def build_time_sync(now: datetime | None = None) -> bytes:
    """Build the legacy clock sync frame (0x30).

    The last byte is the offset in whole *hours* (RingUtil.getZone()).
    Current firmware ignores this; prefer build_zone_time().
    """
    now = now or datetime.now().astimezone()
    offset = now.utcoffset()
    if offset is None:
        now = now.astimezone()
        offset = now.utcoffset()
    hours = int(offset.total_seconds() // 3600) if offset else 0
    payload = bytes(
        [
            (now.year - 1900) & 0xFF,
            now.month,
            now.day,
            now.hour,
            now.minute,
            now.second,
            hours & 0xFF,
        ]
    )
    return build_frame(CMD_SYSTEM_TIME, payload)


def build_zone_time(now: datetime | None = None) -> bytes:
    """Build the zone-time frame (0x51).

    This is the clock sync the app actually sends, and it is what makes the
    ring release buffered records. The offset is minutes east of UTC including
    DST, stored as a little-endian int16 (RingUtil.getZoneTime()).
    """
    now = now or datetime.now().astimezone()
    offset = now.utcoffset()
    if offset is None:
        now = now.astimezone()
        offset = now.utcoffset()
    minutes = int(offset.total_seconds() // 60) if offset else 0
    value = minutes & 0xFFFF
    payload = bytes(
        [
            (now.year - 1900) & 0xFF,
            now.month,
            now.day,
            now.hour,
            now.minute,
            now.second,
            value & 0xFF,
            (value >> 8) & 0xFF,
        ]
    )
    return build_frame(CMD_SYSTEM_TIME_ZONE, payload)


def build_device_info_request() -> bytes:
    """Build the device information request."""
    return build_frame(CMD_DEVICE_INFO)


def build_connection_priority(high: bool = True) -> bytes:
    """Build the connection priority request."""
    from .const import PRIORITY_HIGH, PRIORITY_LOW_POWER

    return build_frame(CMD_CONNECTION_PRIORITY, bytes([PRIORITY_HIGH if high else PRIORITY_LOW_POWER]))


def build_ppg(func: int, enable: bool) -> bytes:
    """Build a PPG (realtime sensor) start/stop frame."""
    return build_frame(CMD_PPG_SWITCH, bytes([0x02, func, 0x01 if enable else 0x00]))


def build_user_info(
    *,
    age: int,
    gender: int,
    height_cm: float,
    weight_kg: float,
    birth_year: int,
    birth_month: int,
    birth_day: int,
    stride_cm: float = 0.0,
    hr: float = 0.0,
    hr_rest: float = 0.0,
    vo2max: float = 0.0,
    women_year: int = 0,
    women_month: int = 0,
    women_day: int = 0,
    women_duration: int = 0,
    women_cycle: int = 0,
) -> bytes:
    """Build the user-profile frame (cmd 0x31).

    Mirrors BleRingDataPackager.updateUserInfo: eight little-endian float32
    values, then the birthday as year-1900/month/day, then the five optional
    women's-health bytes. The vendor app always sends hr/hr_rest/vo2max as 0.
    """
    floats = (age, gender, height_cm, weight_kg, hr, hr_rest, vo2max, stride_cm)
    payload = b"".join(struct.pack("<f", value) for value in floats)
    payload += bytes(
        [
            (birth_year - 1900) & 0xFF,
            birth_month & 0xFF,
            birth_day & 0xFF,
            women_year & 0xFF,
            women_month & 0xFF,
            women_day & 0xFF,
            women_duration & 0xFF,
            women_cycle & 0xFF,
        ]
    )
    return build_frame(CMD_USER_INFO, payload)


def build_find_ring(seconds: int = 120) -> bytes:
    """Build the find-my-ring frame (cmd 0xD0) with a 1-byte duration."""
    clamped = max(1, min(255, int(seconds)))
    return build_frame(CMD_FIND_RING, bytes([0x01, clamped]))


def build_women_health(
    *,
    last_year: int,
    last_month: int,
    last_day: int,
    duration: int,
    cycle: int,
) -> bytes:
    """Build the cycle-tracking frame (cmd 0x15).

    The year on the wire is year - 1900, matching
    BleRingHandler.sendWomenHealthData (which subtracts 1900 before the byte
    cast). Payload: last period year/month/day, period length, cycle length.
    """
    payload = bytes(
        [
            (last_year - 1900) & 0xFF,
            last_month & 0xFF,
            last_day & 0xFF,
            duration & 0xFF,
            cycle & 0xFF,
        ]
    )
    return build_frame(CMD_WOMENS_HEALTH, payload)


def build_gctl(gctl: int, enable: bool) -> bytes:
    """Build a GCTL switch frame (calorie or pressure channel)."""
    return build_frame(CMD_GCTL, bytes([0x02, gctl, 0x01 if enable else 0x00]))


def parse_frame(data: bytes) -> RingFrame | None:
    """Parse a raw notification into a frame, ignoring ACKs and noise."""
    if len(data) < 4 or data[0] != FRAME_HEADER or data[1] != FRAME_DIR_DATA:
        return None
    declared = data[3]
    payload = bytes(data[4 : 4 + declared])
    return RingFrame(cmd=data[2], payload=payload)


def _parse_timestamp(payload: bytes) -> datetime | None:
    if len(payload) < 4:
        return None
    stamp = int.from_bytes(payload[:4], "little")
    if not MIN_PLAUSIBLE_TIMESTAMP <= stamp <= MAX_PLAUSIBLE_TIMESTAMP:
        return None
    return datetime.fromtimestamp(stamp, UTC)


def _u16(payload: bytes, offset: int) -> int | None:
    if len(payload) < offset + 2:
        return None
    return int.from_bytes(payload[offset : offset + 2], "little")


def _u32(payload: bytes, offset: int) -> int | None:
    if len(payload) < offset + 4:
        return None
    return int.from_bytes(payload[offset : offset + 4], "little")


def _decode_sleep(frame: RingFrame) -> RingRecord | None:
    """Decode a sleep session (cmd 0x13).

    Layout confirmed against BleRingDataStorage.receiveData in POBOVi Ring
    V1.2.63, where each timestamp is read with bytesToULong(4) (four bytes)
    and the minimum payload length is 11:

        [0..3]   uint32 LE start timestamp (seconds)
        [4..7]   uint32 LE end timestamp   (seconds)
        [8]      pauses (osanum)
        [9]      score
        [10]     stage count N
        then N * (1 byte stage type, uint16 LE minutes)
    """
    payload = frame.payload
    if len(payload) < 11:
        return None
    start = int.from_bytes(payload[0:4], "little")
    end = int.from_bytes(payload[4:8], "little")
    if not MIN_PLAUSIBLE_TIMESTAMP <= start <= MAX_PLAUSIBLE_TIMESTAMP:
        return None
    if not start < end <= MAX_PLAUSIBLE_TIMESTAMP + 86400:
        return None
    duration_seconds = end - start
    if not 600 <= duration_seconds <= 86400:
        return None

    count = payload[10]
    stages: list[str] = []
    offset = 11
    for _ in range(count):
        if len(payload) < offset + 3:
            break
        stages.append(f"{payload[offset]}:{int.from_bytes(payload[offset + 1 : offset + 3], 'little')}")
        offset += 3

    return RingRecord(
        METRIC_SLEEP,
        duration_seconds // 60,
        datetime.fromtimestamp(start, UTC),
        frame.hex,
        {
            "end": datetime.fromtimestamp(end, UTC).isoformat(),
            "duration_seconds": duration_seconds,
            "score": payload[9],
            "pauses": payload[8],
            "segments": count,
            "stages": ",".join(stages),
        },
    )


def _decode_temperature(frame: RingFrame) -> RingRecord | None:
    """Decode a temperature reading (cmd 0x17).

    The app's BleRingDataStorage describes an 8-byte timestamp plus float32,
    but the rings send an 8-byte payload: a 4-byte little-endian timestamp
    followed by an IEEE-754 float32. Both layouts are accepted; ``layout``
    says which was used.
    """
    payload = frame.payload
    if len(payload) >= 12:
        stamp = int.from_bytes(payload[0:8], "little")
        if MIN_PLAUSIBLE_TIMESTAMP <= stamp <= MAX_PLAUSIBLE_TIMESTAMP:
            value = struct.unpack_from("<f", payload, 8)[0]
            if -20.0 <= value <= 60.0:
                return RingRecord(
                    METRIC_TEMPERATURE,
                    round(value, 2),
                    datetime.fromtimestamp(stamp, UTC),
                    frame.hex,
                    {"layout": "ts64+f32"},
                )

    if len(payload) >= 8:
        timestamp = _parse_timestamp(payload)
        if timestamp is None:
            return None
        value = struct.unpack_from("<f", payload, 4)[0]
        if not -20.0 <= value <= 60.0:
            return None
        return RingRecord(
            METRIC_TEMPERATURE,
            round(value, 2),
            timestamp,
            frame.hex,
            {"layout": "ts32+f32"},
        )
    return None


def _decode_stress(frame: RingFrame) -> RingRecord | None:
    """Decode a stress reading (cmd 0x14).

    The firmware calls this channel "pressure" (in Chinese, stress) and computes
    it with the Gomore algorithms from PPG and accelerometer data; there is no
    blood-pressure sensor in this ring. The value is a 0-100 stress level.

    The app parses an 8-byte timestamp followed by one byte, but the frames this
    ring actually produces use a 4-byte timestamp plus a uint16. Both layouts are
    accepted; ``layout`` says which was used.
    """
    payload = frame.payload
    if len(payload) >= 9:
        stamp = int.from_bytes(payload[0:8], "little")
        if MIN_PLAUSIBLE_TIMESTAMP <= stamp <= MAX_PLAUSIBLE_TIMESTAMP:
            value = payload[8]
            if value <= 100:
                return RingRecord(
                    METRIC_STRESS,
                    value,
                    datetime.fromtimestamp(stamp, UTC),
                    frame.hex,
                    {"layout": "ts64+u8"},
                )

    if len(payload) >= 6:
        timestamp = _parse_timestamp(payload)
        if timestamp is None:
            return None
        value = int.from_bytes(payload[4:6], "little")
        if value <= 100:
            return RingRecord(
                METRIC_STRESS,
                value,
                timestamp,
                frame.hex,
                {"layout": "ts32+u16"},
            )

    return None


def decode_record(frame: RingFrame) -> RingRecord | None:
    """Decode a single time-stamped metric record.

    Only fields confirmed against captured live traffic are emitted as values.
    Anything ambiguous is kept in ``extra`` so it can be verified later.
    """
    if frame.cmd == CMD_SLEEP:
        return _decode_sleep(frame)

    if frame.cmd == CMD_TEMPERATURE:
        return _decode_temperature(frame)

    if frame.cmd == CMD_STRESS:
        return _decode_stress(frame)

    timestamp = _parse_timestamp(frame.payload)
    if timestamp is None:
        return None

    payload = frame.payload
    raw = frame.hex
    extra: dict[str, float | int | str] = {}

    if frame.cmd == CMD_STEPS:
        steps = _u32(payload, 4)
        if steps is None:
            return None
        return RingRecord(METRIC_STEPS, steps, timestamp, raw)

    if frame.cmd == CMD_CALORIES:
        calories = _u16(payload, 4)
        if calories is None:
            return None
        for index, name in ((6, "value_2"), (8, "value_3")):
            value = _u16(payload, index)
            if value is not None:
                extra[name] = value
        return RingRecord(METRIC_CALORIES, calories, timestamp, raw, extra)

    if frame.cmd == CMD_RR:
        if len(payload) < 8:
            return None
        value = struct.unpack("<f", payload[4:8])[0]
        if not 2.0 <= value <= 100.0:
            return None
        return RingRecord(METRIC_RESPIRATORY, round(value, 1), timestamp, raw)

    if frame.cmd == CMD_ACTIVE_TIME:
        minutes = _u16(payload, 4)
        if minutes is None:
            return None
        return RingRecord(METRIC_ACTIVE_MINUTES, minutes, timestamp, raw)

    if frame.cmd == CMD_PPG_HR:
        if len(payload) < 5:
            return None
        return RingRecord(METRIC_HEART_RATE, payload[4], timestamp, raw)

    if frame.cmd == CMD_PPG_HRV:
        if len(payload) < 5:
            return None
        return RingRecord(METRIC_HRV, payload[4], timestamp, raw)

    if frame.cmd == CMD_PPG_SPO2:
        if len(payload) < 5:
            return None
        return RingRecord(METRIC_SPO2, payload[4], timestamp, raw)

    return None


def decode_device_info(frame: RingFrame) -> dict[str, str]:
    """Decode the reply to the device information request (cmd 0x32)."""
    payload = frame.payload
    if len(payload) < 4:
        return {}
    info: dict[str, str] = {}
    try:
        info["device_name"] = payload[0:32].split(b"\x00")[0].decode(errors="replace")
        info["firmware_flag"] = payload[32:34].hex(" ")
        segments = [seg for seg in payload[34:].split(b"\x00") if seg]
        if segments:
            info["serial"] = segments[0].decode(errors="replace")
        if len(segments) > 1:
            info["tail"] = segments[-1].decode(errors="replace")
    except (IndexError, UnicodeDecodeError):
        return info
    return info


def ppg_function(metric: str) -> int | None:
    """Map a metric to its PPG function selector."""
    return {
        METRIC_HEART_RATE: PPG_FUNC_HR,
        METRIC_HRV: PPG_FUNC_HRV,
        METRIC_SPO2: PPG_FUNC_SPO2,
        METRIC_TEMPERATURE: PPG_FUNC_TEMPERATURE,
    }.get(metric)
