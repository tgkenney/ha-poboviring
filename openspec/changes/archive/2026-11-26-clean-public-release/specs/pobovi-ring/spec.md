# Spec Delta

## ADDED Requirements

### Requirement: Distribution is instance-neutral

The source, tests and documentation examples SHALL NOT contain a specific
installation's SparkyFitness URL, Home Assistant URL, entity IDs, person names,
Bluetooth addresses or device serials. Defaults exposed by the integration
SHALL be empty or generic, and the only fixed URLs SHALL be the project
hosting, the vendor firmware endpoint and generic documentation links.

#### Scenario: A new user installs the integration

- **WHEN** a user enables SparkyFitness pushing without entering a URL
- **THEN** the options flow reports that a URL is required; nothing defaults to another person's server

#### Scenario: The dashboard cards are installed elsewhere

- **WHEN** the cards are used without a `rings` configuration
- **THEN** they show a configuration error instead of referencing another installation's entities

### Requirement: Entry removal clears cached data

Deleting a config entry SHALL remove the integration's per-entry cached stores
(pushed keys, frames, pending queue, latest values, model, device info and
sleep sessions), in addition to Home Assistant removing its devices and
entities.

#### Scenario: A ring is removed

- **WHEN** a user deletes the POBOVi Ring config entry
- **THEN** no `pobovi_ring.<entry_id>.*` store file remains for that entry

### Requirement: Diagnostics exclude SparkyFitness health data

Config-entry diagnostics SHALL redact credentials and SHALL NOT include the
SparkyFitness profile readback (height, weight, body fat or other health
records). Connection details, model information and the captured ring frames
may remain for debugging.

#### Scenario: A user downloads diagnostics

- **WHEN** diagnostics are downloaded with SparkyFitness configured
- **THEN** the API key is shown as redacted and no SparkyFitness health readback is present

## MODIFIED Requirements

### Requirement: Dashboard cards present the retained data

The Overview and Trends cards SHALL be shipped as source in `cards/` and
deployed as inline Lovelace resources. Both cards SHALL read their rings from a
required `rings` card configuration containing a key, display name, colour and
entity map; the source SHALL NOT contain personal defaults. The Overview SHALL
show battery, steps, vitals, respiration, sleep score and a stage bar; its
sleep value SHALL sum sessions whose wake time is the current local day. The
Trends card SHALL show statistics-driven panels and the retained sleep
sessions.

#### Scenario: Cards are released

- **WHEN** a release tag is built
- **THEN** the release pipeline updates the inline resources before restarting Home Assistant

#### Scenario: A ring is configured in the card

- **WHEN** the card receives a `rings` entry with its entities
- **THEN** it renders that ring's data without requiring a code change

#### Scenario: The card has no configuration

- **WHEN** a card is added without `rings`
- **THEN** it reports a configuration error that points to the README example
