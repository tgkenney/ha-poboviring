"""Codec and firmware-container tests using frames captured from the ring."""

from __future__ import annotations

from datetime import UTC, datetime
from itertools import pairwise

from custom_components.pobovi_ring import protocol

SLEEP_144 = "55 aa 13 0e d0 bc 07 6b 90 de 07 6b 00 52 01 02 90 00"
SLEEP_24 = "55 aa 13 14 40 1f 08 6b e0 24 08 6b 2c 2e 03 02 12 00 01 03 00 02 03 00"
SLEEP_65 = (
    "55 aa 13 20 40 1f 08 6b 7c 2e 08 6b 2c 2e 07 02 1d 00 00 05 00 02 0a 00 "
    "01 0b 00 02 03 00 01 02 00 02 04 00"
)
SLEEP_NIGHT = (
    "55 aa 13 86 90 a2 07 6b d0 25 08 6b 00 57 29 02 0c 00 03 0f 00 02 25 00 "
    "03 12 00 02 05 00 00 04 00 02 0b 00 01 07 00 02 03 00 01 07 00 02 0f 00 "
    "01 06 00 02 12 00 01 0e 00 02 0e 00 03 0f 00 02 05 00 03 0b 00 02 05 00 "
    "03 05 00 02 03 00 01 01 00 02 07 00 03 09 00 02 04 00 01 19 00 02 16 00 "
    "03 06 00 02 16 00 01 06 00 02 28 00 01 15 00 02 14 00 01 22 00 02 0f 00 "
    "03 0c 00 02 03 00 03 15 00 02 13 00 01 08 00 02 1d 00"
)
RESP_138 = "55 aa 6e 08 55 a4 07 6b 4d cd 5c 41"
RESP_124 = "55 aa 6e 08 26 a7 07 6b 66 30 46 41"
TEMPERATURE = "55 aa 17 08 a1 53 09 6b 29 5c 09 42"


def decode(hex_string: str):
    frame = protocol.parse_frame(bytes.fromhex(hex_string))
    assert frame is not None
    return protocol.decode_record(frame)


def test_find_ring_packet_layout() -> None:
    assert protocol.build_find_ring(120) == bytes.fromhex("55 aa d0 02 01 78")
    assert protocol.build_find_ring(0) == bytes.fromhex("55 aa d0 02 01 01")


def test_parse_frame_rejects_garbage() -> None:
    assert protocol.parse_frame(b"") is None
    assert protocol.parse_frame(b"\x00\x01\x02\x03") is None


def test_sleep_sessions_decode() -> None:
    expected = {
        SLEEP_144: (144, 82, 0, 1),
        SLEEP_24: (24, 46, 44, 3),
        SLEEP_65: (65, 46, 44, 7),
        SLEEP_NIGHT: (560, 87, 0, 41),
    }
    for frame, (minutes, score, pauses, segments) in expected.items():
        record = decode(frame)
        assert record is not None
        assert record.metric == "sleep"
        assert record.value == minutes
        assert record.extra["score"] == score
        assert record.extra["pauses"] == pauses
        assert record.extra["segments"] == segments
        assert len(record.extra["stages"].split(",")) == segments


def test_sleep_record_converts_to_sparky_session_with_stages() -> None:
    record = decode(SLEEP_NIGHT)
    assert record is not None
    payload = record.as_sparky("test_ring")
    assert payload is not None
    assert payload["type"] == "SleepSession"
    assert payload["duration_in_seconds"] == 560 * 60
    assert payload["sleep_score"] == 87
    events = payload["stage_events"]
    assert len(events) == 41
    assert events[0]["start_time"] == payload["bedtime"]
    assert events[-1]["end_time"] <= payload["wake_time"]
    assert {event["stage_type"] for event in events} <= {"deep", "light", "rem", "awake"}
    for earlier, later in pairwise(events):
        assert earlier["end_time"] == later["start_time"]


def test_temperature_decodes_u32_timestamp() -> None:
    record = decode(TEMPERATURE)
    assert record is not None
    assert record.metric == "temperature"
    assert abs(record.value - 34.34) < 0.01
    assert record.timestamp == datetime(2026, 11, 27, 9, 55, 45, tzinfo=UTC)
    assert record.extra.get("layout") == "ts32+f32"


def test_respiration_decodes() -> None:
    first = decode(RESP_138)
    second = decode(RESP_124)
    assert first is not None and first.metric == "respiratory_rate"
    assert first.value == 13.8
    assert second is not None and second.value == 12.4
    payload = first.as_sparky("test_ring")
    assert payload is not None
    assert payload["type"] == "ring_respiration"
    assert payload["unit"] == "breaths/min"


def test_device_info_reply() -> None:
    payload = (
        b"POBO Ring 001".ljust(32, b"\x00")
        + b"\x0b\x05"
        + b"TESTSERIAL0001\x00reserve"
    )
    info = protocol.decode_device_info(protocol.RingFrame(0x32, payload))
    assert info["device_name"] == "POBO Ring 001"
    assert info["firmware_flag"] == "0b 05"
    assert info["serial"] == "TESTSERIAL0001"
    assert info["tail"] == "reserve"


def test_ota_packet_layout_and_crc() -> None:
    packet = protocol.build_ota_packet(2, b"\xaa\xbb\xcc")
    assert packet == bytes.fromhex("07 00 02 aa bb cc 4c f8 4d be")
    assert protocol.build_ota_packet(3, b"") == bytes.fromhex("04 00 03 00 00 00 00")


def test_firmware_image_validation() -> None:
    header = bytearray(48)
    payload = b"\x55" * 700
    header[8:12] = len(payload).to_bytes(4, "little")
    image = protocol.parse_firmware_image(bytes(header) + payload)
    assert len(image.header) == 48
    assert image.declared_size == 700
    assert image.payload == payload

    try:
        protocol.parse_firmware_image(bytes(header) + payload[:-1])
    except ValueError as error:
        assert "declares" in str(error)
    else:
        raise AssertionError("truncated firmware was accepted")


def test_firmware_version_parsing() -> None:
    assert protocol.parse_firmware_version("V1.2-2026061312") == 2026061312
    assert protocol.parse_firmware_version("V1.2-2025092301") == 2025092301
    assert protocol.parse_firmware_version("junk") is None
    assert protocol.parse_firmware_version(None) is None


def test_record_timestamp_is_utc() -> None:
    record = decode(SLEEP_144)
    assert record is not None
    assert record.timestamp == datetime(2026, 11, 26, 5, 0, tzinfo=UTC)
