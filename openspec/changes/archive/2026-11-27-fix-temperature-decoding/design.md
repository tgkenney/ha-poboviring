# Design

## Evidence

Captured frame: `55 aa 17 08 a1 53 09 6b 29 5c 09 42`

- frame header `55 aa`, cmd `17`, payload length `08`
- payload `a1 53 09 6b 29 5c 09 42` = u32 `0x6b0953a1` (2026-11-27 09:55:45
  UTC) + float32 `29 5c 09 42` (34.34 °C)
- the same 8-byte u32+float32 layout is used by respiration (`0x6e`), whose
  decoder already works

`BleRingDataStorage.receiveData` describes an 8-byte timestamp, but the wire
frames are 8 bytes total. The decoder treated the description as the wire
layout and required 12 bytes, so every 0x17 frame was dropped.

## Fix

Follow `_decode_stress`, which already accepts both a 64-bit-timestamp app
layout and the rings' 4-byte timestamp layout:

1. If the payload is at least 12 bytes, try the 8-byte timestamp + float32 at
   offset 8 when the timestamp is plausible.
2. If the payload is at least 8 bytes, parse the 4-byte timestamp with
   `_parse_timestamp` and the float32 at offset 4.
3. Record which layout was used in `extra["layout"]`.

Both values are range-checked (-20..60 °C) and timestamps must be plausible.

## Testing

`test_temperature_decodes_u32_timestamp` decodes the captured frame and asserts
the metric, 34.34 °C, the UTC timestamp, and the `ts32+f32` layout.

## Out of scope

- SparkyFitness metric-name changes; the existing temperature record flows
  through the normal realtime push path once decoded.
- Tyler's entity naming; the same decoder serves both rings.
