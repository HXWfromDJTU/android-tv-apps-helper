---
name: android-tv-apps-helper
description: Use when a user wants to connect an Android TV over ADB, install or inspect TV APKs, simplify the launcher, or diagnose app launch, picture, sound, or remote-control problems.
---

# Android TV Apps Helper

Guide one Android TV through a deterministic, reversible workflow. The harness owns wording, transitions, tables, validation, and approvals. The model supplies verified observations only.

## Start every invocation

Read [references/platforms.md](references/platforms.md), [references/interaction-contract.md](references/interaction-contract.md), and [references/workflow.md](references/workflow.md). Require a local-computer context with local shell and LAN access. Cloud-only execution stops before ADB and shows one bounded switch/retry/exit question.

Create a checkpoint with:

```sh
python3 ../../scripts/tv-helper init-session <artifact-dir>/session.json --surface <structured_form|text_menu> --host-platform <claude|codex|workbuddy|doubao-work> --execution-context local_computer
```

At the first safe point, use the harness entry command. It checks the official stable GitHub Release and then runs the automatic limited read-only precheck. A declined update suppresses every update reminder for 24 hours using stable user-data state outside the installed Skill. Never delete the working version before the new host package, Skill ID, version, and SHA-256 are validated. The precheck may locate ADB and run `adb version` and `adb devices -l`; it may not scan a subnet or connect to an unselected address.

```sh
python3 ../../scripts/tv-helper workflow-entry <artifact-dir>/session.json --installed-version 0.3.0
```

Use `question.component_prompt` and `question.component_options` for native cards; never render `prompt` alone. They contain progress, evidence, blocker, remediation, question and visible choices. For `short_text`, collect text and show only `component_options`; `options[0]` is not selectable. Otherwise show `rendered` unchanged. Never ask whether to begin precheck.

## Continue a question

Submit the exact visible answer through:

```sh
python3 ../../scripts/tv-helper workflow-answer <artifact-dir>/session.json --question-id <current-id> --value <answer>
```

On exit code 2, render the returned same question, table, blocker, and guidance. Do not execute any later action. Do not replace a pending question. Every reply contains the previous result/progress inside the active component, exactly one required question, mutually exclusive options, and an accepted-answer format.

When the result contains `action_required`, execute only that approved action. Record real stdout/stderr, exit code, inspected identity/hash, or read-only check in an evidence JSON object, then submit it before displaying any completion state:

```sh
python3 ../../scripts/tv-helper workflow-action-result <artifact-dir>/session.json --action-id <exact-action-id> --status <completed|failed|attention> --evidence <artifact-dir>/action-evidence.json
```

Never move past a pending action by writing the session or merely saying it succeeded.

For `PREPARE-INSTALL-PLAN-ACTION`, run `prepare-install-plan`; return its plan as evidence. Never hand-author one.

```sh
python3 ../../scripts/tv-helper prepare-install-plan <artifact-dir>/session.json --out <artifact-dir>/install-plan.json
```

## Operations

Read [references/adb-operations.md](references/adb-operations.md) before device commands and [references/apk-policy.md](references/apk-policy.md) before downloads. Use `adb -s <verified-serial>`. Downloads, installs, Home and wallpaper require separate confirmations. Never root, flash, reset, clear data, disable the factory launcher, or use unknown mirrors.

Use `../../catalog/apps.json` as the application source of truth.

Use the fixed task labels and application table. Multi-select uses the native control or numbers such as `1、2、3`; then confirm the resolved application names and versions before downloading. Downloading does not approve installation. Dangbei Market uses only its publisher-linked official source and never asks an ordinary user to find an APK.

After reading the target identity, run `prepare-device-context` with `data/device-guides.json` and `data/compatibility.json`. After Emotn UI is verified installed, separately ask about the default launcher and wallpaper. Custom wallpaper requires a valid image plus apply confirmation. Every wallpaper question states that vendor firmware may reset it after days, reboot, or update. Show the verified TV identity and independent Home/wallpaper risks before approval.

## Evidence and finish

Every interactive and final reply is table-first. Status symbols come from harness evidence: ✅ completed, ❌ attempted but incomplete, ⚠️ attention or user verification, ⏳ pending, ⏭️ skipped. Keep file validation, installation, launch, runtime signal, and on-site picture/sound/remote acceptance separate.

All exits after ADB use route through `FINISH-SAFETY-Q1`. Match the device guide and ask the user to close ADB/network/wireless debugging and the developer-options master switch. Disconnection alone is not proof. If ADB still responds after the user says it is closed, keep the same question and show the conflict.

After reaching a terminal state, render and save the harness final report:

```sh
python3 ../../scripts/tv-helper final-report <artifact-dir>/session.json --out <artifact-dir>/final-report.md
```
