from __future__ import annotations

import re
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse
from .catalog import download_location


class DownloadError(ValueError):
    """Raised when a download source or APK identity fails closed."""


def redirect_allowed(url: str, allowed_hosts: Iterable[str]) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.hostname in set(allowed_hosts)


def resolve_official_url(
    html: str, publisher_page: str, allowed_hosts: Iterable[str]
) -> str:
    candidates = re.findall(r'''href=["']([^"']+\.apk(?:\?[^"']*)?)["']''', html, flags=re.IGNORECASE)
    for candidate in candidates:
        absolute = urljoin(publisher_page, candidate)
        if redirect_allowed(absolute, allowed_hosts):
            return absolute
    raise DownloadError("官方页面没有提供允许域名内的 APK 下载地址。")


def validate_download_identity(
    expected: dict[str, Any], actual: dict[str, Any]
) -> None:
    for field in (
        "package",
        "version_name",
        "version_code",
        "min_sdk",
        "abi",
        "signing_sha256",
        "size",
        "sha256",
    ):
        value = expected.get(field)
        if not value or actual.get(field) != value:
            raise DownloadError(f"APK {field} does not match the verified catalog identity.")


def _downloadable(app: dict[str, Any]) -> bool:
    return bool(download_location(app))


def app_selection_rows(
    apps: Iterable[dict[str, Any]], installed: dict[str, str]
) -> list[dict[str, Any]]:
    rows = []
    for index, app in enumerate(apps, 1):
        installed_version = installed.get(str(app["id"]))
        current = installed_version == app.get("version")
        enabled = True
        if current:
            availability = "已安装此版本；仍可选择重新下载"
        elif _downloadable(app):
            availability = "可以下载"
        else:
            availability = "可选择；确认后由 Agent 查找下载地址"
        rows.append(
            {
                "index": index,
                "id": app["id"],
                "name": app["name"],
                "version": app.get("version", "未知"),
                "purpose": app.get("purpose", "电视应用"),
                "installed": installed_version or "未安装",
                "enabled": enabled,
                "availability": availability,
            }
        )
    return rows


def named_download_confirmation(
    apps: Iterable[dict[str, Any]], selected_ids: Iterable[str]
) -> dict[str, Any]:
    by_id = {str(app["id"]): app for app in apps}
    selected = tuple(selected_ids)
    if not selected:
        raise DownloadError("下载清单不能为空。")
    missing = [app_id for app_id in selected if app_id not in by_id]
    if missing:
        raise DownloadError(f"未知应用：{', '.join(missing)}")
    display_names = tuple(
        f"{by_id[app_id]['name']} {by_id[app_id].get('version', '未知版本')}"
        for app_id in selected
    )
    return {
        "question_id": "DOWNLOAD-CONFIRM-Q1",
        "selected_ids": selected,
        "display_names": display_names,
        "prompt": "是否下载以下应用：" + "、".join(display_names) + "？",
        "options": ("confirm_download", "back_to_apps", "safe_exit"),
    }
