# Changelog

All notable changes to this project will be documented in this file.

New changes should go into [Unreleased] by default, CI/CD will automatically move these to a release version.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.9.0] - 2026-11-26

### Added
- A quality-scale review and roadmap in `docs/quality-scale.md`, covering all
  54 rules of the current Home Assistant integration quality scale.

### Changed
- The repository is ready for public use: the default SparkyFitness URL is now
  empty (the options flow still requires one when pushing is enabled), the
  manifest points at this repository and names a code owner, and diagnostics no
  longer include the SparkyFitness health readback.
- Both dashboard cards require a `rings` configuration; the personal entity and
  name defaults are gone.
- README examples are instance-neutral, with removal instructions, use cases,
  an automation example, a card configuration example, and a "Known
  limitations" section.
- Deleting a config entry now removes the integration's cached stores.
- Test fixtures no longer use person names or a real ring serial.

## [0.8.7] - 2026-11-26

### Fixed
- Sleep-session history kept only the newest session. The history builder ran
  after the "newest value" gate, so any session older than the current latest
  sleep record was skipped. A 144-minute session followed by a 65-minute one
  was therefore missing from the `sessions` attribute and the dashboard even
  though the ring had sent it.

### Changed
- The Overview card "sleep today" tile now sums every sleep session whose wake
  time is the current local day, and its stage bar aggregates the same
  sessions.

## [0.8.6] - 2026-11-26

### Fixed
- Find-my-ring did nothing. The command bytes matched the vendor app, but the
  integration sent one write-no-response without notifications and hung up
  without checking for the ring's acknowledgement. It now enables
  notifications, retries the write (with-response first, no-response
  fallback), waits for the `55 BB D0` ACK, and reports an explicit error when
  the ring does not acknowledge the command.

## [0.8.5] - 2026-11-26

### Added
- Sleep-session history: the last 50 distinct sessions are retained per ring
  and the newest 10 are exposed as a `sessions` attribute on the Sleep sensor.
- A custom Rings Trends dashboard card with stat-driven panels for steps,
  sleep, sleep score, heart rate, HRV, SpO2, respiration and stress, plus a
  per-ring list of recent sleep sessions and their stage bars.
- A recent sleep sessions table in the Rings Trends view.

### Fixed
- SparkyFitness pushed-key retention trimmed by metric name instead of
  timestamp, which could re-push old records. The cap is now 5000 and trimming
  keeps the newest entries.

## [0.8.4] - 2026-11-26

### Added
- Respiration rate (`0x6E`) decoded, exposed as a sensor, and uploaded to
  SparkyFitness as the `ring_respiration` custom metric.
- A ring sleep-score sensor plus sleep attributes for bedtime, wake time,
  score, pauses, segments and deep/light/REM/awake minutes.
- Real sleep stage events are sent to SparkyFitness (deep/light/REM/awake) so
  it can compute its own score and stage totals.

### Changed
- The Overview card gained a sleep score tile, a respiration tile and a
  per-stage bar for the latest session.

## [0.8.3] - 2026-11-26

### Changed
- Sensors keep their last known values while the ring is out of range instead
  of becoming unavailable on every failed poll. The Last sync sensor reports
  freshness.
- Battery level and the last successful sync are persisted across restarts.
- A sleep session re-sent with the same start time keeps the ring's latest
  revision rather than the longest copy.

## [0.8.2] - 2026-11-26

### Added
- Frame-log backfill: on startup the integration re-decodes saved raw frames,
  recovering records (notably sleep) that an older build had dropped, and
  queues them for SparkyFitness.

## [0.8.1] - 2026-11-26

### Fixed
- Sleep frames were silently discarded. The decoder read two 64-bit timestamps
  and required 19 payload bytes, but the ring sends two 32-bit timestamps and
  an 11-byte minimum. The score, pause and stage offsets were corrected and the
  real stage timeline is now decoded.

## [0.8.0] - 2026-11-25

### Added
- Firmware update service (`pobovi_ring.flash_firmware`) using the Ambiq AMOTA
  protocol: header, 512-byte data packets, verify, reset, then version
  readback.
- Safety gates: dry run by default, explicit confirmation, vendor host
  allowlist, image size validation, RSSI and battery minimums, same/downgrade
  protection, no automatic retries, and polling suspended during the update.
- `services.yaml`, OTA diagnostics/events, and firmware-update documentation.

### Earlier
- Initial local BLE integration: sync across multiple proxies, decoding for
  sleep, activity, heart rate, HRV, SpO2, stress and temperature, persistent
  stores and a retry queue, SparkyFitness upload, ring profile and cycle
  settings, find-my-ring, and the Rings dashboard.

[Unreleased]: https://gitea.tgkenney.dev/tgkenney/ha-poboviring/compare/v0.9.0...HEAD
[0.9.0]: https://gitea.tgkenney.dev/tgkenney/ha-poboviring/compare/v0.8.7...v0.9.0
[0.8.7]: https://gitea.tgkenney.dev/tgkenney/ha-poboviring/releases/tag/v0.8.7
