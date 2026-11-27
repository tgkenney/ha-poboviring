# POBOVi Ring — agent context

## What this is

A Home Assistant custom integration (`pobovi_ring`) that talks directly to the
POBOVi smart ring over Bluetooth LE, with optional SparkyFitness upload and a
pair of custom dashboard cards. It was reverse engineered from the POBOVi Ring
Android app `V1.2.63` (283); the vendor app is not required.

Repository: `gitea.tgkenney.dev/tgkenney/ha-poboviring` (Gitea, Woodpecker CI).

## OpenSpec workflow (mandatory)

This repository uses OpenSpec. A non-trivial change must have an OpenSpec change
under `openspec/changes/` before implementation. The current truth lives in
`openspec/specs/`.

1. `openspec list` — see active changes.
2. `openspec new change <kebab-name>` — scaffold `proposal.md`, `design.md`,
   `tasks.md`, and spec deltas.
3. Fill the artifacts, then `openspec validate <change>` until it passes.
4. Implement against the tasks; keep the change updated when the design moves.
5. `openspec archive <change>` after verification; this updates the main spec.

Agent entry points:

- OpenCode: `/opsx-propose`, `/opsx-apply`, `/opsx-update`, `/opsx-archive`,
  `/opsx-explore`, `/opsx-sync`.
- Claude Code: `/opsx:propose`, `/opsx:apply`, `/opsx:update`,
  `/opsx:archive`, `/opsx:explore`, `/opsx:sync`.
- Codex: `$openspec-propose`, `$openspec-apply`, `$openspec-archive`.

Do not implement directly from a chat request when no OpenSpec change exists.
Typos, dependency bumps, and other trivial maintenance may skip the workflow;
record them in `CHANGELOG.md`.

## Commands

```bash
# Lint and test (same commands CI runs)
ruff check custom_components/ tests/
bandit -r custom_components/ -s B101
pytest tests/ -v

# OpenSpec
openspec list
openspec validate <change>
openspec archive <change>

# Deploy the dashboard cards manually (HA must be up)
HA_URL=http://homeassistant.local:8123 HA_TOKEN=... python3 scripts/deploy_cards.py
```

`scripts/bump_version.py` is CI-only: it reads `CHANGELOG.md` `[Unreleased]`,
bumps `manifest.json`, commits, tags, and pushes to trigger the release.

## Architecture

All integration code is in `custom_components/pobovi_ring/`.

| File | Purpose |
|---|---|
| `ble.py` | BLE session: proxy retry, connect, notify subscription, command writes, `async_collect`, find-my-ring, device-info reads. |
| `protocol.py` | Wire codec: framing, record decoders (steps, calories, active, sleep, stress, temperature, HR, HRV, SpO2, respiration), Sparky payloads, OTA packets, firmware image parsing. |
| `coordinator.py` | Polling/state: stores (latest, frames, sessions, pending, pushed, model, device), backfill, Sparky queue, OTA orchestration, find button. |
| `models.py` | Firmware variants (`pobo-2026`, `pobo-2025`, `generic`) and clock commands. |
| `ota.py` | AMOTA download/validate/flash/verify. |
| `sparky.py` | SparkyFitness HTTP client and response parsing. |
| `sensor.py`, `button.py`, `entity.py` | Entities. Sleep sensor exposes stage/session attributes; find button. |
| `config_flow.py` | UI setup and options (per-entry Sparky key, profile, cycle, polling). |
| `diagnostics.py` | Version, entry, model, stores, Sparky state, OTA state, frame log, snapshot. |

Dashboard card sources live in `cards/` and are deployed as inline Lovelace
resources (not files under `www/`). Deploy them through the HA dashboard
resource API (MCP) or `scripts/deploy_cards.py`; the release pipeline does not:

- `cards/rings-dashboard-card.js` — Overview (battery, steps, tiles, HR spark,
  sleep score, stage bar, find button).
- `cards/rings-trends-card.js` — Trends (stats-driven panels and recent sleep
  sessions).

## Critical behavior

- The ring hands records over once. Raw frames are saved **before** decoding so
  `async_backfill_frames` can recover records dropped by a bad decoder; the
  SparkyFitness keys deduplicate replays.
- Sleep sessions are grouped by start timestamp; a re-sent session keeps the
  ring's **latest** revision. The last 50 sessions are retained and the newest
  10 exposed as the Sleep sensor's `sessions` attribute, newest first. The
  Overview tile sums sessions by **wake day**.
- SparkyFitness uses one API key per config entry, so each ring writes to its
  own profile. Uploads are queued (5000 cap, 200 per batch) and retried on
  failure. `sleep_score` is recomputed by SparkyFitness; the ring score is sent
  only for the dashboard.
- Ring commands: profile `0x31`, cycle `0x15`, find `0xD0`. Find needs an active
  notify subscription and the ring's `55 BB D0` acknowledgement; retry the
  write rather than assuming one write is enough.
- OTA is deliberately manual: dry run by default, explicit confirmation, vendor
  host allowlist, RSSI > -80 dBm, battery >= 50%, readable version, no
  same/downgrade unless allowed, no automatic retry, polling paused.
- BLE is weak and intermittent. Sensors keep their last known values; freshness
  is reported by the Last sync sensor. Do not reintroduce blanking on failed
  polls.

## Delivery

- CI: `.woodpecker/tests.yaml` runs ruff, bandit, pytest, secret scanning, then
  `scripts/bump_version.py` on pushes to `main` (empty `[Unreleased]` skips).
- Release: pushing a `vX.Y.Z` tag runs `.woodpecker/release.yaml`:
  version check → Gitea release from `CHANGELOG.md`. CI has no Home Assistant
  access. The integration is installed and updated through HACS from the public
  GitHub mirror.
- Woodpecker secret required: `gitea_token`.
- Never commit tokens, API keys, or `.storage` content. Sparky keys live only in
  the HA config entry.
