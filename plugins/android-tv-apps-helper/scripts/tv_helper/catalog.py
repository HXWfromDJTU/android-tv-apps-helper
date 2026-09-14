from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class CatalogError(ValueError):
    """Raised when catalog provenance or distribution policy is invalid."""


PROJECT_RELEASE_PREFIX = (
    "https://github.com/HXWfromDJTU/android-tv-apps-helper/releases/download/"
)
CLASH_RELEASE_PREFIX = (
    "https://github.com/MetaCubeX/ClashMetaForAndroid/releases/download/"
)
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def load_catalog(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _valid_https(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and bool(parsed.netloc)


def validate_catalog(catalog: dict[str, Any]) -> None:
    if catalog.get("schema_version") != 1 or not isinstance(catalog.get("apps"), list):
        raise CatalogError("Catalog must use schema_version 1 and contain apps.")
    seen: set[str] = set()
    for app in catalog["apps"]:
        app_id = app.get("id")
        if not app_id or app_id in seen:
            raise CatalogError("Every app id must be present and unique.")
        seen.add(app_id)
        distribution = app.get("distribution", {})
        mode = distribution.get("mode")
        assets = app.get("assets", [])
        if mode in {"pending_rights", "pending_file"}:
            if distribution.get("url") or any(asset.get("url") for asset in assets):
                raise CatalogError(f"Pending app {app_id} cannot expose a download URL.")
            continue
        if mode not in {"upstream_release", "project_release"}:
            raise CatalogError(f"Unsupported distribution mode for {app_id}: {mode}")
        if not assets:
            raise CatalogError(f"Downloadable app {app_id} must provide assets.")
        if mode == "project_release":
            evidence = distribution.get("redistribution_evidence")
            if not evidence or not distribution.get("license"):
                raise CatalogError(f"Project-hosted app {app_id} needs redistribution evidence and license.")
        for asset in assets:
            url = asset.get("url", "")
            digest = asset.get("sha256", "")
            if not _valid_https(url):
                raise CatalogError(f"Asset URL for {app_id} must be HTTPS.")
            if not SHA256.fullmatch(digest):
                raise CatalogError(f"Asset sha256 for {app_id} must contain 64 lowercase hex characters.")
            if not isinstance(asset.get("size"), int) or asset["size"] <= 0:
                raise CatalogError(f"Asset size for {app_id} must be positive.")
            if mode == "project_release" and not url.startswith(PROJECT_RELEASE_PREFIX):
                raise CatalogError(f"Project-hosted asset for {app_id} must use this project's GitHub Releases.")
            if app_id == "clash-meta" and not url.startswith(CLASH_RELEASE_PREFIX):
                raise CatalogError("Clash Meta must use its official GitHub Release URL.")


def eligible_downloads(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    validate_catalog(catalog)
    return [
        app
        for app in catalog["apps"]
        if app["distribution"]["mode"] in {"upstream_release", "project_release"}
    ]
