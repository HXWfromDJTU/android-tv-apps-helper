from __future__ import annotations

import json
import os
import re
import hashlib
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z.-]+))?$")
RELEASES_API = "https://api.github.com/repos/HXWfromDJTU/android-tv-apps-helper/releases"


def _parse(version: str) -> tuple[tuple[int, int, int], str | None]:
    match = SEMVER.fullmatch(version)
    if not match:
        raise ValueError(f"Invalid SemVer: {version}")
    return tuple(int(match.group(index)) for index in range(1, 4)), match.group(4)


def compare_stable_versions(installed: str, candidate: str) -> int | None:
    installed_core, installed_prerelease = _parse(installed)
    candidate_core, candidate_prerelease = _parse(candidate)
    if candidate_prerelease is not None:
        return None
    if candidate_core == installed_core and installed_prerelease is not None:
        return 1
    return (candidate_core > installed_core) - (candidate_core < installed_core)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("Update timestamps must include a timezone.")
    return value.astimezone(UTC)


def should_prompt_update(
    installed: str,
    candidate: str,
    state: dict[str, Any],
    *,
    now: datetime | None = None,
) -> bool:
    current = _as_utc(now or datetime.now(UTC))
    snooze = state.get("snooze_until")
    if snooze and current < datetime.fromisoformat(str(snooze)).astimezone(UTC):
        return False
    return compare_stable_versions(installed, candidate) == 1


def record_update_decline(
    state: dict[str, Any],
    declined_version: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    current = _as_utc(now or datetime.now(UTC))
    updated = dict(state)
    updated.update(
        {
            "declined_version": declined_version,
            "declined_at": current.isoformat(),
            "snooze_until": (current + timedelta(hours=24)).isoformat(),
        }
    )
    return updated


def select_latest_stable_release(releases: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = []
    for release in releases:
        if release.get("draft") or release.get("prerelease"):
            continue
        tag = str(release.get("tag_name", ""))
        version = tag[1:] if tag.startswith("v") else tag
        core, prerelease = _parse(version)
        if prerelease is None:
            candidates.append((core, version, release))
    if not candidates:
        raise ValueError("No stable GitHub release is available.")
    _, version, release = max(candidates, key=lambda item: item[0])
    return {"version": version, "release": release}


def fetch_latest_stable_release(*, timeout: float = 5.0) -> dict[str, Any]:
    request = Request(
        RELEASES_API,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "android-tv-apps-helper"},
    )
    with urlopen(request, timeout=timeout) as response:
        value = json.loads(response.read().decode("utf-8"))
    if not isinstance(value, list):
        raise ValueError("GitHub release response must be a list.")
    selected = select_latest_stable_release(value)
    release = dict(selected["release"])
    checksum_asset = next(
        (asset for asset in release.get("assets", ()) if asset.get("name") == "SHA256SUMS"),
        None,
    )
    if checksum_asset and checksum_asset.get("browser_download_url"):
        checksum_request = Request(
            str(checksum_asset["browser_download_url"]),
            headers={"Accept": "application/octet-stream", "User-Agent": "android-tv-apps-helper"},
        )
        with urlopen(checksum_request, timeout=timeout) as response:
            checksums: dict[str, str] = {}
            for line in response.read().decode("utf-8").splitlines():
                parts = line.split()
                if len(parts) == 2 and re.fullmatch(r"[0-9a-f]{64}", parts[0]):
                    checksums[parts[1].lstrip("*")] = parts[0]
            release["sha256sums"] = checksums
    return {**selected, "release": release}


def validate_update_package(
    path: Path,
    *,
    expected_sha256: str,
    expected_version: str,
    expected_platform: str,
) -> dict[str, Any]:
    if expected_platform == "claude-desktop":
        expected_platform = "claude"
    target = Path(path)
    actual_sha = hashlib.sha256(target.read_bytes()).hexdigest()
    if actual_sha != expected_sha256:
        raise ValueError("Update package SHA-256 does not match SHA256SUMS.")
    with zipfile.ZipFile(target) as archive:
        try:
            skill = archive.read("android-tv-apps-helper/SKILL.md").decode("utf-8")
        except KeyError as error:
            raise ValueError("Update package is missing the expected Skill root.") from error
    frontmatter = skill.split("---", 2)
    if len(frontmatter) != 3:
        raise ValueError("Update package Skill metadata is invalid.")
    metadata = frontmatter[1]
    required = {
        "name": "android-tv-apps-helper",
        "version": expected_version,
        "platform": expected_platform,
    }
    for key, value in required.items():
        if not re.search(rf"(?m)^{re.escape(key)}:\s*{re.escape(value)}\s*$", metadata):
            raise ValueError(f"Update package {key} does not match {value}.")
    return {
        "skill_id": "android-tv-apps-helper",
        "version": expected_version,
        "platform": expected_platform,
        "sha256": actual_sha,
    }


def default_update_state_path(platform: str = "shared") -> Path:
    safe_platform = re.sub(r"[^a-z0-9-]", "-", platform.lower())
    return Path.home() / ".local" / "share" / "android-tv-apps-helper" / f"update-state-{safe_platform}.json"


class UpdateStateStore:
    def __init__(self, path: Path | None = None, *, platform: str = "shared"):
        self.path = Path(path) if path else default_update_state_path(platform)

    def read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as error:
            return {"state_error": str(error)}
        if not isinstance(value, dict):
            raise ValueError("Update state must be a JSON object.")
        return value

    def write(self, value: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, self.path)
