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
| Codex | ✅ | ⏭️ No previous Codex copy existed | ✅ RC4 ZIP installed to the personal Skill directory | ✅ Fresh Codex CLI 0.154.0 resolved v0.3.0 | ✅ Table-first `PRECHECK-WIFI-Q1`; `继续` rejected with attempts = 1; same options retained | ✅ Live Codex submitted `0`; final report recorded no TV operation | ⏭️ App selection, Home, wallpaper, ADB shutdown and physical TV not run |
| WorkBuddy 中国大陆版 | ✅ | ✅ Existing target moved recoverably to Trash | ⚠️ RC4 GitHub conversation install hit 502 and the WorkBuddy command path was stopped; exact ZIP installed through a hash-verified local filesystem fallback | ✅ New WorkBuddy task invoked the installed Skill | ✅ Native required card contained progress, blocker, guide, and four non-duplicated choices; `continue` rejected and the same card returned | ⚠️ Live native card displayed it as row 4, but submitted stable `safe_exit` successfully | ⏭️ App selection, Home, wallpaper, ADB shutdown and physical TV not run |
| 豆包工作 | ✅ | ✅ Previous Skill deleted in the client | ✅ RC4 ZIP uploaded; security detection completed; Skill visible | ✅ New 本地电脑 task invoked the installed Skill | ✅ Table-first `PRECHECK-WIFI-Q1`; `继续` rejected by the harness and the same four choices returned | ✅ Live text fallback submitted `0`; final report says no connection, scan, mutation, or tool download | ⏭️ App selection, Home, wallpaper, ADB shutdown and physical TV not run |
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
