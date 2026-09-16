# Interaction Contract

## Cross-platform invariants

Claude, Codex, WorkBuddy, and 豆包工作 use the same workflow revision, `pending_question` data, stable option values, mutation approvals, and evidence labels. Host-native controls may change presentation only. They cannot merge questions, omit options, preselect the recommendation, infer consent, or advance state without a harness-accepted answer.

The model must render questions produced by `workflow-entry`, `workflow-answer`, and `workflow-action-result`. It must not use `set-question` to invent a prompt or next state. A pending question cannot be overwritten, and a pending action cannot advance until evidence is recorded.

## Question lock

Every decision creates one `pending_question` before it is rendered. It contains `question_id`, `state_id`, `kind`, `prompt`, stable options, `required: true`, `attempts`, previous result, progress, blocker, remediation guidance, evidence, table rows, and optional visual/attachment data. The harness also emits `component_prompt` and `component_options`. Native hosts must use those two fields; `component_prompt` is deliberately self-contained so a modal cannot hide the user's blocker in surrounding conversation.

Do not clear `pending_question` or enter the next state until the harness accepts the answer. On an invalid answer:

1. Keep the current state.
2. Execute no later command.
3. Explain the invalidity in one sentence.
4. Render the same `question_id` and options again.
5. Wait.

Answers such as “好的”, “继续”, “随便”, or “你决定” are invalid while a question is pending unless that exact phrase is a displayed option value. An answer to an older question is invalid.

## Surface selection

Set `interaction_surface` once per session:

- `structured_form`: a supported host-native required form, single-choice card, or button surface exists.
- `text_menu`: no supported UI exists, the UI call fails, the result cannot render, or a required submission value is missing.

UI failure changes only the surface. Preserve the question ID, options, and state. Never emit raw `<widget>`, `<choices>`, `<visual-option>`, or fake HTML buttons. Do not call another product such as ChatCut merely to borrow its UI.

For `structured_form`, use stable option values with localized labels and descriptions. Use a native card only when `native_card_compatible` is true. Otherwise render the complete text menu: never omit choices, never preselect the recommendation, and never map `safe_exit` to a generic Other field. Keep the label-to-value map when a host returns display text. Mark blocking inputs `required`. For `explicit_consent`, use one initially unselected confirmation control containing the full action and impact; attachments and other fields are not consent.

## Question types

- `single_choice`: exactly one number, stable value, or unambiguous full label.
- `multi_choice`: only when declared; accept a list such as `1,3,5`.
- `short_text`: require a visible prefix and format, such as `IP: 192.168.31.170` or `路径: /absolute/app.apk`.
- `explicit_consent`: exact confirmation value only; never infer it from “continue”.

Every blocking question includes `safe_exit` (shown as `0. 安全退出`) unless it is already a dedicated finish-routing question. `TASK-Q1` uses the explicit `finish_options` route, and `FINISH-CHOICE-Q1` uses `finish_keep`; adding generic exits to either would duplicate the same outcome. Include `back` when returning is meaningful.

## Reply shape

Each interactive Agent reply contains, in order:

1. A three-to-six-row Markdown status table derived from evidence.
2. The current blocker or risk.
3. Actionable guidance for that blocker.
4. Exactly one question.
5. Options with impact; mark one recommendation when useful but never preselect it.
6. Exact accepted-answer format.

For a native modal/card, keep items 1–5 inside the component. If the host cannot place a table in the component, put it immediately above and repeat the most important blocker inside the component. Never leave the context only in hidden chain-of-thought or surrounding prose.

The Agent may run already authorized work until the next decision, but every new conversational turn must end with a question and options. If the user asks a side question, answer briefly and then render the still-pending question again.

## Text fallback example

```text
| 状态 | 项目 | 结果 | 依据 |
| --- | --- | --- | --- |
| ✅ | 目标候选 | 小米电视 MiTV-ASTP0 | ADB 只读属性 |
| ⚠️ | 用户确认 | 等待确认 | — |

问题 TARGET-Q1：这是要操作的电视吗？

1. 确认这台电视（推荐）——后续命令只发送到此设备
2. 换一台——返回设备发现
0. 安全退出——停止尚未执行的工作

请明确回复：1、2 或 0。
```

## Status and selection contract

The harness maps evidence to symbols: ✅ completed, ❌ attempted and incomplete after allowed recovery, ⚠️ partial/risky/user verification, ⏳ pending, and ⏭️ skipped. A successful command cannot substitute for on-site picture, sound, or remote-control confirmation.

Use native multi-select when available. Text fallback accepts Chinese enumeration commas, Chinese/English commas, or whitespace and displays `1、2、3、4` as the example. Duplicate, unknown, disabled, or `0`-mixed selections are invalid. After selection, the next question lists application names and versions; confirmation starts download only, never installation.
