---
name: android-tv-apps-helper
description: Use when a user wants to connect an Android TV over ADB, install or inspect TV APKs, simplify the launcher, or diagnose app launch, picture, sound, or remote-control problems.
---

# Android TV Apps Helper

Guide one Android TV through a deterministic, reversible workflow. The harness owns questions, transitions, validation, and approvals; the model supplies verified observations.

## Start every invocation

Read [references/platforms.md](references/platforms.md), [references/interaction-contract.md](references/interaction-contract.md), and [references/workflow.md](references/workflow.md). Require a local-computer context with local shell and LAN access. Cloud-only execution stops before ADB and shows one bounded switch/retry/exit question.

Create a checkpoint with:

```sh
python3 ../../scripts/tv-helper init-session <artifact-dir>/session.json --surface auto --host-platform <claude|codex|workbuddy|doubao-work> --execution-context local_computer
```

Run the entry command immediately. It checks the official stable Release, honors the persistent 24-hour update snooze, and runs the limited read-only precheck. Keep the working version until its replacement identity, version, and SHA-256 pass. Precheck may locate ADB and run `adb version` and `adb devices -l`; it cannot scan or connect.

```sh
python3 ../../scripts/tv-helper workflow-entry <artifact-dir>/session.json --installed-version 0.3.2
```

For `native_required`, always display `context_markdown` visibly before calling `tool_name` with exact `tool_input`. The card contains only the question and choices; results, risks and guidance stay outside. Never append context to the title/question or substitute text choices. Map labels through `answer_value_map`. Record observed native-tool failures before using text:

```sh
python3 ../../scripts/tv-helper record-surface-failure <artifact-dir>/session.json --question-id <presentation.question_id> --presentation-id <presentation.presentation_id> --tool-name <presentation.tool_name> --reason <native_tool_not_exposed|native_tool_call_failed|native_tool_render_failed> --detail <observed-error>
```

For `text_fallback`, show `rendered` unchanged. `native_tool_call_failed` and `native_tool_render_failed` apply only to the current question; retry native controls for the next compatible question. `native_tool_not_exposed` applies to the current host session. Never omit choices, preselect, hide `safe_exit` in Other, or ask to begin precheck.

## Continue a question

Submit the exact visible answer through:

```sh
python3 ../../scripts/tv-helper workflow-answer <artifact-dir>/session.json --question-id <current-id> --value <answer>
```

On exit code 2, redisplay the context table, blocker and guidance, then the same short question and options. Do not execute any later action or replace a pending question. Each reply has visible previous results/progress, one required question, mutually exclusive options, and an accepted-answer format.

When the result contains `action_required`, execute only that approved action. Record real stdout/stderr, exit code, inspected identity/hash, or read-only check in an evidence JSON object, then submit it before displaying any completion state:

```sh
python3 ../../scripts/tv-helper workflow-action-result <artifact-dir>/session.json --action-id <exact-action-id> --status <completed|failed|attention> --evidence <artifact-dir>/action-evidence.json
```

Never move past a pending action by writing the session or merely saying it succeeded.

Precheck is read-only. Never download or install ADB, Platform-Tools, an APK, or dependencies without `action_required` after an explicit accepted answer. `configure_adb`, recommendations, and model inference are not approval.

For `PREPARE-INSTALL-PLAN-ACTION`, run `prepare-install-plan`; return its plan as evidence. Never hand-author one.

```sh
python3 ../../scripts/tv-helper prepare-install-plan <artifact-dir>/session.json --out <artifact-dir>/install-plan.json
```

## Operations

Read [references/adb-operations.md](references/adb-operations.md) before device commands and [references/apk-policy.md](references/apk-policy.md) before downloads. Use `adb -s <verified-serial>`. Downloads, installs, Home and wallpaper require separate confirmations. Never root, flash, reset, clear data, disable the factory launcher, or use unknown mirrors.

Use `../../catalog/apps.json` as the application source of truth.

Use the fixed task labels and application table. Multi-select uses the native control or `1、2、3`; confirm resolved names and versions before downloading. Download is not install approval. Dangbei Market uses only its publisher-linked official source.

After reading target identity, run `prepare-device-context` with the packaged guide and compatibility data. After verifying Emotn UI, ask separately about Home and wallpaper. Custom wallpaper needs a valid image and apply confirmation; always show identity, independent risks, and possible vendor reset.

## Evidence and finish

Every interactive and final reply is table-first. Status symbols come from harness evidence: ✅ completed, ❌ attempted but incomplete, ⚠️ attention or user verification, ⏳ pending, ⏭️ skipped. Keep file validation, installation, launch, runtime signal, and on-site picture/sound/remote acceptance separate.

All exits after ADB use route through `FINISH-SAFETY-Q1`. Match the device guide and ask the user to close ADB/network/wireless debugging and the developer-options master switch. Disconnection alone is not proof. If ADB still responds after the user says it is closed, keep the same question and show the conflict.

After reaching a terminal state, render and save the harness final report:

```sh
python3 ../../scripts/tv-helper final-report <artifact-dir>/session.json --out <artifact-dir>/final-report.md
```
