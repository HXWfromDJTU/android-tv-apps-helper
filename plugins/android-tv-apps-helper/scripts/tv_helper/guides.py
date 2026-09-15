from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Iterable


def _score(identity: dict[str, Any], match: dict[str, Any]) -> int:
    if match.get("scope") == "generic":
        return 0
    fields = ("manufacturer", "model_family", "model", "system", "android_version", "build_id")
    score = 0
    for field in fields:
        expected = match.get(field)
        if expected is None:
            continue
        actual = identity.get(field)
        if actual is None or str(actual).casefold() != str(expected).casefold():
            return -1
        score += 1
    return score if score else -1


def match_device_guide(
    identity: dict[str, Any], guides: Iterable[dict[str, Any]]
) -> dict[str, Any]:
    candidates = [( _score(identity, guide.get("match", {})), guide) for guide in guides]
    candidates = [item for item in candidates if item[0] >= 0]
    if not candidates:
        raise ValueError("Device guide registry must include a generic guide.")
    return max(candidates, key=lambda item: item[0])[1]


def validate_wallpaper(path: Path, *, max_size: int = 20 * 1024 * 1024) -> dict[str, Any]:
    target = Path(path)
    if not target.is_file():
        return {"valid": False, "reason": "图片文件不存在。"}
    size = target.stat().st_size
    if size <= 0 or size > max_size:
        return {"valid": False, "reason": "图片为空或超过 20 MB。"}
    head = target.read_bytes()[:16]
    media_type = None
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        media_type = "image/png"
    elif head.startswith(b"\xff\xd8\xff"):
        media_type = "image/jpeg"
    elif head.startswith(b"RIFF") and head[8:12] == b"WEBP":
        media_type = "image/webp"
    if media_type is None:
        return {"valid": False, "reason": "仅支持 PNG、JPEG 或 WebP 图片。"}
    return {
        "valid": True,
        "path": str(target.resolve()),
        "size": size,
        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "media_type": media_type,
    }


def next_finish_state(*, adb_used: bool) -> str:
    return "FINISH-SAFETY-Q1" if adb_used else "END-NO-ADB"
