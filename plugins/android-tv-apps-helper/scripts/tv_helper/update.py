from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z.-]+))?$")


def _parse(version: str) -> tuple[tuple[int, int, int], str | None]:
    match = SEMVER.fullmatch(version)
    if not match:
        raise ValueError(f"Invalid SemVer: {version}")
    return tuple(int(match.group(index)) for index in range(1, 4)), match.group(4)


def compare_stable_versions(installed: str, candidate: str) -> int | None:
    installed_core, _ = _parse(installed)
    candidate_core, candidate_prerelease = _parse(candidate)
    if candidate_prerelease is not None:
        return None
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


def default_update_state_path() -> Path:
    return Path.home() / ".local" / "share" / "android-tv-apps-helper" / "update-state.json"


class UpdateStateStore:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else default_update_state_path()

    def read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        value = json.loads(self.path.read_text(encoding="utf-8"))
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
