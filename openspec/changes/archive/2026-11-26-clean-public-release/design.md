# Design

## Card configuration

Both cards already support a `rings` array internally; this change makes it
required and removes the personal fallback. Shape:

```yaml
type: custom:rings-dashboard-card
rings:
  - key: ring1
    name: Ring 1
    color: '#6366f1'
    entities:
      battery: sensor.ring1_battery
      steps: sensor.ring1_steps
      # ... see the README for the full key list
```

`setConfig` throws a descriptive error when `rings` is missing or empty. The
error appears in the card, which is visible in the dashboard editor. The live
`rings-overview` dashboard is updated to pass the current rings before the new
resource is deployed, so the household dashboard keeps working.

The Trends card currently colours its live values with per-ring CSS classes
named after the ring keys. Those rules are removed and the colour
comes from `ring.color` inline, so any number of rings can be configured.

## SparkyFitness default

`DEFAULT_SPARKY_URL` becomes `""`. The options flow already rejects enabling
pushing without a URL (`url_required`), so behaviour is unchanged for users who
configure it. Existing entries keep their stored URL. The README's default
column becomes a placeholder.

## Manifest and diagnostics

- `documentation` and `issue_tracker` point at
  `https://gitea.tgkenney.dev/tgkenney/ha-poboviring` (the project's public
  host), not the nonexistent GitHub repository.
- `codeowners` gets `@tgkenney`.
- Diagnostics drop `sparky_readback_today` (a daily profile snapshot with
  weight/body fat). The API key remains redacted; the account name stays so
  support can confirm the destination profile.

## Entry removal

`async_remove_entry` removes the seven per-entry Store files (pushed keys,
frames, pending queue, latest values, model, device info, sleep sessions) so a
deleted entry leaves no cached data behind. Home Assistant removes the devices
and entities itself.

## Test fixtures

The captured frames are anonymous (timestamps and stage tables). Rename
`TYLER_NIGHT`/`ASH_*` constants to `SLEEP_*`, change the `as_sparky` source to
`test_ring`, and replace the real serial in the device-info test with
`TESTSERIAL0001`.

## Quality-scale review

`docs/quality-scale.md` records the 2026 quality-scale audit: the 54 rules, the
current status, the main conflicts (notably `entity-unavailable` versus the
last-known-value behaviour and the custom-integration limits of the official
process), and the work packages to reach Platinum. No tier is claimed yet;
`quality_scale.yaml` and the manifest key are added only when the corresponding
rules are done or exempt.

## Out of scope

- Implementing any Platinum work package.
- Changing the release workflow, SMB deployment, or firmware flash logic.
- Adding a licence (a maintainer decision).
