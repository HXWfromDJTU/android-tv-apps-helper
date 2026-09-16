# Platform Adapters

The host adapter only locates the Skill, selects a supported UI surface, and supplies local execution. It never changes the canonical workflow, `pending_question`, ADB target binding, approval plan, APK policy, or evidence levels.

## Desktop HTML routing (current)

Codex, Claude Desktop, WorkBuddy and 豆包工作 initialize `--surface html`; read [html-interaction.md](html-interaction.md). Use the installed MCP App for embedded choices; if unavailable, launch the authenticated local browser page and keep the Agent's wait loop active. A standalone Skill ZIP does not automatically register an MCP server. Never claim embedded rendering from tool availability alone.

The guidance below for native controls applies only to Claude Code or existing native checkpoints. New desktop sessions use HTML. For an existing desktop native question, `resume-html <session> --question-id <current-id>` preserves the workflow/selection state and invalidates the old presentation token. Do not initialize over an existing checkpoint.

WorkBuddy 5.5.6 and Doubao Work 2.29.10 local client resources contain MCP App HTML/bridge implementations. WorkBuddy's official Buddy App documentation also describes MCP Apps integration. These are implementation evidence, not proof of a particular account/version's live render and callback. Test the real client; keep that acceptance status separate.

## Claude Desktop / Code

- Claude Code discovers a project Skill in `.claude/skills/android-tv-apps-helper/` or a personal Skill in `~/.claude/skills/android-tv-apps-helper/`.
- Claude Desktop or claude.ai imports the Claude ZIP through its custom Skills interface when the account supports custom Skills and code execution.
- Claude Code resolves `${CLAUDE_SKILL_DIR}/scripts/tv-helper` and initializes `--host-platform claude --surface auto --execution-context local_computer`. Desktop uses an actual local installed path with `--host-platform claude-desktop --surface html`; do not assume the Code-only environment variable exists in Desktop.
- If code execution cannot reach the user's LAN, stop before S0.
- Claude Code must call `AskUserQuestion` whenever `presentation.mode` is `native_required`. Submit one question only, preserve the supplied labels/descriptions, and map the selected label through `answer_value_map`.

## Codex (legacy native checkpoints)

- Use the repository plugin/marketplace or the canonical project Skill.
- Resolve the harness relative to the plugin Skill and initialize with `--host-platform codex --execution-context local_computer`.
- Inspect the tools actually exposed to this conversation and their mode restrictions. Prefer `request_user_input_async` when available, including in Default mode; initialize with `--native-tool request_user_input_async`. Its schema is `{"questions":[{"title":"short question","options":["label A","label B"]}]}`. Do not pass sync-only fields (`id`, `header`, `question`, object-valued options). Call the real tool, including its namespace when the host exposes one.
- If async is absent, use `request_user_input` only if exposed AND permitted in the current mode; initialize with `--native-tool request_user_input`. Never assume every Codex build exposes async, or that Default universally lacks native UI. A Skill cannot enable a missing host tool or switch operating modes itself.
- For `response_delivery=async_user_message`, the call acknowledges delivery immediately. Save the current question/presentation IDs, yield and await the actual user message. Submit only the explicit selected label (or valid input-stage content) with those IDs. Unanswered/preselected/closed components, unrelated messages and acknowledgements do not advance the workflow. A late answer to an older presentation must not be relabeled with the new token.
- Async lacks per-option description fields. Its context includes a short explanation table for visible choices; display it without moving the text into the title. This table is not a substitute for calling the native component.
- To recover a v0.3.3 checkpoint blocked on the sync tool when async is actually callable: `resume-native <session> --question-id <current-id> --native-tool request_user_input_async`. This preserves the question, precheck, selection state and approvals but issues a new presentation token. Use this only after finding the alternate available tool, not to reset retries indefinitely.
- Call the returned `presentation.tool_name` with its exact `tool_input` for every decision. Before declaring native UI unavailable, check BOTH Codex tools. If neither is callable, record `native_tool_not_exposed` with exact current identities, show the blocked table and pause. Explain the actual missing capability; suggest Plan only when its synchronous tool is known to be available. Never substitute numbered text choices.
- A repository/plugin install must be removed and reinstalled from the v0.4.0-rc.1 candidate for live acceptance; package presence alone is not invocation evidence.

## WorkBuddy

- Install the WorkBuddy ZIP from its GitHub Release URL in an Agent conversation; use manual Skill upload only when direct installation is unavailable.
- Locate the installed Skill root, run `python3 scripts/tv-helper`, and initialize with `--host-platform workbuddy --surface html --execution-context local_computer`.
- Call `AskUserQuestion` with the exact returned `presentation.tool_input` whenever `presentation.mode` is `native_required`. A prose list is a failure, not an equivalent rendering.
- Treat the installed-Skill list and a new-conversation invocation as evidence; a download message alone is not installation evidence.
- Conversation installation is preferred when supported. If the Agent only downloads the ZIP, use manual upload and keep the step marked incomplete until the installed list shows version `0.4.0-rc.1`.

## 豆包工作

- Install the Doubao Work ZIP from its GitHub Release URL in an Agent conversation; use 技能管理中的本地导入 as fallback.
- Start a 本地电脑 task. Never use 云电脑 for ADB because it cannot safely reach the Android TV on the user's local network.
- Locate the installed Skill root, run `python3 scripts/tv-helper`, and initialize with `--host-platform doubao-work --surface html --execution-context local_computer`.
- Call `AskUserQuestion` with exact `presentation.tool_input` for `native_required`. Record observed errors with the returned question/presentation/tool identity; use the single native retry or pause at `native_blocked`, never text choices.
- Invoke from `/`, 更多技能, or an explicit request to use Android TV Apps Helper. Verify the Skill is visible before claiming installation.
- Use a new local-computer conversation after reinstall so cached old instructions are not mistaken for the new version.

## Equivalent first business turn

After update handling and automatic passive precheck, every platform starts at `PRECHECK-WIFI-Q1`. Display actual results in a status table, then blocker and guidance before the choices. HTML displays the same context above a short question; native cards keep context in conversation. Never ask permission to begin precheck. “继续” alone never advances. All platforms share `pending_question` and `local_computer` requirements.

## Rendering and validation

Use `record-surface-failure` for each observed native-tool failure; its response determines retry versus pause.

`native_required` means show `context_markdown` in visible conversation then call the named tool with exact `tool_input`. Keep results, blockers, risks and guidance outside the short title/question. Excess choices are paginated natively; input and large multi-select use the harness's native stages. Submit callbacks with `workflow-native-answer` and the current presentation ID. The supplemental input belongs after the choices, using the host's built-in field. If the host lacks the required tool or input field, report that limitation and pause; never fake a UI or request numbered chat answers.

For every live host, separately record: old version visible, removal visible, candidate installed and version visible, explicit invocation, automatic precheck, invalid-answer lock, app-selection/named confirmation, finish-safety rendering, and any unavailable local-computer or native-control capability. Redact account names, SSID, IP, and serial from public evidence.
