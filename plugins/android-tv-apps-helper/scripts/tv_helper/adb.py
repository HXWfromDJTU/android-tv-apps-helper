from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


class AdbError(RuntimeError):
    """Raised when an ADB precondition or command fails."""


@dataclass(frozen=True)
class Device:
    serial: str
    state: str
    details: tuple[str, ...] = ()


def parse_devices(output: str) -> list[Device]:
    devices: list[Device] = []
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("List of devices attached") or stripped.startswith("*"):
            continue
        parts = stripped.split()
        if len(parts) >= 2:
            devices.append(Device(parts[0], parts[1], tuple(parts[2:])))
    return devices


def find_adb(explicit: Path | None = None) -> Path:
    if explicit is not None:
        candidate = Path(explicit).expanduser()
        if candidate.is_file():
            return candidate.resolve()
        raise AdbError(f"ADB executable not found: {candidate}")
    discovered = shutil.which("adb")
    if discovered:
        return Path(discovered).resolve()
    candidates = (
        Path.home() / ".codex/tools/android-platform-tools/platform-tools/adb",
        Path.home() / "Downloads/platform-tools/adb",
        Path.home() / "Library/Android/sdk/platform-tools/adb",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise AdbError("ADB executable not found. Install official Android SDK Platform-Tools first.")


class AdbRunner:
    def __init__(self, executable: Path, *, timeout: int = 30):
        self.executable = Path(executable)
        self.timeout = timeout

    def run(self, arguments: Sequence[str], *, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
        command = [str(self.executable), *[str(value) for value in arguments]]
        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout or self.timeout,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as error:
            raise AdbError(f"ADB command could not run: {error}") from error
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"
            raise AdbError(detail)
        return result

    def version(self) -> str:
        return self.run(["version"]).stdout.strip()

    def list_devices(self) -> list[Device]:
        return parse_devices(self.run(["devices", "-l"]).stdout)

    def connect(self, endpoint: str) -> str:
        return self.run(["connect", endpoint]).stdout.strip()

    def shell(self, serial: str, arguments: Sequence[str]) -> str:
        if not serial.strip():
            raise AdbError("A verified target serial is required.")
        return self.run(["-s", serial, "shell", *arguments]).stdout.strip()

    def inspect_device(self, serial: str, *, state: str) -> dict[str, str]:
        self._require_authorized(state)
        properties = {
            "manufacturer": "ro.product.manufacturer",
            "brand": "ro.product.brand",
            "model": "ro.product.model",
            "android_version": "ro.build.version.release",
            "sdk": "ro.build.version.sdk",
            "abi": "ro.product.cpu.abi",
        }
        return {
            key: self.shell(serial, ["getprop", prop])
            for key, prop in properties.items()
        }

    def install(self, serial: str, apk_path: Path, *, state: str) -> str:
        self._require_authorized(state)
        apk = Path(apk_path)
        if not apk.is_file():
            raise AdbError(f"APK file not found: {apk}")
        return self.run(
            ["-s", serial, "install", "-r", str(apk.resolve())],
            timeout=max(self.timeout, 180),
        ).stdout.strip()

    @staticmethod
    def _require_authorized(state: str) -> None:
        if state != "device":
            raise AdbError(f"Target must be in device state; current state is {state}.")
