# POBOVi Ring — Home Assistant integration

[![status-badge](https://woodpecker.apps.tgkenney.dev/api/badges/tgkenney/ha-poboviring/status.svg)](https://woodpecker.apps.tgkenney.dev/repos/tgkenney/ha-poboviring)

Local Bluetooth integration for the POBOVi smart ring, with optional
SparkyFitness upload. It talks to the ring directly over BLE; the vendor app is
not used or required.

Reverse engineered from the POBOVi Ring Android app `V1.2.63` (283).

## Requirements

- Home Assistant with the `bluetooth` integration.
- At least one **connectable** Bluetooth proxy near the ring. An ESPHome proxy
  qualifies when it runs:

  ```yaml
  esp32_ble_tracker:
    scan_parameters:
      active: true
  bluetooth_proxy:
    active: true
  ```

  `active: false` proxies can hear advertisements but cannot be used for the
  GATT connection this integration needs.

## What you can do

- Track sleep sessions, including naps, with duration, score and
  deep/light/REM/awake minutes — no vendor app required.
- See steps, calories, active minutes, heart rate, HRV, SpO2, stress,
  temperature and respiration in Home Assistant.
- Upload records to your own SparkyFitness server, one profile per ring.
- Write the ring's profile and cycle settings, and buzz it to find it.
- Update the ring firmware over Bluetooth through a guarded service.

## Installation

### HACS

Add `https://gitea.tgkenney.dev/tgkenney/ha-poboviring` as a custom repository
(category **Integration**), install **POBOVi Ring**, and restart Home Assistant.

### Manual

Copy `custom_components/pobovi_ring` from this repository into your Home
Assistant `config/custom_components/` directory and restart Home Assistant.

The ring is discovered automatically (manufacturer data `0xFFFF` starting with
`POBO`). You can also add it manually with its Bluetooth address
(`Settings → Devices & Services → Add Integration → POBOVi Ring`).

## Removing the integration

1. Delete the POBOVi Ring entry under **Settings → Devices & Services**. Home
   Assistant removes the entry, its devices and entities, and the integration
   deletes its cached stores.
2. Remove the files if installed manually (`config/custom_components/pobovi_ring`)
   or uninstall the repository from HACS.
3. Delete the dashboard cards and their inline resources if you added them.

## Repository layout and development

| Path | Contents |
|---|---|
| `custom_components/pobovi_ring/` | The integration (BLE, protocol, coordinator, entities, OTA, SparkyFitness) |
| `cards/` | Rings dashboard card sources, deployed as inline Lovelace resources |
| `scripts/` | Version bump and dashboard-card deployment |
| `tests/` | Codec, session and firmware-container tests |
| `docs/` | Quality-scale review and roadmap |
| `.woodpecker/` | CI: lint/test/secret scan plus the tag release pipeline |
| `openspec/` | Specifications and change proposals |

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements_test.txt
.venv/bin/ruff check custom_components/ tests/
.venv/bin/python -m pytest tests/ -v
```

Releases are automatic. Add a `CHANGELOG.md` entry under `[Unreleased]` and push
to `main`: Woodpecker runs the checks, bumps the manifest according to the
changelog section, commits, tags `vX.Y.Z`, deploys the integration over SMB,
updates the dashboard cards over the HA WebSocket API, restarts Home Assistant,
and publishes the Gitea release. Required Woodpecker secrets: `gitea_token`,
`smb_host`, `smb_user`, `smb_password`, `ha_token`.

The cards are stored in Home Assistant as inline Lovelace resources, so the SMB
copy cannot update them. Deploy them manually after editing:

```bash
HA_URL=http://homeassistant.local:8123 HA_TOKEN=... python3 scripts/deploy_cards.py
```

Non-trivial changes go through OpenSpec: create a proposal in
`openspec/changes/`, validate it with `openspec validate`, implement, and
archive it. The current specifications live in `openspec/specs/`; the workflow
and agent commands are documented in `AGENTS.md`.

## Configuration

Setup asks for the ring's Bluetooth address and a display name. Everything else
lives in the config entry options, not in YAML.

| Option | Default | Notes |
|---|---|---|
| Poll interval | 30 min | How often Home Assistant connects to the ring |
| Seconds to listen per poll | 20 s | How long each session collects pushed records |
| Realtime reading | off | Heart rate is always sampled. This adds HRV, SpO2 and temperature |
| Push to SparkyFitness | off | Enables the upload |
| SparkyFitness base URL | — (required to enable) | Your server's base URL; `/api/health-data` is appended |
| SparkyFitness API key | — | Password field, stored in the config entry |
| Source name | `pobovi_ring` | Sent as `source` on each record |
| Write ring profile | off | Sends gender/birthday/height/weight/stride (cmd `0x31`) |
| Find-my-ring duration | 120 s | How long the ring buzzes for |

The API key is entered in the options flow (a password selector) and stored in
the config entry inside `.storage`, so it is never hardcoded and never written
to YAML. Leaving the field blank on a later edit keeps the existing key. It is
redacted in diagnostics.

Generate the key in SparkyFitness under **Settings → API key**. The server must
have `ENCRYPTION_KEY` configured before it will issue one.

## Dashboard cards

The repository ships two cards. Both require a `rings` list; the card shows a
configuration error instead of guessing entity IDs when it is missing.

```yaml
type: custom:rings-dashboard-card
rings:
  - key: ring1
    name: Ring 1
    color: '#6366f1'
    entities:
      battery: sensor.ring1_battery
      steps: sensor.ring1_steps
      calories: sensor.ring1_calories
      active: sensor.ring1_active_minutes
      hr: sensor.ring1_heart_rate
      hrv: sensor.ring1_hrv
      spo2: sensor.ring1_blood_oxygen
      resp: sensor.ring1_respiratory_rate
      stress: sensor.ring1_stress
      sleep: sensor.ring1_sleep
      sleepScore: sensor.ring1_sleep_score
      temp: sensor.ring1_temperature
      sync: sensor.ring1_last_sync
      firmware: sensor.ring1_firmware
      rssi: sensor.ring1_signal_strength
      find: button.ring1_find_ring
```

The Trends card (`custom:rings-trends-card`) uses the same `rings` array but
only reads `steps`, `sleep`, `sleepScore`, `hr`, `hrv`, `spo2`, `resp` and
`stress`. The cards are inline Lovelace resources; see
[Repository layout and development](#repository-layout-and-development) for
deployment.

## Supported models / firmware variants

Rings that look identical can ship with different firmware, so variants are
described once in `models.py` and selected by the firmware string the ring
reports. Each `RingModel` names the firmware prefixes it matches and the
capabilities that differ — currently which clock-sync commands to send, since
the clock command is also what releases buffered records.

| Model | Firmware | Clock commands | Note |
|---|---|---|---|
| `pobo-2026` | `V1.2-2026*` | `0x51` zone time | current firmware; flushes on zone time |
| `pobo-2025` | `V1.2-2025*` | `0x30` legacy **and** `0x51` | older firmware does not act on zone time alone, so its RTC is never set |
| `generic` | anything else | both | fallback used before the firmware is known |

The detected model is stored per ring, logged when it changes, and shown in
diagnostics (`model`, `model_name`, `clock_commands`). Unknown firmware is
treated as `generic`, which sends the union of known-safe commands — those are
idempotent, so this is safe on every variant seen so far.

To add a variant: add a `RingModel` entry with a firmware prefix and the
capabilities it needs, then use those capabilities in `ble.py` / `protocol.py`.
No version checks belong anywhere else.

One observed difference beyond the clock command: HRV from the 2025 firmware
reads far higher (158-212) than the 2026 firmware (24-72) for the same field.
That looks like a different HRV metric (SDNN-like rather than RMSSD), so do not
compare HRV between variants until it is confirmed.

## Ring profile (no vendor app needed)

With the profile option enabled the integration writes the ring's user profile on
every sync, which is what the app's "personal info" screen does. This covers
calorie, distance and step-length calculations.

Command `0x31`, payload 40 bytes:

```
8 x float32 LE : age, gender, height_cm, weight_kg, hr, hr_rest, vo2max, stride_cm
3 x uint8      : birth year - 1900, month, day
5 x uint8      : women's health - lately year/month/day, duration, cycle
```

Notes:

- Units are metric on the wire; the app converts inches/pounds before sending.
- `gender` is only ever 0 or 1 (the app coerces its three-way setting to
  `gender == 1 ? 1 : 0`). This integration sends 1 for `male`, otherwise 0.
- `hr`, `hr_rest` and `vo2max` are always 0 — the app never fills them either.
- The frame is 44 bytes over the air, which needs the MTU the app negotiates
  (256). ESPHome proxies negotiate a larger MTU, so this works through them.
- Cycle tracking is a separate command (`0x15`): last period start
  (year - 1900, month, day), period length and cycle length. It is opt-in via
  the options and sent on every sync when enabled, so the ring can predict the
  cycle without the app.
- Note the vendor app is inconsistent here: its dedicated `0x15` path subtracts
  1900 from the year correctly, while its profile path passes the raw year and
  overflows the byte. This integration sends `year - 1900` on both paths.
- The builder was verified to reproduce the app's own demo frame byte for byte.

## Firmware updates (OTA)

The integration can flash the vendor's current firmware over Bluetooth using the
AMOTA protocol, but it is deliberately manual and guarded.

Call `pobovi_ring.flash_firmware` with any entity of the ring:

```yaml
action: pobovi_ring.flash_firmware
data:
  entity_id: sensor.ring1_battery
  confirm: true
  dry_run: true      # default; runs every check without flashing
```

Safety gates, all enforced before anything is written:

- `confirm: true` is required, and `dry_run` defaults to **true**
- Firmware must come from `fl.pobovielectronics.com` / `app.pobovielectronics.com`
- The image's AMOTA header must declare exactly the payload length it contains
- Connection RSSI must be better than **-80 dBm**
- Battery must be at least **50 %**
- The ring's current version must be readable, and the vendor version must be
  newer unless `allow_downgrade: true`
- Polling is paused for the duration, and a second update or a concurrent sync
  is refused

Expect **10-20 minutes**. Speed is bound by the protocol, not the signal: each
512-byte packet is sent as 26 BLE writes and waits for a command response, so
~916 packets means ~24,000 writes. RSSI only affects retransmission reliability.

Progress is logged at INFO, fired as `pobovi_ring_ota` events, and shown in
diagnostics under `ota`. After the reset the integration reconnects and reads the
firmware version back: a completed flash that reports a different version is
returned as `unverified` rather than `success`.

**Risk**: a ring has no DFU button or visible recovery path. AMOTA asks the ring
to verify the image before activating it, which should leave the old firmware
active when verification fails, but an interrupted transfer can leave the ring
waiting for a retry. Keep the ring on its charger, close the vendor app, and
prefer a proxy in the same room. The vendor app remains a valid fallback.

## Find my ring

`button.<ring>_find_ring` opens a short connection, sends cmd `0xD0`
(`55 AA D0 02 01 <seconds>`) and disconnects. The ring buzzes on its own for the
configured duration (default 120 s, the app's default), so nothing needs to stay
connected. A press during an in-progress sync is skipped with a log message
rather than fighting for the single BLE connection.

## Sensors

| Entity | Unit | Confidence |
|---|---|---|
| `sensor.pobovi_ring_battery` | % | confirmed |
| `sensor.pobovi_ring_heart_rate` | bpm | confirmed |
| `sensor.pobovi_ring_hrv` | ms | confirmed |
| `sensor.pobovi_ring_blood_oxygen` | % | high |
| `sensor.pobovi_ring_steps` | steps | confirmed |
| `sensor.pobovi_ring_calories` | kcal | medium |
| `sensor.pobovi_ring_active_minutes` | min | medium |
| `sensor.pobovi_ring_temperature` | °C | layout from app, pending live check |
| `sensor.pobovi_ring_stress` | 0-100 | confirmed (see below) |
| `sensor.pobovi_ring_sleep` | min | layout from app, pending live check |
| `sensor.pobovi_ring_last_sync` | timestamp | — |
| `sensor.pobovi_ring_sparky_status` | ok/error/disabled | — |

Blood pressure and temperature are decoded defensively and are **not** uploaded
to SparkyFitness yet.

Temperature (`0x17`) is an 8-byte timestamp plus an IEEE-754 float32; it is
requested through PPG function 10 when the realtime option is on.

Stress (`0x14`) is what the vendor calls "pressure" (Chinese: stress). The
firmware's own command enum names the channel `COMMAND_GOMORE_STRESS` and
computes it with the Gomore algorithms from PPG plus the accelerometer — there
is no blood-pressure sensor in this ring, so earlier assumptions about BP were
wrong. The value is a 0-100 stress level and is uploaded to SparkyFitness as
`Stress`.

With the realtime option on, the channel is enabled via GCTL
(`55 AA 09 03 02 14 01`) and disabled at the end of the poll. The decoder
accepts both the layout the app expects (8-byte timestamp + uint8) and the one
this firmware actually emits (4-byte timestamp + uint16); the `layout`
attribute shows which was used. Values above 100 are discarded. Raw frames are kept in a rolling log (see below) if a
field needs re-checking against a real capture.

### Sleep

Sleep sessions (`0x13`) use a different layout from the other metrics, taken
from `BleRingDataStorage.receiveData` in the app:

```
[0..7]    uint64 LE start timestamp (seconds)
[8..15]   uint64 LE end timestamp   (seconds)
[16]      total
[17]      score
[18]      stage count N
then N * (1 byte stage type, uint16 LE minutes)
```

The integration derives duration from start/end, keeps the score, and records
the raw stage pairs (`type:minutes`) in the sensor attributes. The mapping from
stage byte to deep/light/REM is not known yet, so no per-stage breakdown is sent
to SparkyFitness — only bedtime, wake time, duration and score.

### Verifying a metric against a real capture

The integration keeps a rolling log of the last 1000 raw frames per ring,
persisted across restarts. After a night's sleep:

1. Let a normal poll run after you wake up (the ring records internally, so it
   does not need to be connected while you sleep — but it must be in range of a
   proxy at some point during the poll).
2. Open the integration entry, **Download diagnostics**.
3. Look for `55 aa 13 ...` entries in `frame_log` and check `snapshot.records`.

If a sleep record decodes to a sane bedtime/wake time, the layout is confirmed.

## SparkyFitness mapping

| Ring metric | SparkyFitness type |
|---|---|
| steps | `ring_steps` (custom metric, unit `steps`) |
| calories | `ActiveCaloriesBurned` |
| active minutes | `active_minutes` |
| heart rate | `heart_rate` |
| HRV | `HRV` |
| SpO2 | `oxygen_saturation` |
| stress | `Stress` |

Steps are deliberately pushed as **`ring_steps`**, not `steps`. SparkyFitness
upserts a single `steps` value per day, and Apple Health already de-duplicates
steps across the iPhone, Apple Watch and any other sources. Writing the ring's
count into `steps` would make the two overwrite each other, so the ring keeps
its own custom metric and Apple Health owns the official daily total.

Records are sent as a JSON array of
`{"type", "value", "timestamp", "source"}` to `POST /api/health-data` with
`Authorization: Bearer <key>`.

Uploads go through a persistent queue: anything the ring hands over is written
to `.storage` first and only removed once SparkyFitness accepts it. That matters
because the ring never replays a record — a failed upload would otherwise lose
the data permanently. The queue also fills while SparkyFitness is disabled or
unconfigured, so configuring it later uploads the backlog. It is drained in
batches of 200, capped at 5000 records (oldest dropped first, with a warning),
and retried on the next poll.

## Protocol reference

### Channels

| | |
|---|---|
| Service | `a6ed0201-d344-460a-8075-b9e8ec90d71b` |
| Write | `00000061-0000-1000-8000-00805f9b34fb` (write without response) |
| Notify | `00000060-0000-1000-8000-00805f9b34fb` |
| Battery | `00002a19` (standard) |
| Device info | `0000180a` (standard) |

### Frames

```
host -> ring : 55 AA <cmd> <len> <payload...>
ring -> host : 55 AA <cmd> <len> <payload...>
host ack     : 55 BB <cmd> 00
```

Every frame the ring sends must be acknowledged or the stream stalls. Metric
records start with a little-endian `uint32` Unix timestamp followed by the
values.

### Commands

| Cmd | Direction | Meaning |
|---|---|---|
| `0x09` | host | GCTL switch (calorie / pressure channel) |
| `0x10` | ring | Steps |
| `0x11` | ring | Calories |
| `0x12` | ring | Active time |
| `0x13` | ring | Sleep |
| `0x14` | ring | Stress level |
| `0x17` | ring | Temperature |
| `0x20` | host | PPG switch (`1` HR, `2` HRV, `6` SpO2, `10` temperature) |
| `0x21` | ring | Heart rate |
| `0x22` | ring | SpO2 |
| `0x23` | ring | HRV |
| `0x30` | host | Legacy clock sync (offset in hours). Ignored by current firmware |
| `0x51` | host | Zone time — sets the clock and **triggers a buffer flush** |
| `0x32` | host / ring | Device info request / reply |
| `0x34` | host | Connection priority |
| `0xEC` | ring | End of a history stream |
| `0x6E`, `0x16`, `0x24`, `0x5D`, `0xC8`, `0xE2`, `0xEB` | ring | RR, physiology, errors, reminders, test data, rotate |

Commands that alter the device (`0x35` reset, `0xC1` shipping mode, `0x36`
bind, the AMOTA/OTA service) are deliberately not implemented.

## How syncing works (read this before using the vendor app)

The ring does **not** replay its history. It hands records over once and advances
its internal cursor, so whichever client connects next gets only what has
accumulated since the last hand-over.

Measured behaviour:

- Connecting and subscribing but not requesting anything yields **nothing**.
  The ring releases its buffer after a **zone-time command (`0x51`)** — the
  clock sync the app actually sends (`0x30` is legacy and ignored by current
  firmware). Every poll sends `0x51`, which both sets the clock and flushes any
  pending records.
- Two sessions minutes apart returned **disjoint** records (HRV at `02:42:18` in
  one, `02:58:27` in the next). Nothing was repeated.
- A backlog captured earlier (steps, calories, active time) did not reappear on
  later connections.

Consequences:

- **Use one syncer per ring.** If the vendor app is also opened, the two clients
  split the stream: whatever the app collects never reaches Home Assistant or
  SparkyFitness, and vice versa. There is no way for both to receive everything.
- Because of that, gaps in SparkyFitness are expected while both are in use. For
  complete data, let Home Assistant be the only client and stop opening the app.
- Poll at least once a day so the ring's onboard buffer does not wrap.
- Home Assistant will not re-upload records it has already sent (dedupe key is
  metric + timestamp), and SparkyFitness stores daily metrics like steps as a
  per-day **upsert**, so a repeated cumulative step count cannot double count.
  Heart rate, HRV and SpO2 are stored as time-series samples, which is also
  duplicate-free as long as timestamps differ.

## Multiple rings / multiple people

One config entry per ring. Each ring has its own Bluetooth address, its own
polling options and, importantly, its own SparkyFitness API key, so two rings
can feed two different SparkyFitness profiles from a single Home Assistant.

Why that works: a SparkyFitness API key resolves to exactly one user
(`req.authenticatedUserId = user.id` in `authMiddleware`), and
`POST /api/health-data` writes to that user. The key *is* the destination
profile.

Setup for two people:

1. Add the first ring (it is auto-discovered). Give it a name such as
   `Ring 1`. The default name already carries the last four hex digits of the
   address, so two rings never collide on entity IDs.
2. Open **Configure** on that entry and paste the SparkyFitness API key for
   that person (generated while signed in as that user). Set the source name if
   you want.
3. Repeat for the second ring with its own key. Add it by address if discovery
   shows two identical-looking entries — the confirm dialog shows each ring's
   Bluetooth address so you can tell them apart.
4. Both rings now produce separate devices (for example
   `sensor.ring_1_heart_rate` and `sensor.ring_2_heart_rate`) and upload to
   separate profiles.

Notes:

- Renaming a ring later is done the normal Home Assistant way: rename the
  **device** on its device page. Entity IDs follow, and the Sparky source name
  defaults to the ring name only until you override it in the options.
- Already-uploaded samples are tracked per entry, so restarting one ring never
  re-sends the other's history.
- If you would rather use a single shared key, SparkyFitness supports
  `x-on-behalf-of-user-id` together with its family sharing permissions. The
  per-user key is simpler and is what this integration assumes.
- Two rings can poll at the same time; an ESPHome proxy accepts a few
  concurrent connections. If you run many rings through one proxy, stagger the
  poll intervals.

## Automation examples

A morning sleep summary. Replace the notify target and entity ID with your own.
Templates are only used for the message text; the trigger and condition are
native.

```yaml
automation:
  - alias: Ring sleep summary
    trigger:
      - trigger: time
        at: "08:00:00"
    condition:
      - condition: state
        entity_id: sensor.ring1_sleep
        state_not: "unavailable"
    action:
      - action: notify.mobile_app_phone
        data:
          title: Sleep last night
          message: >-
            {{ states('sensor.ring1_sleep') }} min, score
            {{ state_attr('sensor.ring1_sleep', 'score') }};
            deep {{ state_attr('sensor.ring1_sleep', 'deep_minutes') }} min.
```

## Quality scale

The integration is assessed against the Home Assistant integration quality
scale in [`docs/quality-scale.md`](docs/quality-scale.md). No tier is claimed
yet; that document lists every rule, the current status and the work packages
to reach Platinum. The official tier is awarded through Home Assistant core
review; this repository tracks the same rules for a custom integration.

## Troubleshooting

### `ESP_GATT_CONN_CONN_CANCEL while connecting: Connection cancelled`

The ESPHome proxy cancelled the connection attempt. Causes, most likely first:

1. **The ring was not advertising at that moment.** It advertises only every
   30-80 seconds, so a connect attempt has to land inside that window.
2. **The ring is still connected to the phone app.** It accepts a single
   connection.
3. **The ring is asleep** after lying still. Pick it up or move it.
4. **The proxy has no free connection slot** (`connection_slots`, default 3).

The integration retries every connectable proxy, strongest RSSI first, for up to
75 seconds before giving up, and the error names the last proxy it tried. During
a setup attempt, close the phone app and keep the ring near a connectable proxy.

If attempts keep failing, give the proxy more slots:

```yaml
bluetooth_proxy:
  active: true
  connection_slots: 5
```

Diagnostics report `connected_via` (proxy name + RSSI) for the last successful
poll. If that shows a distant proxy at -90 dBm or worse, the ring needs a
connectable proxy closer to wherever it spends the night.

### `Could not connect. No connectable proxy reported the ring`

Home Assistant expires advertisements after about 3 minutes, so a ring that is
heard only occasionally is not connectable when a poll starts. On `esp32` the
default `scan_parameters` are `interval: 320ms` / `window: 30ms` — the proxy is
listening roughly 9% of the time. Widen the window:

```yaml
esp32_ble_tracker:
  scan_parameters:
    interval: 320ms
    window: 300ms
```

Then check the real signal strength. In testing, every proxy heard the ring at
only **-92 to -101 dBm** while a Mac a few feet away saw -65 to -87 dBm, so the
ring's radio is extremely weak. If `connected_via` or the Bermuda data shows
-90 dBm or worse, duty cycle alone will not fix it: add a connectable proxy
(`bluetooth_proxy: active: true`) in the room where the ring actually sits —
desk and bedside are the two that matter for a ring.

The integration also watches for advertisements: after a failed attempt it
retries as soon as a connectable proxy hears the ring (at most every two
minutes), rather than waiting for the next scheduled poll. To force one
immediately, call `homeassistant.update_entity` on `sensor.<ring>_last_sync`.

## Known limitations

- **One connection at a time, and one syncer.** While Home Assistant is syncing,
  the vendor app cannot connect, and the ring's history is split between whichever
  clients connect (see "How syncing works" above).
- **Static random MAC.** The advertised address is a random *static* address, so
  it is stable, but a firmware update or factory reset can change it. If the
  ring disappears, re-check its address. (Bermuda also misclassifies this kind
  of address as resolvable — a separate upstream bug.)
- **Weak radio.** These rings transmit very weakly. Proxies further than a room
  away will not see it; keep a proxy with `bluetooth_proxy: active: true` close
  by.
- **Time sync** is sent each session so the ring's day boundaries match. The
  recorded samples are absolute Unix timestamps, so they are unaffected if the
  ring clock is off.
- Sleep and temperature payload layouts are only partly confirmed. Sleep was
  derived from the app's own parser and verified against a synthetic frame, but
  stage codes are unmapped; temperature remains local-only.
