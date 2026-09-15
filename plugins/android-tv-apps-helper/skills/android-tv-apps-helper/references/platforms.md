# Platform Adapters

The host adapter only locates the Skill, selects a supported UI surface, and supplies local execution. It never changes the canonical workflow, `pending_question`, ADB target binding, approval plan, APK policy, or evidence levels.

## Claude Desktop / Code

- Claude Code discovers a project Skill in `.claude/skills/android-tv-apps-helper/` or a personal Skill in `~/.claude/skills/android-tv-apps-helper/`.
- Claude Desktop or claude.ai imports the Claude ZIP through its custom Skills interface when the account supports custom Skills and code execution.
- Resolve the harness with `${CLAUDE_SKILL_DIR}/scripts/tv-helper` and initialize with `--host-platform claude --execution-context local_computer`.
- If code execution cannot reach the user's LAN, stop before S0.

## Codex

- Use the repository plugin/marketplace or the canonical project Skill.
- Resolve the harness relative to the plugin Skill and initialize with `--host-platform codex --execution-context local_computer`.
- Prefer a native required-choice surface when one is actually available; otherwise use `text_menu`.
- A repository/plugin install must be removed and reinstalled from the v0.3.0 candidate for live acceptance; package presence alone is not invocation evidence.

## WorkBuddy

- Install the WorkBuddy ZIP from its GitHub Release URL in an Agent conversation; use manual Skill upload only when direct installation is unavailable.
- Locate the installed Skill root, run `python3 scripts/tv-helper`, and initialize with `--host-platform workbuddy --execution-context local_computer`.
- Treat the installed-Skill list and a new-conversation invocation as evidence; a download message alone is not installation evidence.
- Conversation installation is preferred when supported. If the Agent only downloads the ZIP, use manual upload and keep the step marked incomplete until the installed list shows version `0.3.0`.

## 豆包工作

- Install the Doubao Work ZIP from its GitHub Release URL in an Agent conversation; use 技能管理中的本地导入 as fallback.
- Start a 本地电脑 task. Never use 云电脑 for ADB because it cannot safely reach the Android TV on the user's local network.
- Locate the installed Skill root, run `python3 scripts/tv-helper`, and initialize with `--host-platform doubao-work --execution-context local_computer`.
- Invoke from `/`, 更多技能, or an explicit request to use Android TV Apps Helper. Verify the Skill is visible before claiming installation.
- Use a new local-computer conversation after reinstall so cached old instructions are not mistaken for the new version.

## Equivalent first business turn

After update handling and automatic passive precheck, every platform starts at `PRECHECK-WIFI-Q1`. Its three-to-six-row table contains the actual precheck results, its blocker is inside the component, and it asks whether computer and TV use the same Wi-Fi. It never asks permission to begin precheck. An ambiguous answer such as “继续” redisplays the same question, context, and options and executes no later command.

## Rendering and validation

Prefer a native required card and native multi-select only when the host really supports them. If a native component cannot contain a Markdown table, render the table immediately above it and repeat the key blocker in the prompt. Record that degradation in `docs/platform-validation.md`.

For every live host, separately record: old version visible, removal visible, candidate installed and version visible, explicit invocation, automatic precheck, invalid-answer lock, app-selection/named confirmation, finish-safety rendering, and any unavailable local-computer or native-control capability. Redact account names, SSID, IP, and serial from public evidence.
