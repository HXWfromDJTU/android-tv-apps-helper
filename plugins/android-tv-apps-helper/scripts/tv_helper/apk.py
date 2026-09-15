from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

from .session import SessionStore


class ApkError(RuntimeError):
    """Raised when APK validation or an installation approval gate fails."""


PLAN_FIELDS = ("action", "app_id", "serial", "apk", "rollback")


def _plan_id(plan: dict[str, Any]) -> str:
    try:
        body = {key: plan[key] for key in PLAN_FIELDS}
    except KeyError as error:
        raise ApkError(f"Install plan is missing required field: {error.args[0]}") from error
    canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]


def _require_unchanged_plan(plan: dict[str, Any]) -> None:
    if plan.get("plan_id") != _plan_id(plan):
        raise ApkError("The install plan changed after its plan_id was created.")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_apk(path: Path, *, expected_sha256: str | None = None) -> dict[str, Any]:
    apk = Path(path)
    if not apk.is_file():
        raise ApkError(f"APK file not found: {apk}")
    if not zipfile.is_zipfile(apk):
        raise ApkError("APK is not a valid ZIP archive.")
    try:
        with zipfile.ZipFile(apk) as archive:
            if "AndroidManifest.xml" not in archive.namelist():
                raise ApkError("APK ZIP does not contain AndroidManifest.xml.")
            corrupt = archive.testzip()
            if corrupt:
                raise ApkError(f"APK ZIP contains a corrupt member: {corrupt}")
    except zipfile.BadZipFile as error:
        raise ApkError("APK is not a valid ZIP archive.") from error
    digest = _sha256(apk)
    if expected_sha256 and digest != expected_sha256.lower():
        raise ApkError("APK SHA-256 does not match the approved catalog digest.")
    return {
        "path": str(apk.resolve()),
        "filename": apk.name,
        "size": apk.stat().st_size,
        "sha256": digest,
    }


def create_install_plan(
    *,
    app_id: str,
    serial: str,
    apk_path: Path,
    expected_sha256: str,
) -> dict[str, Any]:
    if not serial.strip():
        raise ApkError("A verified target serial is required.")
    inspection = inspect_apk(apk_path, expected_sha256=expected_sha256)
    body = {
        "action": "install",
        "app_id": app_id,
        "serial": serial,
        "apk": inspection,
        "rollback": "Uninstall or reinstall the previously recorded version after explicit confirmation.",
    }
    body["plan_id"] = _plan_id(body)
    body["status"] = "planned"
    return body


def approve_plan(session: SessionStore, plan: dict[str, Any], *, confirmation: str) -> None:
    if plan.get("requires_revalidation"):
        raise ApkError("The migrated install plan requires revalidation before approval.")
    if confirmation != "confirm_install":
        raise ApkError("The install plan requires the explicit confirm_install answer.")
    _require_unchanged_plan(plan)
    approved = dict(plan)
    approved["status"] = "approved"
    session.set_approved_plan(approved)


def install_approved(
    session: SessionStore,
    runner: Any,
    plan: dict[str, Any],
    *,
    device_state: str,
) -> str:
    if plan.get("requires_revalidation"):
        raise ApkError("The migrated install plan requires revalidation before installation.")
    _require_unchanged_plan(plan)
    saved = session.read().get("approved_plan")
    if isinstance(saved, dict) and saved.get("requires_revalidation"):
        raise ApkError("The saved install plan requires revalidation before installation.")
    if not saved or saved.get("status") != "approved" or saved.get("plan_id") != plan.get("plan_id"):
        raise ApkError("This exact install plan has not been approved.")
    if saved.get("serial") != plan.get("serial"):
        raise ApkError("The approved plan is bound to a different target serial.")
    if _plan_id(saved) != _plan_id(plan):
        raise ApkError("The approved plan body does not match the requested install.")
    inspection = inspect_apk(
        Path(plan["apk"]["path"]),
        expected_sha256=plan["apk"]["sha256"],
    )
    if inspection["sha256"] != saved["apk"]["sha256"]:
        raise ApkError("The APK changed after approval.")
    return runner.install(
        plan["serial"],
        Path(plan["apk"]["path"]),
        state=device_state,
    )
