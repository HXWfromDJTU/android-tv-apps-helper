from __future__ import annotations

import shutil
import subprocess
from typing import Any, Callable, Iterable

from .adb import parse_devices


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
    for index, device in enumerate(listed, 1):
        kind = classify_discovered_device(device)
        details = device.get("details") or ()
        model = next(
            (
                str(item).split(":", 1)[1]
                for item in details
                if str(item).startswith("model:")
            ),
            "型号待确认",
        )
        rows.append(
            {
                "status": "attention",
                "item": f"候选设备 {index}",
                "result": f"{kind} / {model}",
                "evidence": str(device.get("state", "状态未知")),
            }
        )
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


def run_passive_precheck(
    *,
    adb_path: str | None = None,
    command_runner: Callable[..., Any] = subprocess.run,
) -> dict[str, Any]:
    resolved = adb_path or shutil.which("adb")
    if not resolved:
        return make_precheck_result(
            adb_available=False,
            adb_version=None,
            devices=(),
            local_address=None,
            wifi_name=None,
        )
    version_result = command_runner(
        [resolved, "version"], capture_output=True, text=True, check=False, timeout=5
    )
    devices_result = command_runner(
        [resolved, "devices", "-l"], capture_output=True, text=True, check=False, timeout=5
    )
    version = None
    if version_result.returncode == 0 and version_result.stdout:
        version = version_result.stdout.splitlines()[0].strip()
    devices = ()
    if devices_result.returncode == 0:
        devices = tuple(device.__dict__ for device in parse_devices(devices_result.stdout))
    return make_precheck_result(
        adb_available=version_result.returncode == 0,
        adb_version=version,
        devices=devices,
        local_address=None,
        wifi_name=None,
    )
