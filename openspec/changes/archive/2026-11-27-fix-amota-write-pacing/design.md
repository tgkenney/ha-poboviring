# Design

## Evidence from the vendor app

`AmOtaService.sendPacket` splits the AMOTA packet into 20-byte chunks and calls
`sendOneFrame` for each. `sendOneFrame` writes the chunk through
`BluetoothLeService.writeCharacteristic`, which uses FastBle
`BleManager.write(..., writeType=-1 (AUTO), timeout=10000)`, then waits on
`waitGATTWriteComplete` (a semaphore released by the write callback) before the
next chunk. `sendFwData` then waits up to 15 s for the ring's command response
per 512-byte packet.

`WRITE_TYPE_AUTO` resolves to a write with response when the characteristic
supports it, otherwise write-no-response. Either way the app has per-chunk flow
control.

## Fix

- In `_AmotaSession.__init__`, inspect
  `client.services.get_characteristic(AMOTA_WRITE_UUID).properties`.
  `self._write_response = "write" in properties`.
- `_write` uses `response=True` while `_write_response` is true. The awaited
  bleak call returns after the ATT write response, which is the per-chunk flow
  control the ring needs.
- If a write-with-response attempt fails (`BleakError`, `ValueError`,
  `TypeError`), switch the session to write-no-response and retry that chunk;
  future chunks use the fallback delay. This covers a proxy or ring that
  advertises support but rejects it.
- `_write_delay`: 5 ms with response, 30 ms without. The command-response waits
  per packet remain at 20 s.

## Timing

The image is 468,812 bytes: 916 data packets, about 23,800 chunk writes. With
response writes through a proxy at ~20–50 ms each, expect roughly 8–20 minutes,
matching the documented 10–20 minute window. The no-response fallback at 30 ms
is about 12 minutes of writing plus response waits.

## Out of scope

- Retrying a failed AMOTA session automatically.
- Larger-than-20-byte GATT writes.
- Any change to the download, validation, safety gates or version readback.
