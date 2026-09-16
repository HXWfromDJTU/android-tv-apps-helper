# Platform Validation — v0.3.0

Validation date: 2026-09-16 (Asia/Shanghai)

## Evidence rules

The platform matrix separates artifact build, installation, explicit Skill invocation, dialogue-contract behavior, and physical-TV acceptance. A later level never fills an earlier missing level. Seeing a ZIP or reading `SKILL.md` is not installation evidence, and command success is not on-site picture/sound/remote acceptance.

The live dialogue probe is the same on every available host:

1. Start a new local-computer conversation and explicitly invoke Android TV Apps Helper for a read-only precheck. The response must run the automatic limited precheck, show a table and exactly one `PRECHECK-WIFI-Q1`, include all choices and `安全退出`, and perform no ADB/Platform-Tools download, active scan, connection, or TV mutation. Text menus use shortcut `0`; native cards submit the stable value `safe_exit` even when the host visually assigns another row number.
2. Submit an unlisted ambiguous answer such as `继续` or `continue`. The host must pass that exact value to the harness. Exit code 2 must preserve `PRECHECK-WIFI-Q1`, increment `attempts`, redisplay its context and options, and execute no later action.
3. Submit the visible safe-exit choice (`0` in text menus, `safe_exit` from native controls). The session must end safely and state that no TV operation ran.

Public evidence below redacts local account names, IP addresses, SSIDs, serials, and temporary paths.

## Result summary

| Platform | Artifact | Removal | Installation | Explicit invocation | Precheck + invalid-answer lock | Safe exit | Deeper flow / physical TV |
|---|---|---|---|---|---|---|---|
| Codex | ✅ | ✅ Previous RC4 copy moved recoverably to Trash before the stable package was installed | ✅ Stable v0.3.0 Codex ZIP installed to the personal Skill directory and entrypoint checked | ✅ Fresh Codex CLI 0.154.0 resolved v0.3.0 during RC4 live acceptance | ✅ RC4 live acceptance plus stable-package automated checks: table-first `PRECHECK-WIFI-Q1`; `继续` rejected with attempts = 1; same options retained | ✅ RC4 live Codex submitted `0`; final report recorded no TV operation | ⏭️ Stable-package GUI dialogue, app selection, Home, wallpaper, ADB shutdown and physical TV not run |
| WorkBuddy 中国大陆版 | ✅ | ✅ Previous RC4 target moved recoverably to Trash before stable installation | ✅ Stable v0.3.0 WorkBuddy ZIP installed through a hash-verified local filesystem fallback and entrypoint checked | ✅ New WorkBuddy task invoked the installed RC4 Skill | ✅ RC4 live acceptance: native required card contained progress, blocker, guide, and four non-duplicated choices; `continue` rejected and the same card returned | ⚠️ RC4 live native card displayed safe exit as row 4, but submitted stable `safe_exit` successfully | ⏭️ Stable-package dialogue, app selection, Home, wallpaper, ADB shutdown and physical TV not run |
| 豆包工作 | ✅ | ✅ Previous Skill deleted for RC4; stable v0.3.0 then replaced the same Skill in the client | ✅ Stable v0.3.0 ZIP uploaded; replacement confirmed; security detection completed; Skill visible and enabled | ✅ New 本地电脑 task invoked the stable installed Skill | ✅ Stable live acceptance: table-first `PRECHECK-WIFI-Q1`; `继续` rejected with a ❌ row and the same four choices returned | ✅ Stable live native card submitted `安全退出`; final report says no connection, scan, mutation, or tool download | ⏭️ App selection, Home, wallpaper, ADB shutdown and physical TV not run |
| Claude Desktop / Code | ✅ automated package checks | ⏭️ Deferred by user request | ⏭️ Not run | ⏭️ Not run | ⏭️ Not run | ⏭️ Not run | ⏭️ Not run |

## Candidate artifacts used for live validation

The final candidate was GitHub prerelease `v0.3.0-rc.4`. Its locally verified SHA-256 values were:

| Artifact | SHA-256 |
|---|---|
| `android-tv-apps-helper-workbuddy-v0.3.0.zip` | `d960a38507e53a76255247667307a692e5dc5d7ee160e28c662d2e1f50708f89` |
| `android-tv-apps-helper-doubao-work-v0.3.0.zip` | `3b7ec6d615a28b4ab7803b35c18d7e72dc0104f8c3a5b9bcdc9b1b5a444faede` |
| `android-tv-apps-helper-claude-v0.3.0.zip` | `eff1496ff16a0a1ae8d4604ce6486c03e873a2ba371de500dee86a82b0374596` |
| `android-tv-apps-helper-codex-v0.3.0.zip` | `808ad3f198adde1f95c207cf214a17589099d043f9cbe7bf138f279eceb08d0a` |

Final `v0.3.0` artifacts are rebuilt from merged `main`; their release hashes may therefore differ and are published in `SHA256SUMS`.

## Stable v0.3.0 post-release installation

The public stable release is [`v0.3.0`](https://github.com/HXWfromDJTU/android-tv-apps-helper/releases/tag/v0.3.0), built from commit `f5c750cdcd666cbab6f6e280881013c1ca7d0a91`. The release is public, non-draft, and non-prerelease. Its published package hashes are:

| Artifact | SHA-256 |
|---|---|
| `android-tv-apps-helper-workbuddy-v0.3.0.zip` | `a7476106f6e5ec8124943d361830708d67b5adb58b043648e63e2cacfc56a4ee` |
| `android-tv-apps-helper-doubao-work-v0.3.0.zip` | `d7fb72d335df24cab47795e1a0ae7ba5500de6b2cb55043dbfd451ba12887917` |
| `android-tv-apps-helper-claude-v0.3.0.zip` | `fde0cbb55301833900caeb2e87bd7c92f74e194c6722883453e835771a6bd56f` |
| `android-tv-apps-helper-codex-v0.3.0.zip` | `97758971a02c9d7201ba9085447d51d5bc3ae5fcd36d636bff26cb07d8306476` |

- Codex and WorkBuddy received the exact stable packages after SHA-256 verification. Their previous RC4 directories were moved to Trash with timestamped names, and the packaged `tv-helper --help` entrypoints passed. Their shared core workflow hash is `4eeb79af16b51373b6aaa99956e5bc7a5f5f55c59a811b776eb3d4b5ff2b239c`.
- 豆包工作 received the exact stable Doubao package through `上传技能`. The client displayed the irreversible same-name replacement confirmation, the user confirmed it, and the client then displayed `安全检测已完成`; the Skill remained visible and enabled.
- A new stable-package 豆包工作 local-computer task invoked the installed Skill. It ran `workflow-entry` with `doubao-work / local_computer / structured_form`, displayed the status table and one self-contained `PRECHECK-WIFI-Q1`, rejected `继续` with a ❌ row while preserving the question, and accepted the native `安全退出` option. Its final report recorded no TV operation, no active scan or connection, and no ADB, Platform-Tools, or APK download/install.
- Stable-package Codex and WorkBuddy replacement/entrypoint checks are current; their live dialogue evidence remains the RC4 acceptance described below. The fixes added after RC4—session-start launcher restore binding, exact prechecked ADB path binding, and non-duplicated finish choices—are covered by the final automated suite rather than a physical-TV run.

## WorkBuddy live evidence

1. The earlier RC3 conversation-install path succeeded, proving that WorkBuddy can install a GitHub Release ZIP from a normal Agent prompt.
2. During the first RC3 dialogue, WorkBuddy tried to download Platform-Tools after reporting missing ADB, without an approved action. The run was stopped before any download or install completed. No Platform-Tools directory or temporary archive remained.
3. The Skill was patched so precheck can never download/install ADB, Platform-Tools, APKs, or dependencies, and so native cards are used only when `native_card_compatible` is true. The ADB-missing question was reduced to four complete choices so WorkBuddy does not hide `安全退出` in “Other”.
4. Direct RC4 conversation installation was blocked by the WorkBuddy network proxy with `502 CONNECT tunnel failed`. A local-ZIP installation attempted through WorkBuddy's command runner stalled before deletion, so it was stopped.
5. The exact RC4 ZIP was then hash-verified and installed through the local terminal. The previous target was moved to Trash instead of being destroyed. `SKILL.md` showed version `0.3.0`, platform `workbuddy`, and the packaged harness passed `tv-helper --help`.
6. A new WorkBuddy task ran the read-only probe. The native card included the previous progress, missing-ADB blocker, official setup guidance, local-network result, four choices, and safe exit. Entering `continue` returned exit code 2 and the same `PRECHECK-WIFI-Q1`; choosing safe exit ended at `END-NO-ADB`.

WorkBuddy's native card visually numbers the fourth option as `4`, although its stable value remains `safe_exit` and the text fallback shortcut remains `0`. This is a host presentation limitation, not a workflow change.

## 豆包工作 live evidence

1. The old Android TV Apps Helper entry was disabled and deleted in the Skill manager. The Skill count decreased by one.
2. The RC4 Doubao ZIP was uploaded through `添加 → 上传技能`. Security detection completed and the new personal Skill became visible and enabled; the Skill count returned to its previous total.
3. The detail pane visibly contained the new contracts for automatic read-only precheck, `native_card_compatible`, no implicit dependency download, named app confirmation, the official Dangbei source, wallpaper reset risk, table-first results, and the final ADB/developer-mode reminder.
4. `在对话中试用` opened a fresh 本地电脑 task. The Skill initialized `doubao-work / local_computer / structured_form`, executed only the harness entry, and returned a status table plus one `PRECHECK-WIFI-Q1`. No ADB download, active scan, connection, or TV mutation occurred.
5. The reply `继续` was submitted as the exact value. The harness rejected it, kept `PRECHECK-WIFI-Q1`, displayed the invalid-answer row with ❌, and repeated all four choices. Replying `0` generated a final table stating that no TV operation ran and that no tool was downloaded or installed.

Doubao rendered the structured payload as a table plus numbered text menu rather than a clickable choice card. The information and validation contract remained complete.

## Codex live evidence

1. No existing personal Codex copy of this Skill was present, so there was nothing to delete. The hash-verified RC4 Codex ZIP was installed at `~/.codex/skills/android-tv-apps-helper` and passed `tv-helper --help`.
2. Computer-use automation is not permitted to control the Codex desktop app in this environment. The live host probe therefore used a fresh official Codex CLI process, not a simulated harness-only transcript.
3. The globally installed Codex CLI 0.39.0 could not use the account's current model and was left unchanged. An isolated temporary npm cache ran Codex CLI 0.154.0; no global software update was made.
4. The fresh Codex agent discovered `android-tv-apps-helper`, read the required references, initialized a `codex / local_computer / text_menu` session, and ran `workflow-entry`. Its workspace sandbox blocked the GitHub version check, so the table correctly marked update checking as temporarily unavailable and continued with the installed version.
5. The first response was the exact table-first `PRECHECK-WIFI-Q1` with four choices and no dependency download or mutation. A second fresh Codex agent continued the same persisted Skill session, submitted `继续`, received exit code 2, and rendered the same question with `attempts = 1` and no `action_required`.
6. A third fresh Codex agent continued the same session, submitted `0`, reached the terminal no-ADB path, and generated a final table stating that no television operation ran.

## Automated and reviewer evidence

- `106/106` Python unit tests pass after the RC4 fix and the final session-start-Home restore gap fix.
- All four platform ZIPs contain 30 files, no APK, and identical shared references, catalog, notices, and harness hashes.
- Extracted packages run their real `tv-helper init-session`; Doubao cloud-computer initialization fails before a session is created while local-computer initialization succeeds.
- Two independent user-view reviewers first exposed issues and then rechecked the corrected candidate. The novice review found short-text display-number drift, internal application IDs in user-facing plans, and state-transition gaps. Fixes preserved original displayed indices, mapped catalog IDs to names/versions, hid internal plan digests, locked pending questions/actions, completed safe-exit routing, and kept finish safety on the same question when ADB still responded. Targeted regressions and the full suite passed afterward.
- The final novice and adversarial reviews also caught evidence-reporting overstatement. The report was corrected to distinguish native-card numbering, local installation fallback, automated deep-flow coverage, live first-turn coverage, and physical-TV work that was not run.
- Their final pass caught a duplicate task/finish choice and an ADB executable identity gap. `TASK-Q1` now uses the neutral `进入任务收尾` route, while restore evidence is bound to the exact prechecked ADB path, target serial, HOME component, and verification argv. Both reviewers returned GREEN after the fixes.

## Scope not claimed

- No physical television was connected or modified during this release validation.
- APK installation, Home-key routing, wallpaper application, picture/sound/remote acceptance, and model-specific developer-mode shutdown were not re-executed on hardware.
- Claude live-client behavior remains unverified by explicit user decision; only its package and shared-core contracts passed.
