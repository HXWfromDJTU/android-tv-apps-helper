# Platform Validation — v0.3.1

Historical report. See platform-validation.md for the current release.

Date: 2026-09-16 (Asia/Shanghai). Public evidence omits account names, LAN addresses, TV serials and private local paths.

## Release verdict and boundaries

The native-choice fix is implemented and automated regression checks pass. WorkBuddy and Doubao rendered real native controls in the initial v0.3.1 candidate. Subsequent review added question-instance binding, platform schema limits, recommendation labels, context tables and removed tool allowlists. **Final WorkBuddy/Doubao GUI revalidation could not complete because Computer Use returned `Sky Computer Use native pipe startup failed` on two consecutive app connections. Initial-candidate GUI results are not final-package UI acceptance.**

| Platform | Final package installation | Final harness entrypoint | Live dialogue evidence | Final GUI status |
|---|---|---|---|---|
| Codex | Exact release ZIP installed in personal Skill directory; former copy moved to Trash | `tv-helper --help` passed | Codex CLI 0.154.0 invokes installed Skill; complete four-option question uses explicit schema-limit fallback | CLI validation; desktop GUI not claimed |
| WorkBuddy China 5.5.6 | Exact release ZIP installed in personal Skill directory; former copy moved to Trash | `tv-helper --help` passed | Initial candidate: real `AskUserQuestion` group and clicked safe exit | Final GUI blocked by Computer Use service failure |
| Doubao Work | Exact release ZIP placed in previously observed local user-Skill directory; former copy moved to Trash | `tv-helper --help` passed | Initial candidate: UI upload/replacement, security check, native radio group and safe exit | Final GUI and cloud-copy refresh not verified; local install does not prove uploaded Skill state |
| Claude Desktop / Code | ZIP build and shared-core checks only | Automated extracted-package checks | Not run by user decision | Not run |

No physical television was connected or modified. APK installation, Home, wallpaper, audiovisual/remote acceptance and ADB shutdown on hardware were not re-executed.

## Final artifacts

These exact ZIPs, not earlier candidates, are the release assets. Every ZIP contains 30 files, no APK, and identical shared harness/catalog/references. All four `SHA256SUMS` entries passed. All 30 installed files on each of Codex, WorkBuddy and Doubao were compared byte-for-byte against their final ZIP and matched.

| Platform | SHA-256 |
|---|---|
| WorkBuddy | `dcab3b58858104d7ca27bce51dadbdb06e226115bc97e685a50bca7f227228d8` |
| Doubao Work | `843043e850bd48a0298599086d7d33753f61ef863c8c6106d450c73c72c1a028` |
| Claude | `87fdf0a9b3f328a2644079fc2849db22afedd9d0931aeeb711d46b717b85d317` |
| Codex | `6b39c09441c9982c03c0659b95738da48005ba9a1b5fcd9995150806a3e96fc8` |

## Initial-candidate live reproduction

### WorkBuddy

1. Installed candidate after moving previous target recoverably to Trash; verified entrypoint.
2. Started a fresh task requesting only automatic passive read-only precheck, with no dependency download, scan, connection or TV mutation.
3. The Agent loaded the Skill, ran `workflow-entry --installed-version 0.3.1`, received `native_required`, and called `AskUserQuestion`.
4. Observed a real clickable group with four choices: install/specify ADB, same Wi-Fi, Wi-Fi not confirmed, safe exit. Its prompt included progress, actual results, missing-ADB blocker and official setup guidance.
5. Clicked safe exit. The Agent mapped its label to `safe_exit`, submitted `PRECHECK-WIFI-Q1`, reached `END-NO-ADB`, and generated a final report. No TV action ran.
6. This preceded final context-table and permission changes; it proves candidate native interaction, not final-package table-first UI.

Initial ZIP SHA-256: `27dc7618470ca1d1cbb6249b97778ce9b58c96265cbdf3227a52c331b4e6d95d`.

### Doubao Work

1. Uploaded candidate through installed Skills, replaced same-name entry, waited for security detection, refreshed, and observed enabled Skill.
2. Started a new **local-computer** task. The Agent loaded references, initialized the harness and ran passive precheck.
3. Observed a result table followed by a real native radio group. The card repeated progress, blocker, official Platform-Tools guidance and all four choices.
4. Accessibility radio-node clicks initially did not submit; clicking the visible option text succeeded. A coordinate attempt returned `noWindowsAvailable`; reconnecting restored control.
5. The Agent submitted `workflow-answer ... --question-id PRECHECK-WIFI-Q1 --value safe_exit`, generated `final-report.md`, and displayed a no-TV-operation result table.
6. Final package later replaced the observed local directory because Computer Use became unavailable. Final-package upload/security detection/new-task rendering remains unverified.

Initial ZIP SHA-256: `7a7cec139389fc6539a97e608f2970924b05396507eed1cf65bce6b76da58fad`.

### Codex

1. Ran official Codex CLI 0.154.0 in an isolated temporary workspace/npm cache; global CLI and npm ownership were unchanged.
2. Initial candidate started with `--surface auto`; noninteractive host did not expose `request_user_input`. Agent recorded `native_tool_not_exposed`, retained the question and showed the reason in its table.
3. After fixing Codex's 2–3-option limit, a subsequent run produced `question_not_native_compatible` for complete four-choice `PRECHECK-WIFI-Q1`, without sending invalid tool parameters or dropping safe exit.
4. Workspace sandbox blocked GitHub update lookup; the result showed an update warning. No dependency download, scan, connection or mutation occurred. Execution stopped awaiting an answer.
5. Pre-existing icon-path and unrelated MCP startup warnings were separate from Skill behavior. An early npm cache-permission failure was resolved with an isolated cache before Skill execution.
6. Repeated the precheck with the exact final Codex ZIP installed: CLI exited 0, displayed the result table and unchanged complete four-option question, including `question_not_native_compatible` and the update-network warning. It stopped without answering or touching a TV.

## Review and automated regression

Two independent user-view reviewers found and rechecked these fixes:

| Finding | Resolution | Evidence |
|---|---|---|
| Codex sent four options to a three-option tool | Platform-specific limits and complete per-question fallback | Native schema tests |
| Old failure callback could affect a new question | UUID per question instance; presentation digest binds instance/content/host/tool/payload | Cross-question and same-ID replay rejection |
| Temporary rendering error disabled later native questions | Current-question fallback only; accepted answer clears active failure and preserves audit context | Same-ID reentry test |
| Native choice omitted recommendation and separate table | Label/value aliases and `context_markdown`; context remains inside card | Rendering/mapping tests |
| All package tests used default Codex host | Extract each ZIP and initialize actual platform | Package tests |
| Tool allowlist might exclude Shell or native input | Omit `allowed-tools`; inherit host availability and permissions without extra Shell preapproval | Package frontmatter checks |

`116/116` automated tests passed on final source. Skill/plugin validation, compilation, JSON parsing and `git diff --check` passed. State checks prove rejection of stale callbacks; an Agent-supplied error string cannot independently prove a host rendered a card. Actual UI evidence is separated above. Both reviewers accepted the final code fixes. A further WorkBuddy connection retry before publication returned the same Computer Use startup failure.

## Known limitations

- Codex four-choice questions, menus beyond host option limits, disabled-option lists, short-text and unsupported multi-select use complete text fallback. Pagination was not added. Next compatible question still prefers native input.
- Tool availability depends on host mode. A Skill cannot enable missing components with markup.
- Final WorkBuddy/Doubao GUI acceptance must be rerun after Computer Use recovers. This is not a claim of final three-platform GUI acceptance.
- Historical evidence remains in [v0.3.0 report](platform-validation-v0.3.0.md).
