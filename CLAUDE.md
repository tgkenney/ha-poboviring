# POBOVi Ring — Claude Code context

## What this is

A Home Assistant custom integration (`pobovi_ring`) that talks directly to the
POBOVi smart ring over Bluetooth LE, with optional SparkyFitness upload and two
custom dashboard cards. Reverse engineered from the POBOVi Ring Android app
`V1.2.63` (283).

Repository: `gitea.tgkenney.dev/tgkenney/ha-poboviring` (Gitea, Woodpecker CI).

## OpenSpec workflow (mandatory)

This repository uses OpenSpec for non-trivial changes. Before writing code or
configuration, create or continue a change under `openspec/changes/`; get
`openspec validate <change>` to pass, implement, then archive it. The current
specs under `openspec/specs/` are the source of truth.

Commands: `/opsx:propose`, `/opsx:apply`, `/opsx:update`, `/opsx:archive`,
`/opsx:explore`, `/opsx:sync`.

Do not implement directly from a chat request when no OpenSpec change exists.
Trivial maintenance (typos, dependency bumps) may skip the workflow; record it
in `CHANGELOG.md`.

## Commands

```bash
ruff check custom_components/ tests/
bandit -r custom_components/ -s B101
pytest tests/ -v
openspec list
openspec validate <change>
openspec archive <change>

HA_URL=http://homeassistant.local:8123 HA_TOKEN=... python3 scripts/deploy_cards.py
```

## Architecture

Integration code lives in `custom_components/pobovi_ring/`:

- `ble.py` — proxy retry/connect, notify subscription, command writes,
  `async_collect`, find-my-ring, device info.
- `protocol.py` — framing, record decoders, Sparky payloads, OTA packets,
  firmware image parsing.
- `coordinator.py` — polling, stores (latest, frames, sessions, pending,
  pushed, model, device), backfill, Sparky queue, OTA orchestration.
- `models.py` — firmware variants and clock commands.
- `ota.py` — AMOTA download/validate/flash/verify.
- `sparky.py` — SparkyFitness client.
- `sensor.py` / `button.py` / `entity.py` — entities.
- `config_flow.py` — setup/options: per-entry Sparky key, ring profile, cycle.
- `diagnostics.py` — stores, Sparky state, OTA state, frame log.

Cards: `cards/rings-dashboard-card.js` (Overview) and
`cards/rings-trends-card.js` (Trends). They are inline Lovelace resources
deployed through the HA dashboard resource API (MCP) or
`scripts/deploy_cards.py`, not files under `www/`.

## Critical behavior

- Records are delivered once by the ring. Raw frames are persisted before
  decoding and `async_backfill_frames` replays them to recover dropped records;
  Sparky keys deduplicate.
- Sleep sessions are grouped by start; the latest revision wins. 50 retained,
  newest 10 exposed as the Sleep sensor's `sessions` attribute. The Overview
  tile sums sessions by wake day.
- SparkyFitness is one API key per config entry (one profile per ring); uploads
  queue (5000 cap, 200 per batch) and retry. SparkyFitness recalculates sleep
  score; the ring score is for HA/dashboard.
- Find-my-ring needs notifications enabled, a retried write, and the ring's
  `55 BB D0` acknowledgement.
- OTA is manual and guarded: dry run by default, confirmation, vendor host
  allowlist, RSSI > -80 dBm, battery >= 50%, version checks, no auto-retry.
- BLE is intermittent; sensors keep last known values instead of going
  unavailable. Freshness comes from Last sync.

## Testing

Tests are pure Python and load the codec/models without executing the
integration's HA entry point (`tests/conftest.py`). Add regression tests for
every decoder or session-selection bug.

## Delivery

- `.woodpecker/tests.yaml`: ruff, bandit, pytest, secret scan, then the
  changelog bump/tag on `main`.
- `.woodpecker/release.yaml` (tag): version check and Gitea release from
  `CHANGELOG.md`. CI has no Home Assistant access; HACS installs the
  integration from the public GitHub mirror.
- Cards: deploy separately through the HA dashboard resource API (MCP) or
  `scripts/deploy_cards.py`.
- Woodpecker secret: `gitea_token`.
- Never commit secrets. Sparky API keys live only in the HA config entry.
