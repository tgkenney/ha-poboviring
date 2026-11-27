# Proposal

## Why

The first real flash reached the ring (header accepted at −59 dBm) but the first
512-byte data packet timed out waiting for the ring's acknowledgement. The
vendor app sends each 20-byte AMOTA chunk and waits for that GATT write to
complete before sending the next; our session sent 20-byte chunks back-to-back
with only 5 ms between them and no per-chunk delivery confirmation. The header
(3 chunks) survived; a data packet (26 chunks) overran the ring.

## What Changes

- Detect whether the AMOTA write characteristic supports a GATT write with
  response. Use it, mirroring the vendor app's `WRITE_TYPE_AUTO`, so every
  20-byte chunk is acknowledged before the next.
- If the characteristic only supports write-no-response, keep that mode but
  pace it at 30 ms per chunk instead of 5 ms.
- No protocol, service or safety-gate changes. The dry run already passed; this
  fixes the data-plane delivery for the real flash.

## Capabilities

None: this is an implementation fix for the existing firmware-update behavior,
not a spec-level change. `skip_specs: true` is set on the change.

## Impact

- `custom_components/pobovi_ring/const.py`, `ota.py`
- `CHANGELOG.md`
- No behavior change for dry runs, syncs, stores or SparkyFitness.
