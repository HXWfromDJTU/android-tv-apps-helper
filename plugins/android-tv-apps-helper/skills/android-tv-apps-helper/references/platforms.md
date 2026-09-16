# Platform Adapters

The host adapter only locates the Skill, selects a supported UI surface, and supplies local execution. It never changes the canonical workflow, `pending_question`, ADB target binding, approval plan, APK policy, or evidence levels.

## Claude Desktop / Code

- Claude Code discovers a project Skill in `.claude/skills/android-tv-apps-helper/` or a personal Skill in `~/.claude/skills/android-tv-apps-helper/`.
- Claude Desktop or claude.ai imports the Claude ZIP through its custom Skills interface when the account supports custom Skills and code execution.
- Resolve the harness with `${CLAUDE_SKILL_DIR}/scripts/tv-helper` and initialize with `--host-platform claude --execution-context local_computer`.
- If code execution cannot reach the user's LAN, stop before S0.
- Claude Code must call `AskUserQuestion` whenever `presentation.mode` is `native_required`. Submit one question only, preserve the supplied labels/descriptions, and map the selected label through `answer_value_map`.

## Codex

- Use the repository plugin/marketplace or the canonical project Skill.
- Resolve the harness relative to the plugin Skill and initialize with `--host-platform codex --execution-context local_computer`.
- Call `request_user_input` whenever `presentation.mode` is `native_required` and the tool is exposed in the current mode. If it is not exposed, run `record-surface-failure` with the returned `question_id`, `presentation_id`, `tool_name`, reason `native_tool_not_exposed`, and the observed limitation before showing text.
- A repository/plugin install must be removed and reinstalled from the v0.3.2 candidate for live acceptance; package presence alone is not invocation evidence.

## WorkBuddy

- Install the WorkBuddy ZIP from its GitHub Release URL in an Agent conversation; use manual Skill upload only when direct installation is unavailable.
- Locate the installed Skill root, run `python3 scripts/tv-helper`, and initialize with `--host-platform workbuddy --execution-context local_computer`.
- Call `AskUserQuestion` with the exact returned `presentation.tool_input` whenever `presentation.mode` is `native_required`. A prose list is a failure, not an equivalent rendering.
- Treat the installed-Skill list and a new-conversation invocation as evidence; a download message alone is not installation evidence.
- Conversation installation is preferred when supported. If the Agent only downloads the ZIP, use manual upload and keep the step marked incomplete until the installed list shows version `0.3.2`.

## 豆包工作

- Install the Doubao Work ZIP from its GitHub Release URL in an Agent conversation; use 技能管理中的本地导入 as fallback.
- Start a 本地电脑 task. Never use 云电脑 for ADB because it cannot safely reach the Android TV on the user's local network.
- Locate the installed Skill root, run `python3 scripts/tv-helper`, and initialize with `--host-platform doubao-work --execution-context local_computer`.
- Call `AskUserQuestion` with the exact returned `presentation.tool_input` whenever that tool is exposed and `presentation.mode` is `native_required`. If the host rejects the call, record the concrete error together with the returned `question_id`, `presentation_id`, and `tool_name` before falling back.
- Invoke from `/`, 更多技能, or an explicit request to use Android TV Apps Helper. Verify the Skill is visible before claiming installation.
- Use a new local-computer conversation after reinstall so cached old instructions are not mistaken for the new version.

## Equivalent first business turn

After update handling and automatic passive precheck, every platform starts at `PRECHECK-WIFI-Q1`. Display its actual results in a visible three-to-six-row status table, then blocker and guidance, immediately before the native component. The component asks only whether computer and TV use the same Wi-Fi, with the supplied choices. It never asks permission to begin precheck. An ambiguous answer such as “继续” redisplays the same context, short question and options and executes no later command.

## Rendering and validation

`native_required` means the Agent must show `context_markdown` in visible conversation and then call the named tool with exact `tool_input`; it may not substitute a Markdown choices list. Keep all results, blockers, risks and guidance outside the component title/question. This table-before-short-card layout is intentional on all platforms, not a fallback. Text choices are permitted only for `text_fallback`, after question incompatibility or a recorded real host failure.

For every live host, separately record: old version visible, removal visible, candidate installed and version visible, explicit invocation, automatic precheck, invalid-answer lock, app-selection/named confirmation, finish-safety rendering, and any unavailable local-computer or native-control capability. Redact account names, SSID, IP, and serial from public evidence.
