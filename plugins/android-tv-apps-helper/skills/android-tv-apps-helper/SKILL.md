---
name: android-tv-apps-helper
description: Use when a user wants to connect an Android TV over ADB, install or inspect TV APKs, simplify the launcher, or diagnose app launch, picture, sound, or remote-control problems.
---

# Android TV Apps Helper

The harness owns questions, transitions, validation and approvals; supply verified observations.

## Start every invocation

Read [references/platforms.md](references/platforms.md), [references/interaction-contract.md](references/interaction-contract.md), and [references/workflow.md](references/workflow.md). Require a local-computer context with local shell and LAN access. Cloud-only execution stops before ADB and shows one bounded switch/retry/exit question.

Follow platforms.md capability detection. In Codex, prefer available `request_user_input_async` using `--native-tool request_user_input_async`. Initialize:

```sh
python3 ../../scripts/tv-helper init-session <artifact-dir>/session.json --surface auto --host-platform <claude|codex|workbuddy|doubao-work> --execution-context local_computer
```

Run entry immediately for Release checks, 24-hour update snooze and passive precheck. Validate replacement identity/version/SHA-256 before updating. Precheck locates ADB and runs `adb version` and `adb devices -l`; it cannot scan or connect.

```sh
python3 ../../scripts/tv-helper workflow-entry <artifact-dir>/session.json --installed-version 0.3.4
```

For `native_required`, display `context_markdown`, then call `tool_name` with exact `tool_input`. Keep context outside the short card. Every decision requires native choices; never ask for numbered-text answers. Record observed tool failures:

For `response_delivery=async_user_message`, preserve question/presentation IDs and yield until the actual user reply. Tool acknowledgement or preselection is not an answer.

```sh
python3 ../../scripts/tv-helper record-surface-failure <artifact-dir>/session.json --question-id <presentation.question_id> --presentation-id <presentation.presentation_id> --tool-name <presentation.tool_name> --reason <native_tool_not_exposed|native_tool_call_failed|native_tool_render_failed> --detail <observed-error>
```

Retry the returned native presentation once. For `native_blocked`, display its table and pause; resume only after host recovery using `resume-native`. Never use a text menu. Preserve options, explicit consent and safe exit.

## Continue a question

Submit the exact visible answer through:

```sh
python3 ../../scripts/tv-helper workflow-native-answer <artifact-dir>/session.json --question-id <current-id> --presentation-id <current-presentation-id> --value <returned-label-or-value>
```

Use `--values-json` for actual native multi-select. Pagination/toggles stay in the current question. Input starts with a native fill-information choice; only `accepts_free_input=true` permits the supplemental input field after the options. On exit code 2, redisplay context and the returned native card, not a text menu.

When the result contains `action_required`, execute only that approved action. Record real stdout/stderr, exit code, inspected identity/hash, or read-only check in an evidence JSON object, then submit it before displaying any completion state:

```sh
python3 ../../scripts/tv-helper workflow-action-result <artifact-dir>/session.json --action-id <exact-action-id> --status <completed|failed|attention> --evidence <artifact-dir>/action-evidence.json
```

Never move past a pending action by writing the session or merely saying it succeeded.

For `PASSIVE-DISCOVERY-ACTION`, run `workflow-discover <session>`: it executes and records fresh results together. Never reuse the entry precheck or manually reconstruct discovery evidence.

Precheck is read-only. Never download or install ADB, Platform-Tools, an APK, or dependencies without `action_required` after an explicit accepted answer. `configure_adb`, recommendations, and model inference are not approval.

For `PREPARE-INSTALL-PLAN-ACTION`, run `prepare-install-plan`; return its plan as evidence. Never hand-author one.

```sh
python3 ../../scripts/tv-helper prepare-install-plan <artifact-dir>/session.json --out <artifact-dir>/install-plan.json
```

## Operations

Read [references/adb-operations.md](references/adb-operations.md) before device commands and [references/apk-policy.md](references/apk-policy.md) before downloads. Use `adb -s <verified-serial>`. Downloads, installs, Home and wallpaper require separate confirmations. Never root, flash, reset, clear data, disable the factory launcher, or use unknown mirrors.

Use `../../catalog/apps.json`. All apps stay selectable; source-review status never blocks downloading. For missing URLs, resolve after confirmation per apk-policy.md.

Use fixed task labels and the application table. Use native multi-select or native toggle pages; confirm names and versions before downloading. Download is not install approval. Dangbei uses only publisher-linked sources.

After reading target identity, run `prepare-device-context` with the packaged guide and compatibility data. After verifying Emotn UI, ask separately about Home and wallpaper. Custom wallpaper needs a valid image and apply confirmation; always show identity, independent risks, and possible vendor reset.

## Evidence and finish

Every interactive and final reply is table-first. Status symbols come from harness evidence: ✅ completed, ❌ attempted but incomplete, ⚠️ attention or user verification, ⏳ pending, ⏭️ skipped. Keep file validation, installation, launch, runtime signal, and on-site picture/sound/remote acceptance separate.

All exits after ADB use route through `FINISH-SAFETY-Q1`. Match the device guide and ask the user to close ADB/network/wireless debugging and the developer-options master switch. Disconnection alone is not proof. If ADB still responds after the user says it is closed, keep the same question and show the conflict.

After reaching a terminal state, render and save the harness final report:

```sh
python3 ../../scripts/tv-helper final-report <artifact-dir>/session.json --out <artifact-dir>/final-report.md
```
