# Design

## Why the SMB step goes

- It was copied from the ha-music-manager template and never used for this
  integration. The v0.9.0 tag exists, but the instance is still on 0.8.7, which
  is consistent with the deploy step failing (or being skipped) rather than a
  working deployment path.
- HACS installs into `config/custom_components/pobovi_ring` and tracks those
  files. Any SMB upload from CI would modify HACS-managed files outside HACS,
  cause version drift, and can break HACS updates.

## Remaining tag pipeline

1. `validate-version`: tag equals `manifest.json`.
2. `deploy-cards`: update the two inline Lovelace resources over the HA
   WebSocket API. Uses `ha_url` (full base URL, including scheme and port) and
   `ha_token`.
3. `create-release`: Gitea release from the changelog section.

The release pipeline no longer restarts Home Assistant. The card resource
update does not require a restart, and HACS performs the restart when it
installs an update.

## Secrets

- Keep: `gitea_token`, `ha_token`.
- Add: `ha_url` (for example `http://10.10.20.10:8123` or
  `https://ha.example.com`).
- Remove once no other pipeline uses them: `smb_host`, `smb_user`,
  `smb_password`.

## Installation path

Gitea remains the development source and runs CI. The default branch is
mirrored to GitHub; HACS adds the public GitHub repository as a custom
repository (Integration) and updates from the default branch. The mirror sync
must run after a version bump for HACS to see it; releases on GitHub are
optional.

## Out of scope

- Moving CI from Woodpecker to GitHub Actions.
- Creating GitHub releases from the mirror.
- Changing the card deployment content or the integration code.
