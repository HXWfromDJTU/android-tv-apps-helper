#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from build_platform_packages import REPO_ROOT, SUPPORTED_PLATFORMS, build


def build_release(output_dir: Path) -> dict[str, object]:
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(
        (
            REPO_ROOT
            / "plugins"
            / "android-tv-apps-helper"
            / "plugin.json"
        ).read_text(encoding="utf-8")
    )
    version = str(manifest["version"])
    artifacts: list[dict[str, object]] = []
    for platform in SUPPORTED_PLATFORMS:
        filename = f"android-tv-apps-helper-{platform}-v{version}.zip"
        artifacts.append(build(platform, output_dir / filename, version))

    checksums = "".join(
        f"{artifact['sha256']}  {Path(str(artifact['output'])).name}\n"
        for artifact in sorted(artifacts, key=lambda item: str(item["platform"]))
    )
    (output_dir / "SHA256SUMS").write_text(checksums, encoding="utf-8")
    shutil.copyfile(
        REPO_ROOT / "docs" / "platform-compatibility.json",
        output_dir / "platform-compatibility.json",
    )
    return {
        "output_dir": str(output_dir),
        "version": version,
        "artifacts": artifacts,
        "checksums": str(output_dir / "SHA256SUMS"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build all release Skill assets.")
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(build_release(args.output_dir), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
