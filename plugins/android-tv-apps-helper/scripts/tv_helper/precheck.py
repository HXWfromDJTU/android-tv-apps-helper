from __future__ import annotations

import socket
import subprocess
import ipaddress
from pathlib import Path
from typing import Any, Callable, Iterable

from .adb import AdbError, find_adb, parse_devices


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
    adb_path: str | None = None,
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
    scan_approval = None
    if local_address:
        try:
            address = ipaddress.ip_address(local_address)
            if address.version == 4 and address.is_private:
                scan_approval = {
                    "scope": [str(ipaddress.ip_network(f"{local_address}/24", strict=False))],
                    "ports": [5555],
                    "purpose": "仅查找 Android TV ADB 服务",
                }
        except ValueError:
            pass
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
        "local_address": local_address,
        "wifi_name": wifi_name,
        "scan_approval": scan_approval,
        "adb_path": adb_path,
    }


def probe_local_address() -> str | None:
    """Read the active route's local address without sending discovery traffic."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("1.1.1.1", 53))
            address = str(probe.getsockname()[0])
        parsed = ipaddress.ip_address(address)
        return address if parsed.version == 4 and not parsed.is_loopback else None
    except (OSError, ValueError):
        return None


def run_passive_precheck(
    *,
    adb_path: str | None = None,
    command_runner: Callable[..., Any] = subprocess.run,
    network_probe: Callable[[], str | None] = probe_local_address,
) -> dict[str, Any]:
    local_address = network_probe()
    try:
        resolved = adb_path or str(find_adb())
    except AdbError:
        resolved = None
    if not resolved or (command_runner is subprocess.run and not Path(resolved).is_file()):
        failed = make_precheck_result(
            adb_available=False,
            adb_version=None,
            devices=(),
            local_address=local_address,
            wifi_name=None,
            adb_path=None,
        )
        return {**failed, "execution_ok": False, "error": "未找到可用 ADB"}
    try:
        version_result = command_runner(
            [resolved, "version"], capture_output=True, text=True, check=False, timeout=5
        )
        devices_result = command_runner(
            [resolved, "devices", "-l"], capture_output=True, text=True, check=False, timeout=5
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        failed = make_precheck_result(
            adb_available=False, adb_version=None, devices=(),
            local_address=local_address, wifi_name=None, adb_path=None,
        )
        return {**failed, "execution_ok": False, "error": str(error)}
    version = None
    if version_result.returncode == 0 and version_result.stdout:
        version = version_result.stdout.splitlines()[0].strip()
    devices = ()
    if devices_result.returncode == 0:
        devices = tuple(device.__dict__ for device in parse_devices(devices_result.stdout))
    result = make_precheck_result(
        adb_available=version_result.returncode == 0,
        adb_version=version,
        devices=devices,
        local_address=local_address,
        wifi_name=None,
        adb_path=str(Path(resolved).expanduser().resolve()),
    )
    return {
        **result,
        "commands": [[resolved, "version"], [resolved, "devices", "-l"]],
        "execution_ok": version_result.returncode == 0 and devices_result.returncode == 0,
        "devices_output": devices_result.stdout,
        "devices_exit_code": devices_result.returncode,
        "error": devices_result.stderr or version_result.stderr,
    }
