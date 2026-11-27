# Spec Delta

## MODIFIED Requirements

### Requirement: Dashboard cards present the retained data

The Overview and Trends cards SHALL be shipped as source in `cards/` and
deployed as inline Lovelace resources through the Home Assistant dashboard
resource API. Both cards SHALL read their rings from a required `rings` card
configuration containing a key, display name, colour and entity map; the source
SHALL NOT contain personal defaults. The Overview SHALL show battery, steps,
vitals, respiration, sleep score and a stage bar; its sleep value SHALL sum
sessions whose wake time is the current local day. The Trends card SHALL show
statistics-driven panels and the retained sleep sessions.

#### Scenario: Cards are released

- **WHEN** a card source changes
- **THEN** it is deployed through the Home Assistant dashboard resource API (or the repository script); the release pipeline does not deploy it

#### Scenario: A ring is configured in the card

- **WHEN** the card receives a `rings` entry with its entities
- **THEN** it renders that ring's data without requiring a code change

#### Scenario: The card has no configuration

- **WHEN** a card is added without `rings`
- **THEN** it reports a configuration error that points to the README example

### Requirement: Delivery follows the release workflow

Changes SHALL be recorded in `CHANGELOG.md` under `[Unreleased]`. CI SHALL lint,
test and scan for secrets; a push to `main` with a non-empty `[Unreleased]`
SHALL bump the manifest, commit, tag and push. The tag pipeline SHALL create a
Gitea release. The integration SHALL be installed and updated through HACS from
the public GitHub mirror; CI SHALL NOT copy integration files, deploy the
dashboard cards, or restart Home Assistant.

#### Scenario: A change is merged

- **WHEN** a push to `main` contains changelog entries
- **THEN** the version is bumped according to the section (Removed → major, Added/Changed → minor, otherwise patch) and a release tag is created

#### Scenario: A tag is pushed

- **WHEN** the tag matches the manifest version
- **THEN** a Gitea release is created from the changelog; CI does not deploy files or cards and does not restart Home Assistant

#### Scenario: A new version reaches GitHub

- **WHEN** the mirrored default branch contains a newer manifest version
- **THEN** HACS offers the update and installs it; Home Assistant restarts as part of the HACS update
