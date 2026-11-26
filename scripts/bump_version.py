#!/usr/bin/env python3
"""
Automated semver bump for ha-poboviring.

Reads the [Unreleased] section of CHANGELOG.md and determines the bump type:
  - ### Removed            → major
  - ### Added/Changed/Deprecated → minor
  - ### Fixed/Security only      → patch

Then:
  1. Updates custom_components/pobovi_ring/manifest.json version
  2. Moves ## [Unreleased] → ## [X.Y.Z] - YYYY-MM-DD in CHANGELOG.md
  3. Updates the comparison link footer in CHANGELOG.md
  4. Commits + tags + pushes (authenticated via GITEA_TOKEN env var)

Exit codes:
  0 — success (bumped and pushed, or skipped because [Unreleased] was empty)
  1 — fatal error
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
CHANGELOG = ROOT / "CHANGELOG.md"
MANIFEST = ROOT / "custom_components" / "pobovi_ring" / "manifest.json"


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, **kwargs)


def bump_version(current: str, bump_type: str) -> str:
    major, minor, patch = (int(x) for x in current.split("."))
    if bump_type == "major":
        return f"{major + 1}.0.0"
    if bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def detect_bump_type(unreleased_body: str) -> str:
    if re.search(r"^### Removed", unreleased_body, re.MULTILINE):
        return "major"
    if re.search(r"^### (Added|Changed|Deprecated)", unreleased_body, re.MULTILINE):
        return "minor"
    return "patch"


def main() -> None:
    # --- Parse [Unreleased] section ---
    changelog_text = CHANGELOG.read_text()
    m = re.search(r"## \[Unreleased\](.*?)(?=\n## \[|\Z)", changelog_text, re.DOTALL)
    if not m:
        print("ERROR: Could not find ## [Unreleased] section in CHANGELOG.md")
        sys.exit(1)

    unreleased_body = m.group(1).strip()
    if not unreleased_body:
        print("INFO: [Unreleased] section is empty — nothing to release, skipping.")
        sys.exit(0)

    bump_type = detect_bump_type(unreleased_body)

    # --- Determine new version ---
    manifest = json.loads(MANIFEST.read_text())
    current_version = manifest["version"]
    new_version = bump_version(current_version, bump_type)

    print(f"Bump type  : {bump_type}")
    print(f"Version    : {current_version} → {new_version}")

    # --- Guard: skip if tag already exists ---
    existing = subprocess.run(
        ["git", "tag", "-l", f"v{new_version}"], capture_output=True, text=True
    ).stdout.strip()
    if existing:
        print(f"INFO: Tag v{new_version} already exists — skipping.")
        sys.exit(0)

    # --- Update manifest.json ---
    manifest["version"] = new_version
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Updated    : manifest.json → {new_version}")

    # --- Update CHANGELOG.md ---
    today = date.today().isoformat()

    # Insert versioned heading below [Unreleased]
    new_changelog = changelog_text.replace(
        "## [Unreleased]",
        f"## [Unreleased]\n\n## [{new_version}] - {today}",
        1,
    )

    # Update the [Unreleased] comparison link and insert a new versioned link.
    # Before: [Unreleased]: https://host/owner/repo/compare/vOLD...HEAD
    # After:  [Unreleased]: https://host/owner/repo/compare/vNEW...HEAD
    #         [vNEW]:       https://host/owner/repo/compare/vOLD...vNEW
    link_match = re.search(
        r"\[Unreleased\]: (https://[^\s]+)/compare/(v[^\s]+)\.\.\.HEAD",
        new_changelog,
    )
    if link_match:
        base_url = link_match.group(1)
        old_tag = link_match.group(2)  # e.g. "v0.8.7"
        old_line = f"[Unreleased]: {base_url}/compare/{old_tag}...HEAD"
        new_lines = (
            f"[Unreleased]: {base_url}/compare/v{new_version}...HEAD\n"
            f"[{new_version}]: {base_url}/compare/{old_tag}...v{new_version}"
        )
        new_changelog = new_changelog.replace(old_line, new_lines, 1)
    else:
        print("WARNING: Could not find [Unreleased] link in CHANGELOG.md — links not updated.")

    CHANGELOG.write_text(new_changelog)
    print(f"Updated    : CHANGELOG.md — moved [Unreleased] → [{new_version}]")

    # --- Git config (required in CI environment) ---
    _run(["git", "config", "user.email", "ci@woodpecker.local"])
    _run(["git", "config", "user.name", "Woodpecker CI"])

    # --- Commit + tag ---
    _run(["git", "add", str(MANIFEST), str(CHANGELOG)])
    _run(["git", "commit", "-m", f"chore: release v{new_version} [skip ci]"])
    _run(["git", "tag", f"v{new_version}"])
    print(f"Created    : commit + tag v{new_version}")

    # --- Authenticated push ---
    token = os.environ["GITEA_TOKEN"]
    ci_repo = os.environ.get("CI_REPO", "tgkenney/ha-poboviring")
    remote = f"https://woodpecker:{token}@gitea.tgkenney.dev/{ci_repo}.git"

    _run(["git", "push", remote, "HEAD:main"])
    _run(["git", "push", remote, f"v{new_version}"])
    print(f"Pushed     : commit + tag v{new_version} to Gitea")


if __name__ == "__main__":
    main()
