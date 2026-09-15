# Four-Platform Skill Parity Design

## Goal

Ship Android TV Apps Helper from one canonical workflow to Claude Desktop/Code, Codex, Tencent WorkBuddy, and Doubao Work without allowing host-specific packaging or UI differences to change the core state machine, approval boundaries, APK policy, or evidence claims.

## Architecture

The existing Codex skill remains the canonical source. A deterministic platform packager copies the canonical `SKILL.md`, references, harness, catalog, and notices into self-contained ZIP artifacts. Host profiles may change frontmatter and script path syntax only; they may not fork workflow content.

The supported host families are:

| Platform | Installation | Invocation | Runtime boundary |
|---|---|---|---|
| Codex | repository marketplace/plugin | `$android-tv-apps-helper` or intent discovery | local shell |
| WorkBuddy | Agent installs Release ZIP; manual upload fallback | explicit Skill selection or intent discovery | local computer task |
| Doubao Work | Agent installs Release ZIP; local import fallback | `/`, “更多技能”, or intent discovery | local computer task only |
| Claude Desktop/Code | Desktop ZIP upload; Code `.claude/skills` or `~/.claude/skills` | `/android-tv-apps-helper` or intent discovery | local code execution |

Doubao Work cloud-computer sessions cannot reach an Android TV on the user's LAN and must stop before ADB discovery. A host with no native structured form uses the exact numbered text menu with the same question ID and stable option values.

## Package Contract

`scripts/build_platform_packages.py` accepts `--platform`, `--output`, and optional `--version`. Supported package profiles are `workbuddy`, `doubao-work`, and `claude`. Each ZIP has one top-level `android-tv-apps-helper/` directory and contains no APK files.

All artifacts contain byte-identical workflow, interaction, ADB, APK policy, catalog, notices, and Python harness files. Generated `SKILL.md` bodies are derived from the canonical entrypoint. The only permitted differences are frontmatter fields and the command used to resolve the bundled harness:

- WorkBuddy and Doubao Work: `python3 scripts/tv-helper` after locating the installed Skill root.
- Claude: `python3 "${CLAUDE_SKILL_DIR}/scripts/tv-helper"`.
- Codex: repository-relative `../../scripts/tv-helper` in the canonical plugin Skill.

## Host Preflight

Before S0, the Skill records `host_platform`, `execution_context`, `interaction_surface`, `skill_root`, `python_command`, and `adb_path`. It must prove that the session can execute local commands and access the local network. Failure displays a bounded result and asks one question offering retry, switch to local mode, or exit. It must not pretend a downloaded or imported package has run successfully.

After host preflight, every platform uses the same S0-S11 state graph and the same persisted `pending_question` contract.

## Verification Model

Each platform has five independent evidence levels:

1. artifact built;
2. Skill installed and visible in the host;
3. Skill explicitly loaded in a new conversation;
4. first reply matches S0 and refuses ambiguous input without advancing;
5. physical Android TV workflow accepted.

This release targets level 4 for Codex, WorkBuddy, and Doubao Work when their clients are available. Claude receives automated artifact validation only and remains explicitly unverified in a live host.

## Release

Version `0.3.0` publishes:

- `android-tv-apps-helper-workbuddy-v0.3.0.zip`
- `android-tv-apps-helper-doubao-work-v0.3.0.zip`
- `android-tv-apps-helper-claude-v0.3.0.zip`
- `SHA256SUMS`
- a machine-readable platform compatibility report

The README must distinguish tested, automated-only, and unverified states. Clash Meta remains official-release-only and no new third-party APK rights are inferred.
