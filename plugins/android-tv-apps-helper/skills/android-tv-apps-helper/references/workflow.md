# Workflow States

## Host preflight

Before S0, identify the host and prove the Skill can run local commands and access the same LAN as the TV. Initialize the checkpoint with `--host-platform` and `--execution-context local_computer`. 豆包工作 must use its local-computer task, not cloud computer. If the host cannot provide local execution, show the verified limitation and ask exactly one question: switch to local mode, retry detection, or safe exit. Do not run ADB and do not create a false success record.

## S0 Start

Detect whether a host-native structured input surface is available. Create `session.json`. Ask `S0-Q1`: begin read-only checks, view scope, or safe exit. Do not run preflight until the user explicitly chooses begin.

## S1 ADB preflight

Locate and run `adb version`. If missing, ask: install official Google Platform-Tools, submit an existing absolute path, or exit. A submitted path is a separate required `short_text` question.

## S2 Device discovery

Run `adb devices -l` and mDNS discovery before any subnet probe. Zero devices: retry once, then ask to rescan after checking Wi-Fi, submit an IP, or exit. Multiple devices: show numbered IP/model candidates and ask for one. A submitted IP is a separate required `short_text` question.

## S3 Authorization

Branch on the reported state:

- `device`: continue.
- `unauthorized`: ask the user to accept the TV's RSA prompt, report no prompt, retry, or exit.
- `offline`: reconnect the target safely; do not kill a shared ADB server when other active devices exist.
- unreachable: return to discovery.

## S4 Target lock

Show serial, manufacturer, model, Android version, SDK, and ABI. Ask to confirm, choose another TV, or exit. Save the confirmed serial. All later device commands bind to it.

## S5 Read-only inventory

Inspect free space, current HOME activity, installed packages, and known catalog versions. Show a concise result, then ask one task:

1. Recommended setup.
2. Select apps.
3. Local APK.
4. Launcher cleanup.
5. Diagnose an installed app.
6. Finish and report.
0. Safe exit.

Selections and paths are separate required questions.

## S6-S8 Plan

Resolve the selected catalog entry or local file, read [apk-policy.md](apk-policy.md), validate prerequisites, and classify each item as executable, pending rights, missing, incompatible, already installed, or needing a risky replacement.

Show an immutable numbered plan with target serial, APK path/source, version, size, SHA-256, command, effect, risk, and recovery. Ask: approve all, choose item numbers, modify, cancel/report, or safe exit. Any changed serial, digest, command, or risk invalidates approval.

## S9 Execute

Checkpoint before each mutation. Execute only approved plan IDs, one item at a time. Capture stdout, stderr, exit status, and timestamp. Safe retry limit: one. Clearing data, uninstalling a conflicting signature, downgrade, package disable, or launcher change always needs a new `explicit_consent` question.

## S10 Verify

Verify package/version and foreground activity. Report separate evidence levels: file, installed, launched, runtime signal, and on-site accepted. Ask the user to select: all normal, no picture, no sound, remote problem, launch/crash problem, defer acceptance, or safe exit.

Collect bounded relevant logs for failures. If a safe repair exists, present it as a new plan question. Otherwise mark incomplete and continue to the next planned item.

## S11 Finish

Show target identity, changes, evidence levels, failures, intentionally preserved items, recovery commands, and artifact path. Ask: finish and close debugging, continue incomplete work, keep current setup and exit. When resuming a paused session with no pending question, revalidate network, serial, ADB state, and APK digest first.
