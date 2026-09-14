---
name: android-tv-apps-helper
description: Use when a user wants to connect an Android TV over ADB, install or inspect TV APKs, simplify the launcher, or diagnose app launch, picture, sound, or remote-control problems.
---

# Android TV Apps Helper

Guide one verified Android TV through a stateful, reversible workflow. The Agent owns inspection and command execution; the user answers one bounded question at each decision.

## Required interaction

Read [references/interaction-contract.md](references/interaction-contract.md) before the first reply. Every interactive reply ends with exactly one required question and explicit options. Prefer a supported host-native form; fall back to the same numbered text menu. Never preselect a recommendation or advance past an invalid, ambiguous, missing, stale, or malformed answer.

Create a session checkpoint with `../../scripts/tv-helper init-session <output>/session.json --surface <structured_form|text_menu>`. Persist each pending question before showing it and validate the submitted answer through the harness.

## Workflow

Read [references/workflow.md](references/workflow.md), then follow its current state rather than improvising a new questionnaire:

1. Ask whether to begin the read-only preflight.
2. Locate ADB, discover devices, resolve `unauthorized` or `offline`, show the device identity, and require target confirmation.
3. Inspect Android version, ABI, storage, launcher, and installed packages.
4. Ask the user to choose one task: recommended setup, selected apps, local APK, launcher cleanup, diagnosis, or finish.
5. Validate prerequisites and show the exact numbered plan, impact, evidence, and recovery path.
6. Require explicit consent before every mutation class not already covered by the approved plan.
7. Execute one item at a time, verify it, and ask for on-site picture, sound, and remote acceptance.
8. Show a final report and ask whether to finish or continue.

If the network, target serial, APK digest, action, or risk changes, invalidate prior approval and return to the matching question.

## Operations

Read [references/adb-operations.md](references/adb-operations.md) for connection, inspection, install, launcher, verification, and recovery commands. Every device command uses `adb -s <verified-serial>`. Do not root, flash, factory-reset, silently clear data, or remove/disable the current launcher before its replacement passes launch, Home-key, and remote-control acceptance.

Read [references/apk-policy.md](references/apk-policy.md) before resolving or installing an APK. Use `../../catalog/apps.json` as the source of truth. Clash Meta must remain on its official GitHub Release. A project-hosted APK must have a verified digest and redistribution evidence. Treat `pending_rights` and `pending_file` as unavailable; explain the exact status and present options to skip, use an authorized local file, or return.

## Evidence and stopping

Keep file validation, installation, launch, runtime signals, and on-site acceptance separate. Only user-confirmed picture, sound, and remote operation supports “正常运作”. A safe automatic retry may run once. After repeated failure, preserve logs, mark the item incomplete, and ask whether to skip, choose another route, or finish.

End with changed items, evidence level, incomplete items, intentionally preserved items, recovery commands, and the artifact directory. Ask a final explicit question before telling the user to close ADB debugging.
