# pobovi-ring Specification

## Purpose

Define how the POBOVi Ring integration collects data from the ring, retains and
forwards it, writes ring settings, updates firmware, and presents the data in
Home Assistant.

## Requirements

### Requirement: Ring data is collected over Bluetooth proxies

The integration SHALL connect through a connectable Bluetooth proxy, retry
across the available proxies within a bounded budget, and never block Home
Assistant startup on a ring connection. It SHALL pause polling during a
firmware update and SHALL react to fresh advertisements when a poll fails.

#### Scenario: The nearest proxy is not the best one

- **WHEN** several proxies have seen the ring and a connection attempt fails or times out
- **THEN** the integration tries the remaining candidates before failing the poll

#### Scenario: A poll fails while the ring is asleep

- **WHEN** no proxy can connect during a scheduled poll
- **THEN** the entities keep their last known values, Last sync reports the last success, and a later advertisement can trigger a retry

### Requirement: Records are decoded and persisted exactly once

Every received frame SHALL be saved to the raw frame log before decoding.
Decoded records SHALL update the latest-value store, and records for
SparkyFitness SHALL be deduplicated by a stable key that includes the metric
and timestamp (and the wake time for a sleep session). On startup the
integration SHALL re-decode retained frames so records dropped by an earlier
decoder are recovered.

#### Scenario: A decoder bug is fixed after the ring sent the data

- **WHEN** the integration starts with a frame log containing records the previous build dropped
- **THEN** the backfill decodes those frames, stores the latest values, and queues any unseen records for SparkyFitness

#### Scenario: The same record is seen again

- **WHEN** the ring replays a record already pushed
- **THEN** its key is present in the pushed or pending store and it is not uploaded twice

### Requirement: Sleep sessions retain every distinct session and the latest revision

Sleep frames (command `0x13`) SHALL be decoded from two 32-bit timestamps,
followed by pause count, score and stage list. Sessions SHALL be grouped by
start time; a later copy for the same start SHALL replace the earlier one. The
integration SHALL retain the last 50 sessions and expose the newest 10,
newest-first, as the Sleep sensor's `sessions` attribute with start, end,
minutes, score, pauses and deep/light/REM/awake minutes. The Overview dashboard
SHALL sum sessions whose wake time falls on the current local day.

#### Scenario: A session is re-sent with more data

- **WHEN** the ring sends the same start time with a later end or revised stages
- **THEN** the stored session is replaced with the latest copy rather than duplicated

#### Scenario: A day contains a nap and a night

- **WHEN** the ring reports two sessions with different starts that wake on the same day
- **THEN** both remain in the retained history and the Overview "sleep today" value is their sum

#### Scenario: An older session arrives alongside the latest one

- **WHEN** a backfill processes an older session and a newer session in the same run
- **THEN** both are added to the session history; the newer record still wins the latest-value slot

### Requirement: SparkyFitness upload is per-ring and resilient

Each config entry SHALL upload with its own API key so each ring writes to its
own SparkyFitness profile. Records SHALL be queued when SparkyFitness is
unreachable (capacity 5000) and uploaded in batches of 200. Sleep sessions
SHALL be sent as `SleepSession` with bedtime, wake time, duration, score and
stage events. The integration SHALL treat an HTTP 200 response as authoritative
only after inspecting its `processed`, `errors` and `skipped` fields.

#### Scenario: SparkyFitness is down during a sync

- **WHEN** an upload cannot reach the server
- **THEN** the records remain queued and are retried on a later sync

#### Scenario: A sleep session is uploaded

- **WHEN** a sleep record is queued
- **THEN** the payload contains the session bounds and stage events so SparkyFitness can merge stages and calculate its own score

### Requirement: Ring configuration and find are written over BLE

The integration SHALL write the ring profile (command `0x31`) and cycle
settings (command `0x15`) only when enabled in the options. Find-my-ring
(command `0xD0`) SHALL enable notifications before writing, retry the write,
and require the ring's `55 BB D0` acknowledgement; a missing acknowledgement
SHALL be reported as an error.

#### Scenario: Find is pressed while the ring is reachable

- **WHEN** the find button is pressed and the ring acknowledges the command
- **THEN** the ring buzzes for the configured duration

#### Scenario: The ring ignores the first write

- **WHEN** no acknowledgement arrives after the first write
- **THEN** the integration retries the write before reporting failure

### Requirement: Firmware updates are safe and manual

Firmware SHALL only be downloaded from the vendor hosts. The service SHALL
default to a dry run, require explicit confirmation, validate the AMOTA header
against the payload size, require RSSI better than -80 dBm and battery at least
50%, and refuse the same or an older version unless `allow_downgrade` is set.
Flashing SHALL send the AMOTA header, 512-byte data packets, verify and reset;
the integration SHALL reconnect and read the firmware version back. It SHALL
not retry a failed flash automatically.

#### Scenario: Dry run

- **WHEN** the service is called with `dry_run: true`
- **THEN** the image is downloaded and every check is reported without writing to the ring

#### Scenario: Unsafe link or battery

- **WHEN** the connection is weaker than -80 dBm or the battery is below 50%
- **THEN** the update is refused before the first OTA command

#### Scenario: Version readback differs

- **WHEN** the flash completes but the ring reports a different version
- **THEN** the result is `unverified` with the reported version rather than success

### Requirement: Entities report data and freshness under weak links

Sensors SHALL expose the latest value per metric and keep their last known
value when a poll fails; Last sync SHALL report the last successful sync time.
Diagnostics SHALL include the retained stores, frame log, SparkyFitness state
and OTA state.

#### Scenario: The ring is out of range

- **WHEN** several polls fail in a row
- **THEN** the sensors still show the last values and Last sync shows their age

### Requirement: Dashboard cards present the retained data

The Overview and Trends cards SHALL be shipped as source in `cards/` and
deployed as inline Lovelace resources. The Overview SHALL show battery, steps,
vitals, respiration, sleep score and a stage bar. The Trends card SHALL show
statistics-driven panels plus the retained sleep sessions.

#### Scenario: Cards are released

- **WHEN** a release tag is built
- **THEN** the release pipeline updates the inline resources before restarting Home Assistant

### Requirement: Delivery follows the release workflow

Changes SHALL be recorded in `CHANGELOG.md` under `[Unreleased]`. CI SHALL lint,
test and scan for secrets; a push to `main` with a non-empty `[Unreleased]`
SHALL bump the manifest, commit, tag and push, and the tag pipeline SHALL
deploy the component and cards and create a Gitea release.

#### Scenario: A change is merged

- **WHEN** a push to `main` contains changelog entries
- **THEN** the version is bumped according to the section (Removed → major, Added/Changed → minor, otherwise patch) and a release tag is created

#### Scenario: A tag is pushed

- **WHEN** the tag matches the manifest version
- **THEN** the component and translations are uploaded, the cards are deployed, Home Assistant is restarted, and a release is created from the changelog
