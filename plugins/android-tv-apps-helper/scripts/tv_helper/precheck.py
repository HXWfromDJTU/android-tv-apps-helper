from __future__ import annotations

from typing import Any, Iterable


def classify_discovered_device(device: dict[str, Any]) -> str:
    details = " ".join(str(item).lower() for item in device.get("details", ()))
    if any(token in details for token in ("tv", "bravia", "mitv", "shield")):
        return "电视候选设备"
    return "可能是电视"


def make_precheck_result(
    *,
    adb_available: bool,
    adb_version: str | None,
    devices: Iterable[dict[str, Any]],
    local_address: str | None,
    wifi_name: str | None,
) -> dict[str, Any]:
    listed = tuple(devices)
    rows = [
        {
            "status": "completed" if adb_available else "attention",
            "item": "ADB 工具",
            "result": adb_version or "未找到",
        },
        {
            "status": "completed" if local_address else "attention",
            "item": "本机网络",
            "result": local_address or "未读取到地址",
        },
        {
            "status": "completed" if listed else "attention",
            "item": "被动发现",
            "result": f"{len(listed)} 个候选设备",
        },
    ]
    if wifi_name:
        rows.insert(2, {"status": "completed", "item": "当前 Wi-Fi", "result": wifi_name})
    return {
        "status": "completed" if adb_available and listed else "attention",
        "blocker": (
            "被动检查没有发现已授权设备；这不能证明电视未开启 ADB。"
            if not listed
            else ""
        ),
        "devices": [
            {**device, "display_kind": classify_discovered_device(device)}
            for device in listed
        ],
        "rows": rows,
        "active_scan_performed": False,
    }
