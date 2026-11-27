# Design

## Card deployment

The cards are inline resources in HA storage (`.storage/lovelace_resources`).
They are not part of the integration directory that HACS manages, and CI has no
business mutating HA for them. Two supported ways to update them:

- **MCP**: `ha_config_set_dashboard_resource` with the card content and the
  known resource IDs (`119369f9…` for the Overview card, `6d2733db…` for
  Trends), or create the resource when absent.
- **Script**: `HA_URL=... HA_TOKEN=... python3 scripts/deploy_cards.py`, which
  finds resources by their `CARD_TAG` and updates or creates them.

The release pipeline no longer deploys them. Its only steps are the tag/manifest
check and the Gitea release.

## Release pipeline

- `validate-version`: tag equals `manifest.json`.
- `create-release`: Gitea release from the matching changelog section.

No Home Assistant URL or token in CI. The only Woodpecker secret is
`gitea_token`. The tests pipeline is unchanged.

## Installation

HACS installs and updates the integration from the public GitHub mirror of the
Gitea repository. The mirror must sync the default branch after a version bump.
Home Assistant restarts as part of the HACS update.

## Out of scope

- Moving CI to GitHub Actions.
- Building a card bundle or hosting the cards outside HA.
- Integration code changes.
