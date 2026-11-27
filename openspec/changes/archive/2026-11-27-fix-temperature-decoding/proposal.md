# Proposal

## Why

`sensor.roaming_ashleys_ring_temperature` and `sensor.tyler_temperature` have
always been unavailable. The integration decodes cmd 0x17 but requires a
12-byte payload (8-byte timestamp + float32); the rings actually send an 8-byte
payload (4-byte timestamp + float32). Every temperature frame is discarded, so
the sensor never gets a value.

## What Changes

- Accept the ring's 8-byte temperature layout (u32 timestamp + float32) and
  keep the 12-byte u64+float layout as a fallback, matching the existing
  stress decoder's approach.
- Add the captured frame as a regression test.
- No spec-level change: the Temperature sensor is already part of the intended
  sensor set; this makes its decoder match the ring.

## Capabilities

None: `skip_specs: true`.

## Impact

- `custom_components/pobovi_ring/protocol.py`, `tests/test_protocol.py`,
  `CHANGELOG.md`
- The Temperature entities become available once a 0x17 reading is collected.
