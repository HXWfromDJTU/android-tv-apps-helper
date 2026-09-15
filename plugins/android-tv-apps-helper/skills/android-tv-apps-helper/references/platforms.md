# Platform Adapters

The host adapter only locates the Skill, selects a supported UI surface, and supplies local execution. It never changes the S0–S11 workflow, `pending_question`, ADB target binding, approval plan, APK policy, or evidence levels.

## Claude Desktop / Code

- Claude Code discovers a project Skill in `.claude/skills/android-tv-apps-helper/` or a personal Skill in `~/.claude/skills/android-tv-apps-helper/`.
- Claude Desktop or claude.ai imports the Claude ZIP through its custom Skills interface when the account supports custom Skills and code execution.
- Resolve the harness with `${CLAUDE_SKILL_DIR}/scripts/tv-helper` and initialize with `--host-platform claude --execution-context local_computer`.
- If code execution cannot reach the user's LAN, stop before S0.

## Codex

- Use the repository plugin/marketplace or the canonical project Skill.
- Resolve the harness relative to the plugin Skill and initialize with `--host-platform codex --execution-context local_computer`.
- Prefer a native required-choice surface when one is actually available; otherwise use `text_menu`.

## WorkBuddy

- Install the WorkBuddy ZIP from its GitHub Release URL in an Agent conversation; use manual Skill upload only when direct installation is unavailable.
- Locate the installed Skill root, run `python3 scripts/tv-helper`, and initialize with `--host-platform workbuddy --execution-context local_computer`.
- Treat the installed-Skill list and a new-conversation invocation as evidence; a download message alone is not installation evidence.

## 豆包工作

- Install the Doubao Work ZIP from its GitHub Release URL in an Agent conversation; use 技能管理中的本地导入 as fallback.
- Start a 本地电脑 task. Never use 云电脑 for ADB because it cannot safely reach the Android TV on the user's local network.
- Locate the installed Skill root, run `python3 scripts/tv-helper`, and initialize with `--host-platform doubao-work --execution-context local_computer`.
- Invoke from `/`, 更多技能, or an explicit request to use Android TV Apps Helper. Verify the Skill is visible before claiming installation.

## Equivalent first turn

After successful host preflight, every platform starts at S0-Q1. The reply briefly states the read-only versus mutation boundary, asks one required question, offers `1. 开始只读检查`, `2. 查看检查范围`, and `0. 安全退出`, then accepts only `1`, `2`, or `0`. An ambiguous answer such as “继续” redisplays S0-Q1 unchanged and executes no ADB command.
