# Proposal

## Why

The repository is now public and installable by other people. The current
source still carries one household's details: a default SparkyFitness URL for
the author's server, personal entity IDs and names baked into the dashboard
cards, a real ring serial and person-named test fixtures, and manifest links to
a GitHub repository that does not exist. Diagnostics also include the raw
SparkyFitness health readback. These are not credentials, but they are
instance-specific and, in the diagnostics case, health data.

## What Changes

- Replace the hardcoded SparkyFitness default URL with an empty default; the
  options flow keeps requiring a URL when pushing is enabled.
- Point `manifest.json` documentation and issue-tracker links at the Gitea
  repository and add a code owner.
- Make both dashboard cards config-driven: the personal `DEFAULT_RINGS` lists
  are removed and the card requires a `rings` configuration. The live
  dashboard is updated to pass its rings explicitly.
- Remove the SparkyFitness readback (height/weight/body-fat snapshot) from
  diagnostics; the API key stays redacted.
- Delete the integration's cached stores when a config entry is removed.
- Rename test fixtures and replace the real serial with a placeholder; the
  captured protocol frames stay because they contain no identifiers.
- Neutralise README examples (no personal names, instance URLs, entity IDs),
  add removal instructions, use cases, automation examples, a card
  configuration example, and rename Caveats to Known limitations.
- Add `docs/quality-scale.md`, a reviewed gap analysis and roadmap for the
  Home Assistant integration quality scale.

## Capabilities

### New Capabilities

### Modified Capabilities

- `pobovi-ring`: the dashboard-card requirement becomes configuration-driven;
  add requirements for instance-neutral distribution and diagnostics that
  exclude SparkyFitness health data.

## Impact

- `custom_components/pobovi_ring/`: `const.py`, `manifest.json`,
  `diagnostics.py`, README references.
- `cards/`: both card sources and their deployment configuration.
- Home Assistant dashboard `rings-overview`: card configurations are updated
  in storage (not part of the repository).
- `tests/`: fixture names and the device-info serial.
- Documentation: `README.md`, new `docs/quality-scale.md`, `CHANGELOG.md`.
- No change to the BLE protocol, data storage, SparkyFitness upload logic, or
  release pipeline behaviour.
