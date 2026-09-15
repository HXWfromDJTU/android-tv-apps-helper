#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from build_platform_packages import build as build_platform


def build(output: Path) -> dict[str, object]:
    return build_platform("workbuddy", output)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the WorkBuddy Skill ZIP.")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.output), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
