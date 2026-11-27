# Proposal

## Why

The dashboard cards are inline Lovelace resources stored in Home Assistant, not
integration files. Deploying them from the release pipeline makes CI depend on
Home Assistant credentials and couples every release to a live HA instance for
a cosmetic asset. They are already deployed directly through the Home Assistant
dashboard resource API (the MCP server's dashboard resource tool), or with the
repository script when working outside the MCP context.

## What Changes

- Remove the `deploy-cards` step from `.woodpecker/release.yaml`. The tag
  pipeline becomes `validate-version` → `create-release`.
- Remove the `ha_url` and `ha_token` secrets from CI; only `gitea_token` is
  needed.
- Keep `cards/` and `scripts/deploy_cards.py`; deploy cards through the MCP
  dashboard resource tool or the script when their source changes.
- Update README, `AGENTS.md`, `CLAUDE.md`, the changelog, and the dashboard and
  delivery spec requirements.

## Capabilities

### New Capabilities

### Modified Capabilities

- `pobovi-ring`: dashboard cards are deployed through the Home Assistant
  resource API rather than the release pipeline; the tag pipeline only creates
  the Gitea release.

## Impact

- `.woodpecker/release.yaml`: only version validation and the Gitea release.
- Woodpecker secrets: only `gitea_token` remains.
- Documentation and spec; no integration or card code changes.
