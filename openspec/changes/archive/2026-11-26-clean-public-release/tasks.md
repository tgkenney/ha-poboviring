# Tasks

## 1. Remove instance-specific defaults

- [x] 1.1 Set `DEFAULT_SPARKY_URL` to an empty string; keep the options-flow URL requirement.
- [x] 1.2 Update `manifest.json`: Gitea documentation/issue-tracker URLs and a code owner.
- [x] 1.3 Remove the SparkyFitness readback from diagnostics; keep the API-key redaction.
- [x] 1.4 Neutralise test fixtures: rename sleep constants, use `test_ring` as the source, replace the real serial.
- [x] 1.5 Delete the per-entry cached stores in `async_remove_entry`.

## 2. Make the cards config-driven

- [x] 2.1 Remove `DEFAULT_RINGS` from both cards and require a non-empty `rings` configuration with a clear error.
- [x] 2.2 Replace the per-ring colour classes with inline `ring.color`.
- [x] 2.3 Update the live `rings-overview` dashboard cards to pass the current rings.
- [x] 2.4 Deploy the updated card resources and verify both resources updated.

## 3. Documentation

- [x] 3.1 Replace personal examples and the author's SparkyFitness URL in the README.
- [x] 3.2 Add removal instructions, use cases, an automation example and a card configuration example; rename Caveats to Known limitations.
- [x] 3.3 Add `docs/quality-scale.md` with the rule-by-rule audit and the roadmap to Platinum.

## 4. Verification

- [x] 4.1 `ruff check custom_components/ tests/`
- [x] 4.2 `bandit -r custom_components/ -s B101`
- [x] 4.3 `pytest tests/ -v`
- [x] 4.4 `openspec validate clean-public-release`
- [x] 4.5 Confirm no instance-specific URL, name, entity ID, serial or credential remains in source.

## 5. Release bookkeeping

- [x] 5.1 Add the cleanup and quality-scale review to `CHANGELOG.md` under `[Unreleased]`.
- [x] 5.2 Archive the OpenSpec change after verification.
