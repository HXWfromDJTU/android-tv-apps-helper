from __future__ import annotations

from typing import Any, Iterable


ACTION_LABELS = {"wallpaper": "修改壁纸", "home_key": "修改 Home 键默认桌面"}
RISK_MESSAGES = {
    "wallpaper": {
        "verified_supported": "已有成功证据，但厂商系统仍可能在几天后、重启或升级后重置壁纸。",
        "high_risk": "当前型号或系统大概率无法长期替换壁纸，或会被厂商系统恢复。",
        "unknown": "没有当前型号的可靠兼容性证据；修改可能失败或被系统恢复。",
    },
    "home_key": {
        "verified_supported": "已有成功证据，但系统升级仍可能恢复原厂桌面。",
        "high_risk": "当前型号或系统对 Home 键限制严格，大概率无法替换成功。",
        "unknown": "没有当前型号的可靠兼容性证据；Home 键修改可能失败。",
    },
}


def match_compatibility(
    identity: dict[str, Any], records: Iterable[dict[str, Any]]
) -> dict[str, Any] | None:
    best: tuple[int, dict[str, Any]] | None = None
    fields = ("manufacturer", "model", "android_version", "sdk", "build_id", "system", "launcher")
    for record in records:
        score = 0
        for field in fields:
            expected = record.get(field)
            if expected is None:
                continue
            actual = identity.get(field)
            if actual is None or str(actual).casefold() != str(expected).casefold():
                score = -1
                break
            score += 1
        if score >= 0 and (best is None or score > best[0]):
            best = (score, record)
    return best[1] if best else None


def compatibility_rows(
    match: dict[str, Any] | None, actions: Iterable[str]
) -> list[dict[str, str]]:
    rows = []
    for action in actions:
        if action not in ACTION_LABELS:
            raise ValueError(f"Unsupported compatibility action: {action}")
        risk = str((match or {}).get("actions", {}).get(action, "unknown"))
        if risk not in {"verified_supported", "high_risk", "unknown"}:
            raise ValueError(f"Unsupported compatibility risk: {risk}")
        rows.append(
            {
                "action": action,
                "label": ACTION_LABELS[action],
                "risk": risk,
                "message": RISK_MESSAGES[action][risk],
                "evidence": str((match or {}).get("evidence", "未匹配到设备证据")),
            }
        )
    return rows


def match_or_default(
    identity: dict[str, Any], registry: dict[str, Any]
) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    match = match_compatibility(identity, registry.get("records", ()))
    effective = match
    if effective is None and isinstance(registry.get("default"), dict):
        effective = {
            "id": "default-high-risk",
            "actions": registry["default"],
            "evidence": registry.get("default_evidence", "项目默认兼容性结论"),
        }
    return match, compatibility_rows(effective, ("wallpaper", "home_key"))
