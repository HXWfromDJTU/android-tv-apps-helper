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
        if mode not in {"pending_rights", "pending_file", "official_direct", "upstream_release", "project_release"}:
            raise CatalogError(f"Unsupported distribution mode for {app_id}: {mode}")
        # Review/redistribution fields describe metadata, not download permission.
        urls = [distribution.get("url"), distribution.get("resolved_url"), *[asset.get("url") for asset in assets]]
        if any(url and not _valid_https(url) for url in urls):
            raise CatalogError(f"Download URLs for {app_id} must use HTTPS.")
        if app_id == "clash-meta" and any(url and not url.startswith(CLASH_RELEASE_PREFIX) for url in urls):
            raise CatalogError("Clash Meta must use its official GitHub Release URL.")
        for asset in assets:
            url = asset.get("url", "")
            digest = asset.get("sha256", "")
            if not _valid_https(url):
                raise CatalogError(f"Asset URL for {app_id} must be HTTPS.")
            if digest and not SHA256.fullmatch(digest):
                raise CatalogError(f"Asset sha256 for {app_id} must contain 64 lowercase hex characters.")
            if asset.get("size") is not None and (not isinstance(asset["size"], int) or asset["size"] <= 0):
                raise CatalogError(f"Asset size for {app_id} must be positive.")
            if app_id == "clash-meta" and not url.startswith(CLASH_RELEASE_PREFIX):
                raise CatalogError("Clash Meta must use its official GitHub Release URL.")


def eligible_downloads(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    validate_catalog(catalog)
    return [
        app
        for app in catalog["apps"]
        if download_location(app)
    ]


def download_location(app: dict[str, Any]) -> str | None:
    assets = app.get("assets") or []
    distribution = app.get("distribution") or {}
    return next((asset["url"] for asset in assets if asset.get("url")), None) or distribution.get("resolved_url") or distribution.get("url")
