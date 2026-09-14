# Android TV Apps Helper v1 Design

## Goal

Build a public Codex plugin and reusable Skill that guides a user through Android TV discovery, ADB authorization, app selection, APK validation, explicit approval, installation, verification, and recovery without open-ended conversation drift.

## Approved interaction contract

- Every interactive turn contains exactly one question with explicit options.
- A required answer locks the current state. Ambiguous, missing, stale, or malformed answers repeat the same question without executing later work.
- Prefer a host-native required form or choice component. Fall back to an equivalent numbered text menu when the host has no supported UI surface or rendering fails.
- Recommendations are labeled but never preselected.
- Read-only inspection may run after the user starts the workflow. Installation, downgrade, uninstall, disable, data clearing, and launcher changes require an exact plan and explicit confirmation.
- Bind every device command to one verified ADB serial.

## Architecture

The repository is a one-plugin Codex marketplace. `plugins/android-tv-apps-helper` contains the plugin manifest, Skill, references, catalog, and Python harness. The harness stores atomic JSON session checkpoints, validates question answers, wraps ADB with an explicit target, and validates APK files before a plan can be approved.

The Skill chooses the host interaction surface at runtime. UI rendering is host-owned; the plugin never emits fake HTML or raw ChatCut widget tags. The Python harness provides deterministic state and safety checks shared by UI and text modes.

## APK distribution policy

- Clash Meta for Android always resolves to the official `MetaCubeX/ClashMetaForAndroid` GitHub Release. It is never mirrored by this project.
- APKs mirrored in this project's GitHub Releases require a local file, cryptographic hash, known upstream identity, and documented redistribution permission.
- SmartTube 32.10 Stable is eligible for the v1 project Release because the local file matches the official GitHub asset digest and the upstream repository uses the MIT license.
- Proprietary or unclear third-party APKs remain `pending_rights`; missing binaries remain `pending_file`. These states are visible to users and cannot resolve to a download URL.
- APK binaries live in GitHub Releases, not Git history. The repository stores only catalog metadata, hashes, provenance, and notices.

## v1 boundaries

v1 includes plugin installation metadata, the guided Skill, deterministic session/question handling, ADB preflight and device inspection, APK catalog/provenance checks, guarded install planning, unit tests, and a public GitHub Release for eligible assets. It does not root, flash, factory-reset, silently disable system packages, or claim audiovisual acceptance without a user's on-site confirmation.

## Acceptance

- Plugin and Skill validators pass.
- Unit tests prove invalid answers cannot advance state and unapproved plans cannot install.
- Tests prove every ADB operation uses the selected serial.
- Catalog validation proves Clash URLs remain on the official repository and project-hosted entries have provenance and hashes.
- The public GitHub repository and v0.1.0 Release are accessible without authentication.
