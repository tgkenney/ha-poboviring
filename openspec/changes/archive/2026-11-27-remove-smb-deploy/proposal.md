# Proposal

## Why

The release pipeline copies the integration into the Home Assistant config
directory over SMB. That path was inherited from another project and has never
been used for this integration; the v0.9.0 release did not update the instance.
The installation is moving to HACS, which owns `custom_components/pobovi_ring`
and must not have files overwritten behind its back.

## What Changes

- Remove the `deploy-to-ha` SMB step from `.woodpecker/release.yaml`.
- Keep the card deployment, but read the HA base URL from a new `ha_url`
  secret instead of deriving it from `smb_host`.
- The tag pipeline becomes: version check → deploy dashboard cards over the
  WebSocket API → create the Gitea release.
- The integration is installed and updated through HACS from the public GitHub
  mirror; CI no longer copies integration files or restarts Home Assistant.
- Update README, `AGENTS.md`, `CLAUDE.md`, the changelog and the delivery spec.
  Required Woodpecker secrets become `gitea_token`, `ha_url`, `ha_token`.

## Capabilities

### New Capabilities

### Modified Capabilities

- `pobovi-ring`: the delivery requirement no longer includes copying the
  component into Home Assistant; the tag pipeline only deploys the cards and
  the Gitea release, and HACS owns the integration.

## Impact

- `.woodpecker/release.yaml`: `deploy-to-ha` removed; `deploy-cards` uses
  `ha_url`.
- Documentation: README, `AGENTS.md`, `CLAUDE.md`, `CHANGELOG.md`, spec.
- Woodpecker secrets: add `ha_url`; `smb_host`, `smb_user` and `smb_password`
  can be removed.
- No change to the integration code, stores, uploads or the card sources.
