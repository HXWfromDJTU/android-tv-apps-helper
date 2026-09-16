# Interaction Contract — Strong Choice

## Invariants

Claude, Codex, WorkBuddy and 豆包工作 share the workflow, `pending_question`, stable option values, approvals and evidence labels. Codex/Claude Desktop/WorkBuddy/Doubao use the real HTML controller described in html-interaction.md; Claude Code and legacy checkpoints use host-native `structured_form`. A numbered-text menu is unsupported, even after an error.

## HTML decisions

The same page is an embedded MCP App when the host supports it, or an authenticated loopback browser page. Both submit exact option values bound to the current question/presentation. The page shows context as a table above the short question, full application checkboxes and an always-visible confirmation footer, then optional supplemental input. The confirmation goes to named download confirmation, never directly executes installs. Read `tv_ui_state`/`wait-ui` after clicks; never submit them again through native CLI. No page/progress notification constitutes approval.

The remaining native sections apply to `native_required`, not `html_required`; do not attempt to call an absent native tool for an HTML session.

Only render questions from `workflow-entry`, `workflow-native-answer`, `workflow-discover` and `workflow-action-result`. Do not invent questions, edit session JSON, bypass with legacy `workflow-answer`, or advance without an accepted answer. A pending action waits for evidence.

## Required reply order

1. Display `presentation.context_markdown` in visible conversation: table with ✅ completed, ❌ attempted but failed, ⚠️ uncertain/risky, ⏳ pending and ⏭️ unavailable/skipped, then blocker and guidance.
2. Call `presentation.tool_name` with exact `tool_input`. The component contains only a short question and its options. Do not append context to the title.
3. The host's normal supplemental/Other input appears after the options; never replace the choices with a request to type numbers. Do not invent an Other option or fake HTML UI.
4. Submit the actual returned label/value through `workflow-native-answer` with the current `question_id` and `presentation_id`. For an actual multi-selection, use `--values-json '["label A","label B"]'` rather than joining display labels.

Codex capability selection follows platforms.md, including `request_user_input_async`. When `response_delivery=async_user_message`, successful tool invocation only delivers the question: yield and wait, preserving its question/presentation IDs. No default choice is submitted automatically. Do not attach late replies to a newer token.

A question is `required`. Closing a card, a preselected recommendation, an attachment, “继续”, or unrelated supplemental prose is not consent. On exit code 2, show the returned error with the context and invoke the returned native component again; do not execute later actions.

## Pagination and selection

The harness fits every page to the platform limit: Codex 3 choices, AskUserQuestion hosts 4. `native_card_compatible` is legacy raw-count metadata, not permission to downgrade. Use the actual `presentation`.

“更多选项” cycles pages. All enabled choices remain reachable; `safe_exit` stays visible on every page when present in the canonical question. Finish-routing questions retain their canonical exit instead of inventing a duplicate; never map `safe_exit` to a generic Other field. Unavailable choices are explained in the context table and cannot be submitted.

Compatible small multi-choice questions use native multi-select. Larger lists or single-choice-only hosts use native add/remove choices, retained selections across pages, then “完成选择”. Toggling, navigating and completing selection do not authorize downloading. The next workflow question confirms selected application names and versions; installation still requires separate approval.

## Input after choice

For `short_text`, first display a native “填写信息” choice alongside return/exit. Only after that choice is accepted does the harness set `accepts_free_input=true`. Invoke its native component again with return/exit choices and use the host's supplemental input field for the required prefix/value (for example `IP: …` or `ADB: …`). The input must still pass validation; invalid values keep this stage open. A host without that input field must report a rendering failure, not invent a widget or silently switch to chat input.

For ordinary choice questions, supplemental input may clarify the issue but cannot advance the workflow unless it exactly matches a visible option. Always present choices again.

## Native failures

`native_required` always means call the real tool, not Markdown choices. After an observed failure, call `record-surface-failure` with current question ID, presentation ID, tool name, reason and detail. No simulated calls or fabricated failures.

- A call/render error permits one native retry for the same question. The returned token changes; use it.
- A second failure, or a tool not exposed by the current host mode, returns `native_blocked`: display the status table, preserve the pending question and stop operations. No numbered-text fallback.
- After the host component is restored, `resume-native <session> --question-id <current-id>` produces a fresh native presentation. Do not repeatedly reset it to evade the retry limit.

A Skill cannot create a missing host tool. This blocked condition is not successful interaction. Legacy `text_menu` initialization is accepted for checkpoint compatibility but presentation still requires native controls.

## Approval and question lock

The current presentation binds its question instance, page, selected items and tool payload. Old-page callbacks are rejected. Page navigation/input opening is UI-only, never a workflow answer or mutation approval. `explicit_consent` requires the exact confirmation option after displaying action and impact. No inferred approvals.

Until a valid answer is accepted, preserve the question and options, explain any invalidity, and render the current native component. A failure response is still a decision point with choices, not an invitation to type an unstructured answer.
