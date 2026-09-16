# Workflow States

The harness is the state authority. The Agent renders its `InteractionFrame`, submits the user's exact answer, and performs only the already-approved operation associated with the accepted transition. It does not author alternate questions or jump states.

## Entry and update

1. Resume an interrupted device mutation or recovery before anything else.
2. Read the installed version and check the official stable GitHub Release. Ignore prereleases.
3. If a newer stable version exists and the 24-hour global snooze is inactive, ask `UPDATE-Q1`: update after package verification, decline all reminders for 24 hours, view release notes, or exit.
4. Store the snooze outside the installed Skill so deletion/reinstallation does not erase it. During the snooze, do not prompt for a still newer version.
5. Download and verify the replacement before removing the current Skill; failed validation or installation leaves the current version usable.

## Automatic precheck

Run the limited read-only precheck without asking permission. It may locate ADB, inspect local interface/Wi-Fi facts, call `adb devices -l`, and use existing neighbor/mDNS data. It does not scan the subnet, probe arbitrary addresses, or run `adb connect`.

Never download or install ADB, Platform-Tools, an APK, or another dependency during or after this read-only entry. Missing tooling is a blocker to explain, not permission to repair the host. A `configure_adb` answer only advances to the path/guide question. Perform a download, host write, installation, scan, connection, or TV mutation only for an exact current `action_required` created after the harness accepts explicit approval.

The first business question is `PRECHECK-WIFI-Q1`. Its table shows what was actually checked and which devices are only candidates. It asks whether computer and TV use the same Wi-Fi. `PRECHECK-ADB-Q1` separately asks whether ADB/network/wireless debugging is enabled and contains the six-step guide plus the generic diagram.

## Discovery and target lock

Zero devices uses `DISCOVERY-NONE-Q1`. Context above the short component includes attempt count, blocker and same-Wi-Fi/ADB/IP/RSA instructions. Choices are passive retry, IP entry, brand guide, limited-scan details and safe exit; use native pages, never text-menu fallback. Active scanning needs separate scope display and approval. For an approved `PASSIVE-DISCOVERY-ACTION`, use `workflow-discover <session>` to execute and record fresh results together; no reused entry snapshot. A failed check means device count unknown, not zero.

For `unauthorized`, keep the same target candidate and ask about the television RSA prompt. For `offline`, reconnect only the selected target and never kill a shared ADB server when another device is active. For multiple devices, show manufacturer/model evidence and require one choice.

`TARGET-Q1` shows serial only in technical details; the main table shows friendly manufacturer/model/system identity. After confirmation, every device command binds `adb -s <verified-serial>`.

## Inventory and task menu

Read Android version, SDK, ABI, free space, current Home activity, installed packages, and catalog state. `TASK-Q1` uses only:

- 查看并选择推荐应用
- 检查当贝市场官方来源
- 设置电视默认桌面
- 检查应用问题
- 进入任务收尾

Selecting a task performs no mutation.

## Application selection and approvals

`APPS-Q1` shows index, name, purpose, version, installed state, and availability. Unavailable entries remain explained in the table but are not selectable. Use native multi-select when it fits; otherwise use native add/remove pages then “完成选择”. Never request numbered chat answers.

After valid selection, `DOWNLOAD-CONFIRM-Q1` repeats every selected name and version. Confirming it permits only source resolution, download, and file validation. The subsequent immutable install plan binds friendly plan name, hidden internal plan ID, target serial, APK SHA-256, command, impact, risk, and recovery. Installation requires another exact approval.

当贝市场 uses `official_direct`. If its fixed official page/CDN is unavailable or the identity is unverified, `DANGBEI-SOURCE-Q1` offers only retry official source, view official page, skip, or safe exit. Ordinary users are never asked to find or upload its APK.

## Default launcher and wallpaper

Emotn UI must already be installed or come from an authorized verified file. If unavailable, show that in the application table before selection.

Home-key routing and wallpaper replacement are separate actions and separate compatibility rows. Before either approval, show the verified manufacturer/model/system/build and classify each action as verified, high risk, or unknown. Never confuse HarmonyOS with HyperOS and never invent a probability for an unknown device.

After Emotn launch verification:

1. Ask whether to change the Home-key default launcher.
2. Ask whether to upload one custom wallpaper or use Emotn's default.
3. Context preceding every wallpaper component states that firmware may reset it after days, reboot, system update, or launcher update.
4. A custom image must be PNG/JPEG/WebP, at most 20 MB, and requires a separate apply confirmation.
5. Missing/invalid/failed upload remains on the same question and never implies default-wallpaper consent.
6. Keep the factory launcher package and data installed and enabled.

## Execution and evidence

Execute approved items one at a time and record stdout, stderr, exit code, and time with `workflow-action-result`. Until that command accepts non-empty evidence, the state remains a pending action and the Agent cannot render a later success question. A failed action returns to its bounded retry/back/exit decision and must not use completed wording. One predefined safe retry is allowed. New data clearing, downgrade, uninstall, package disable, Home change, or wallpaper change requires a new explicit question.

Report file validation, installation, launch, runtime signal, and on-site acceptance separately. Only the user's picture/sound/remote confirmation supports “现场使用正常”.

## Finish safety

Final task choices are:

- 结束本次任务，保留当前桌面和壁纸
- 继续其他电视操作
- 恢复本次会话开始时的桌面后结束

Restoring the session-start launcher is a new plan and approval. The recorded HOME must not be described as factory/OEM without separate evidence. Every completion, cancellation, and safe exit after ADB use routes to `FINISH-SAFETY-Q1` after artifacts are saved.

Match the shutdown guide in exact model/system, model family, vendor system, then generic order. Show the target, ADB/developer state, steps, and one question: both closed; show model guide; or keep enabled and finish with warning. The Agent does not silently disable developer mode. Disconnection is not proof; conflicting ADB reachability keeps the same question.

Use `final-report` only after a terminal state. The final reply begins with its status table; ✅ and ❌ come only from stored evidence records, not model wording.
