# HTML click interaction

## Routing

Codex, Claude Desktop, WorkBuddy and Doubao Work use `--surface html` with host IDs `codex`, `claude-desktop`, `workbuddy`, `doubao-work`. Claude Code remains `--surface auto --host-platform claude`. Never infer UI support just because MCP tools connect or an HTML file is previewable.

Claude Desktop and Code share the `claude` download artifact/platform metadata; `claude-desktop` is a session host ID, not a separate ZIP name. Optional MCP dependency installation belongs to explicitly authorized Skill setup, not an implicit TV workflow operation.

Initialize and run `workflow-entry` as described in SKILL.md before showing UI. The first page renders actual precheck evidence, not a new question asking whether to precheck. A legacy desktop checkpoint can be migrated without losing its question, selections or approvals:

```sh
python3 scripts/tv-helper resume-html <session.json> --question-id <current-question-id>
```

Commands here are relative to a standalone Skill root. Repository plugins use `../../scripts/tv-helper` relative to their Skill directory. Claude Desktop does not always expose `CLAUDE_SKILL_DIR`; resolve the actual installed local path, never a cloud code-execution path.

## Embedded MCP App (preferred when installed and rendered)

1. Inspect actual available tools. Call `tv_ui_show(session_path=<absolute existing session.json>)` from this plugin's MCP server. The path must lie under the configured `--session-root`. Use the actual exposed namespace.
2. Show the returned `presentation.context_markdown` in the conversation. The HTML card separately shows a progress table above the short question, all options, supplemental input last, and a fixed explicit submit button. The tool result itself is not proof that the host rendered a card.
3. Wait for real user clicks with `tv_ui_wait(session_key, after=<revision>, timeout=25)`. `changed=false` means still unanswered; keep the same session and wait again. Never infer an answer from elapsed time, page creation, default recommendations, closure or a generic “continue”. Use bounded waits so user stop messages remain effective.
4. The page saves accepted choices to the harness; `ui/message` asks the host to continue. A notification alone is not approval: read `tv_ui_state`. Do not resubmit choices with `workflow-native-answer`.
5. The MCP server serves only UI, state and answers; it never downloads, installs or executes ADB. Execute only the current `action_required` with available local tools and return real evidence through the normal harness commands. Without local execution, explain the missing capability and stop device work. The page polls state through a read-only resource and shows the resulting question.

If the page does not render or a UI callback is denied, do not forge success or change mode to Plan merely for the question UI. `tv_ui_browser(session_key)` returns a private loopback URL for the same question. Open that URL with the host's supported browser/open-link mechanism and continue waiting. If policy prevents both channels, preserve the question and report the real blocker; no numbered chat menu.

## Local browser (works without MCP installation)

Start this as a persistent/yielding local process and retain its process handle:

```sh
python3 scripts/tv-helper serve-ui <session.json> --open
```

Its first stdout line contains `url` and `revision`. If automatic opening fails, show a clickable link to that exact local URL. Do not copy it into public reports: its fragment contains a session credential. Keep the server alive while using the page. In another local tool invocation:

```sh
python3 scripts/tv-helper wait-ui <session.json> --after <last-revision> --timeout 25
```

The command returns authoritative state on change or timeout. Reissue while unanswered, retaining the latest revision. A normal browser cannot independently wake an idle Agent after its turn ends: keep the waiting tool active rather than telling the user to type “continue”. If the host cannot retain a background process or wait, report that limitation instead of claiming the loop is working.

A pending action pauses the UI until the Agent submits actual evidence. Never treat a UI-only input-opening step as operation approval. Stop the owned server process after terminal completion; do not kill unrelated processes. A server restart rotates its private URL but preserves the stored question. Do not start two independent Agent writers on the same session.

## Decisions

- Full application list with checkboxes; “确认所选应用，进入安装流程” remains visible in the fixed footer. It advances to named download confirmation, not immediate installation.
- No automatic selections or submissions. Reload preserves the current question and draft checkbox choices; drafts are not approvals.
- Short input requires clicking the fill-information option first. Then fill the input below the options and explicitly select its submit option. Supplementary notes are retained with the answer but cannot authorize actions.
- Invalid/stale/repeated requests show the error and current choices. Pending-action screens cannot accept new answers.
- Browser state and MCP UI use the same session file; a real-host click test is required before claiming a platform passed. SDK/protocol and test iframe checks are not host acceptance.

## Optional MCP setup (maintainer / installation Agent)

Embedded UI requires an installed local MCP server, not just a Skill ZIP. With the user's installation authorization, create an isolated Python 3.11+ venv and install `scripts/mcp-requirements.txt`; do not change a global Python environment. Register a stdio server using absolute paths:

```json
{
  "mcpServers": {
    "android-tv-ui": {
      "command": "/absolute/skill/.venv/bin/python",
      "args": ["/absolute/skill/scripts/tv-helper", "mcp-ui", "--session-root", "/absolute/tv-session-directory"]
    }
  }
}
```

The allowed session directory must already exist. Preserve all unrelated MCP configuration and require the host's normal trust/permission flow. Never enable blanket approval/bypass modes. After registration/restart, verify real tools and rendering; stale conversations may not discover new tools. Browser mode needs only Python standard library and remains available without this setup.
