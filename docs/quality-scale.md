# Integration quality scale review

Reviewed 2026-11-26 against the current Home Assistant
[quality scale](https://contributors.home-assistant.io/core/quality-scale/)
(54 rules: 20 Bronze, 10 Silver, 21 Gold, 3 Platinum). A tier requires every
rule of that tier **and every tier below it** to be `done` or `exempt`.

**Current status: no tier claimed.** Self-assessment after the public-release
cleanup: **33 done, 14 todo, 7 exempt.** A tier needs a `quality_scale.yaml`
file next to `manifest.json` and a `quality_scale` key in the manifest; both are
added once a tier is complete. The official tier is approved through Home
Assistant core review, using hassfest and a reviewer. This is a custom
integration: the rules are a quality bar, not a certified badge. To make
Platinum official, the integration would have to move into core.

## Status

### Bronze (20)

| Rule | Status | Notes |
|---|---|---|
| action-setup | done | Service registered in `async_setup`, not per entry. |
| appropriate-polling | done | Ring buffers records; 30 min default, configurable; advert-triggered retry on failure. |
| brands | todo | Local brand assets now exist for HACS (`custom_components/pobovi_ring/brand/`); the official rule still needs them submitted to the Home Assistant brands repository. |
| common-modules | done | `coordinator.py` and `entity.py` exist as expected. |
| config-flow | done | Bluetooth discovery and manual address flow; data vs options separated. Add `data_description` for the two setup fields. |
| config-flow-test-coverage | todo | No config-flow tests yet. Needs the HA test harness and success/error/duplicate/discovery paths. |
| dependency-transparency | done | `bleak-retry-connector` is open source, on PyPI. Pin the version range for a core submission. |
| docs-actions | done | `pobovi_ring.flash_firmware` documented. |
| docs-conditions | exempt | The integration has no conditions. |
| docs-high-level-description | done | README describes the ring and the local-BLE approach. |
| docs-installation-instructions | done | Prerequisites, HACS and manual installation. |
| docs-removal-instructions | done | Entry removal, files/HACS and cards. |
| docs-triggers | exempt | The integration has no triggers. |
| entity-event-setup | done | Coordinator entities; advertisement callback registered with `async_on_unload`. |
| entity-unique-id | done | `<address>_<key>` unique IDs. |
| has-entity-name | done | `_attr_has_entity_name = True` with device context. |
| runtime-data | todo | Uses `hass.data[DOMAIN][entry_id]`. Move to `entry.runtime_data` with a typed config entry. |
| test-before-configure | todo | The manual-address flow does not connect. Decide between a short connection test or an exemption for a sleeping ring. |
| test-before-setup | todo | Setup schedules the first refresh in the background. Align with the "devices that are often offline" pattern (entities unavailable until the first sync) and the `UpdateFailedUnreachable` change below. |
| unique-config-entry | done | Bluetooth address is the unique ID and duplicates abort. |

### Silver (10)

| Rule | Status | Notes |
|---|---|---|
| action-exceptions | done | The firmware service raises `ServiceValidationError`; the find button should surface a failure as `HomeAssistantError`. |
| config-entry-unloading | done | `async_unload_entry` unloads platforms and clears runtime data. |
| docs-configuration-parameters | done | Every option is in the README table. |
| docs-installation-parameters | done | Address and name are documented. |
| entity-unavailable | todo | **Main design conflict.** Sensors deliberately keep their last value during outages. The rule requires unavailable when the device cannot be reached. Conform (with `UpdateFailedUnreachable`), possibly with a one-interval grace period, or accept that Platinum stays out of reach. |
| integration-owner | done | `codeowners` set to `@tgkenney`. |
| log-when-unavailable | todo | Raise `UpdateFailedUnreachable` instead of `UpdateFailed`; the coordinator then logs once when it loses the ring and once when it returns. |
| parallel-updates | todo | Set `PARALLEL_UPDATES = 0` (coordinator-based) in the sensor and button platforms. |
| reauthentication-flow | exempt | No device authentication. The optional SparkyFitness key is changed in the options flow. |
| test-coverage | todo | Only the codec and models have tests. The rule needs >95% of every module, including coordinator, BLE, OTA, Sparky, entities, diagnostics and config flow. Largest single work item. |

### Gold (21)

| Rule | Status | Notes |
|---|---|---|
| devices | done | Device info includes identifiers, manufacturer, model, serial, software and hardware. |
| diagnostics | done | API key redacted; SparkyFitness health readback removed. Frame logs remain for debugging. |
| discovery | done | Bluetooth manufacturer matcher. |
| discovery-update-info | exempt | The BLE address is the device identity; there is no separate network address to update. |
| docs-data-update | done | "How syncing works" explains the poll and the ring's buffered data. |
| docs-examples | done | Morning sleep summary automation example. |
| docs-known-limitations | done | "Known limitations". |
| docs-supported-devices | done | Supported firmware variants; expand the exact ring model list if more are confirmed. |
| docs-supported-functions | done | Sensors, sleep, SparkyFitness, profile, find and OTA. |
| docs-troubleshooting | done | Connection, proxy and signal-strength sections. |
| docs-use-cases | done | "What you can do". |
| dynamic-devices | exempt | One fixed ring per config entry. |
| entity-category | done | Battery, firmware, signal, last sync and Sparky status are diagnostic. |
| entity-device-class | done | Battery, temperature, signal strength and timestamp where they apply. |
| entity-disabled-by-default | todo | Disable rarely needed entities by default, starting with Sparky status. Firmware/RSSI feed the dashboard cards; decide whether to keep them enabled or make the cards tolerant. |
| entity-translations | done | All entity names come from `strings.json`/translations. |
| exception-translations | todo | Service/OTA failures use raw strings. Add `exceptions` keys and raise with `translation_domain`/`translation_key`. Config-flow errors are already translated. |
| icon-translations | todo | Move icons from descriptions/button attributes into `icons.json`. |
| reconfiguration-flow | exempt | The Bluetooth address is the ring identity; every address change is a different device and needs a new entry. The name is renamed through the device registry; all other settings are options. A reviewer may prefer a name-only reconfigure step. |
| repair-issues | todo | Add repairs for user-fixable problems: repeated SparkyFitness authentication failures, and an unrecognised firmware family. |
| stale-devices | exempt | Single fixed device per config entry; it lives and goes with the entry. |

### Platinum (3)

| Rule | Status | Notes |
|---|---|---|
| async-dependency | done | `bleak`, `bleak-retry-connector` and `aiohttp` are async. |
| inject-websession | done | `SparkyClient` receives `async_get_clientsession(hass)`. |
| strict-typing | todo | Add a strict mypy configuration and CI job, type the coordinator/entities/callbacks, use a typed `ConfigEntry`, and confirm the dependency ships `py.typed`. This is the only Platinum rule left. |

## Work packages

### 1. Bronze completion (about 3-5 days)

- Add `quality_scale.yaml` with every rule and current status.
- Move runtime data to `entry.runtime_data` with a typed `PoboviConfigEntry`.
- Submit the existing brand assets to the brands repository.
- Add config-flow tests (discovery, manual, duplicate, errors) and the
  `data_description` fields.
- Decide `test-before-configure` (connection probe or exemption) and align
  `test-before-setup` with the often-offline pattern.

### 2. Silver completion (about 4-6 days)

- Switch to `UpdateFailedUnreachable` and implement `entity-unavailable` (the
  decision in "Open decisions").
- Log once when the ring disappears and once when it returns (handled by the
  coordinator change).
- Set `PARALLEL_UPDATES = 0`.
- Bring test coverage above 95% for every module; this is the bulk of the work.
- Surface find-ring failures through `HomeAssistantError`.

### 3. Gold completion (about 2-3 days)

- Add `icons.json` and exception translations.
- Add repair issues for SparkyFitness authentication failures and unsupported
  firmware.
- Disable the least useful diagnostic entity by default and make the cards
  tolerant of disabled entities.
- Expand supported-device documentation and confirm the reconfigure exemption.

### 4. Platinum completion (about 2-4 days)

- Enable strict mypy in CI, add typed config entries throughout, and fix the
  typing errors.
- Verify `bleak-retry-connector` ships `py.typed`; if not, add stubs or a typed
  wrapper.

Total estimate: roughly two to three weeks of part-time work. Test coverage and
strict typing dominate.

## Open decisions

1. **Entity availability.** The integration currently keeps the last known value
   when the ring is out of range, which was a deliberate UX choice. The quality
   scale requires entities to go unavailable when the device cannot be reached.
   Options: (a) conform, with the dashboard blanking during outages; (b) conform
   with a one-poll grace period; (c) keep last-known values and accept that the
   integration cannot claim Silver or Platinum.
2. **Official vs self-declared tier.** A custom integration cannot be officially
   rated: hassfest and core review only run in the core repository, and the
   brands and documentation rules point at core infrastructure. The practical
   target is a self-assessed tier with every rule done or exempt; the official
   badge requires a core submission.
3. **Test-before-configure.** A connection test while the user is adding the
   ring can fail for a sleeping or out-of-range device. The rule allows an
   exemption for runtime-discovered devices; a short test with a clear
   "device asleep" error is the alternative.

## References

- [Integration quality scale](https://contributors.home-assistant.io/core/quality-scale/)
- [All rules](https://contributors.home-assistant.io/core/quality-scale/rules/)
- [The quality scale file](https://contributors.home-assistant.io/core/quality-scale/quality-scale-file/)
- [Raise the tier of an integration](https://contributors.home-assistant.io/core/quality-scale/raise-tier/)
