from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
MANIFEST = (
    ROOT / "custom_components" / "bjp_local_hoymiles" / "manifest.json"
)
CHANGELOG = ROOT / "CHANGELOG.md"
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def test_manifest_version_is_semver() -> None:
    version = json.loads(MANIFEST.read_text())["version"]
    assert SEMVER.fullmatch(version)


def test_current_version_has_changelog_entry() -> None:
    version = json.loads(MANIFEST.read_text())["version"]
    changelog = CHANGELOG.read_text()
    assert f"## [{version}] -" in changelog
