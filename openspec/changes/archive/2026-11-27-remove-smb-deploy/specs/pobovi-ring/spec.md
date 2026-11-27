# Spec Delta

## MODIFIED Requirements

### Requirement: Delivery follows the release workflow

Changes SHALL be recorded in `CHANGELOG.md` under `[Unreleased]`. CI SHALL lint,
test and scan for secrets; a push to `main` with a non-empty `[Unreleased]`
SHALL bump the manifest, commit, tag and push. The tag pipeline SHALL deploy the
dashboard cards and create a Gitea release. The integration SHALL be installed
and updated through HACS from the public GitHub mirror; CI SHALL NOT copy
integration files into the Home Assistant config directory.

#### Scenario: A change is merged

- **WHEN** a push to `main` contains changelog entries
- **THEN** the version is bumped according to the section (Removed → major, Added/Changed → minor, otherwise patch) and a release tag is created

#### Scenario: A tag is pushed

- **WHEN** the tag matches the manifest version
- **THEN** the dashboard cards are deployed and a Gitea release is created from the changelog; integration files are not copied and Home Assistant is not restarted by CI

#### Scenario: A new version reaches GitHub

- **WHEN** the mirrored default branch contains a newer manifest version
- **THEN** HACS offers the update and installs it; Home Assistant restarts as part of the HACS update
