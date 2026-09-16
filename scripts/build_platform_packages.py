#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "android-tv-apps-helper"
SKILL_ROOT = PLUGIN_ROOT / "skills" / "android-tv-apps-helper"
PACKAGE_ROOT = "android-tv-apps-helper"
SUPPORTED_PLATFORMS = ("workbuddy", "doubao-work", "claude", "codex")


def _manifest_version() -> str:
    manifest = json.loads((PLUGIN_ROOT / "plugin.json").read_text(encoding="utf-8"))
    return str(manifest["version"])


def _frontmatter(platform: str, version: str) -> str:
    common = f"""---
name: android-tv-apps-helper
description: Use when connecting an Android TV over ADB, installing or inspecting TV APKs, simplifying the launcher, or diagnosing app launch, picture, sound, or remote-control problems.
platform: {platform}
"""
    if platform == "workbuddy":
        extra = f"""display_name: Android TV Apps Helper
display_name_en: Android TV Apps Helper
description_zh: 通过必答选择题安全连接 Android TV、核验并安装 APK、诊断画面声音和遥控问题。
description_en: Safely connect an Android TV, validate and install APKs, and diagnose playback or remote-control issues.
category: productivity
version: {version}
author: SwainWong
user-invocable: true
"""
    elif platform == "doubao-work":
        extra = f"""display_name: Android TV Apps Helper
description_zh: 通过必答选择题安全连接 Android TV、核验并安装 APK、诊断画面声音和遥控问题。
version: {version}
author: SwainWong
user-invocable: true
"""
    elif platform == "claude":
        extra = f"""metadata:
  version: {version}
  platforms: claude,codex,workbuddy,doubao-work
"""
    elif platform == "codex":
        extra = f"""display_name: Android TV Apps Helper
version: {version}
author: SwainWong
user-invocable: true
"""
    else:
        raise ValueError(f"Unsupported platform: {platform}")
    return common + extra + "---\n\n"


def _skill_body(platform: str) -> str:
    source = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    parts = source.split("---", 2)
    if len(parts) != 3:
        raise ValueError("Canonical SKILL.md is missing YAML frontmatter.")
    body = parts[2].lstrip()

    if platform == "workbuddy":
        for name in (
            "interaction-contract.md",
            "workflow.md",
            "adb-operations.md",
            "apk-policy.md",
            "platforms.md",
        ):
            body = body.replace(
                f"[references/{name}](references/{name})",
                f"@references/{name}",
            )

    body = body.replace("../../catalog/apps.json", "references/apps.json")
    if platform == "claude":
        body = body.replace(
            "python3 ../../scripts/tv-helper",
            'python3 "${CLAUDE_SKILL_DIR}/scripts/tv-helper"',
        )
    else:
        body = body.replace(
            "python3 ../../scripts/tv-helper",
            "python3 scripts/tv-helper",
        )
    if platform == "claude":
        adapter = """## Claude host routing

Claude Desktop uses `--host-platform claude-desktop --surface html` and references/html-interaction.md. Resolve the actual installed local Skill path; Desktop need not define CLAUDE_SKILL_DIR. Embedded UI requires separately registered MCP. Claude Code keeps `--host-platform claude --surface auto`: Call `AskUserQuestion` for native_required, preserving the exact payload and explicit consent. Never use a numbered-text menu.

"""
    elif platform in {"workbuddy", "doubao-work"}:
        adapter = """## Desktop HTML interaction adapter

New local-computer sessions use `--surface html` with this package's platform ID. Read references/html-interaction.md for embedded MCP installation/callbacks and local-browser fallback; wait for real clicks. Legacy native sessions remain supported: Call `AskUserQuestion` with exact payload for native_required, or migrate their pending question with resume-html. Never convert a blocked component into a numbered chat menu.

"""
    else:
        adapter = """## Codex HTML interaction adapter

Use `--surface html --host-platform codex` and references/html-interaction.md. Prefer a real installed/rendered MCP App; otherwise use serve-ui and keep wait-ui active. No Plan-mode switch is required for the browser choice UI. Existing request_user_input_async/native checkpoints may migrate using resume-html without discarding their question. Never ask the model to invent selections.

"""
    return body.replace("# Android TV Apps Helper\n", "# Android TV Apps Helper\n\n" + adapter, 1)


def _package_files(platform: str, version: str) -> dict[str, tuple[bytes, int]]:
    if platform not in SUPPORTED_PLATFORMS:
        raise ValueError(f"Unsupported platform: {platform}")
    files: dict[str, tuple[bytes, int]] = {
        "SKILL.md": (
            (_frontmatter(platform, version) + _skill_body(platform)).encode("utf-8"),
            0o644,
        ),
        "references/apps.json": (
            (PLUGIN_ROOT / "catalog" / "apps.json").read_bytes(),
            0o644,
        ),
        "references/THIRD_PARTY_NOTICES.md": (
            (REPO_ROOT / "THIRD_PARTY_NOTICES.md").read_bytes(),
            0o644,
        ),
    }
    references = SKILL_ROOT / "references"
    for source in sorted(references.glob("*.md")):
        content = source.read_text(encoding="utf-8").replace(
            "../../catalog/apps.json", "apps.json"
        )
        files[f"references/{source.name}"] = (content.encode("utf-8"), 0o644)

    data = PLUGIN_ROOT / "data"
    for source in sorted(path for path in data.rglob("*") if path.is_file()):
        relative = source.relative_to(data).as_posix()
        files[f"data/{relative}"] = (source.read_bytes(), 0o644)

    assets = SKILL_ROOT / "assets"
    for source in sorted(path for path in assets.rglob("*") if path.is_file()):
        relative = source.relative_to(assets).as_posix()
        files[f"assets/{relative}"] = (source.read_bytes(), 0o644)

    for source in sorted((SKILL_ROOT / "agents").glob("*.yaml")):
        files[f"agents/{source.name}"] = (source.read_bytes(), 0o644)

    scripts = PLUGIN_ROOT / "scripts"
    for source in sorted(path for path in scripts.rglob("*") if path.is_file()):
        if "__pycache__" in source.parts or source.suffix in {".pyc", ".apk"}:
            continue
        relative = source.relative_to(scripts).as_posix()
        mode = 0o755 if relative == "tv-helper" else 0o644
        files[f"scripts/{relative}"] = (source.read_bytes(), mode)
    return files


def build(
    platform: str,
    output: Path,
    version: str | None = None,
) -> dict[str, object]:
    if platform not in SUPPORTED_PLATFORMS:
        raise ValueError(f"Unsupported platform: {platform}")
    resolved_version = version or _manifest_version()
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    files = _package_files(platform, resolved_version)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative, (content, mode) in sorted(files.items()):
            info = zipfile.ZipInfo(
                f"{PACKAGE_ROOT}/{relative}",
                date_time=(1980, 1, 1, 0, 0, 0),
            )
            info.create_system = 3
            info.external_attr = mode << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, content)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    return {
        "output": str(output),
        "platform": platform,
        "version": resolved_version,
        "sha256": digest,
        "files": len(files),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a platform Skill ZIP.")
    parser.add_argument("--platform", required=True, choices=SUPPORTED_PLATFORMS)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--version")
    args = parser.parse_args()
    print(
        json.dumps(
            build(args.platform, args.output, args.version),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
