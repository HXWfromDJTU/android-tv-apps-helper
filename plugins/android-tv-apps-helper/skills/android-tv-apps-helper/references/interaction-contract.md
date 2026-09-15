# Interaction Contract

## Cross-platform invariants

Claude, Codex, WorkBuddy, and 豆包工作 use the same S0–S11 state graph, `pending_question` data, stable option values, mutation approvals, and evidence labels. Host-native controls may change presentation only. They cannot merge questions, omit options, preselect the recommendation, infer consent, or advance the state without a harness-accepted answer.

## Question lock

Every decision creates one `pending_question` before it is rendered. It contains `question_id`, `state_id`, `type`, `prompt`, stable options, `required: true`, `answer_contract`, and `attempts`.

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

For `structured_form`, use stable option values with localized labels and descriptions. Keep the label-to-value map when a host returns display text. Mark blocking inputs `required`. For `explicit_consent`, use one initially unselected confirmation control containing the full action and impact; attachments and other fields are not consent.

## Question types

- `single_choice`: exactly one number, stable value, or unambiguous full label.
- `multi_choice`: only when declared; accept a list such as `1,3,5`.
- `short_text`: require a visible prefix and format, such as `IP: 192.168.31.170` or `路径: /absolute/app.apk`.
- `explicit_consent`: exact confirmation value only; never infer it from “continue”.

Every question includes `safe_exit` (shown as `0. 安全退出`). Include `back` when returning is meaningful.

## Reply shape

Each interactive Agent reply contains, in order:

1. Previous result or verified facts, if any.
2. One question.
3. Options with impact; mark one recommendation when useful.
4. Exact accepted answer format.

The Agent may run already authorized work until the next decision, but every new conversational turn must end with a question and options. If the user asks a side question, answer briefly and then render the still-pending question again.

## Text fallback example

```text
问题 S4-Q1：这是要操作的电视吗？

1. 确认这台电视（推荐）——后续命令只发送到此设备
2. 换一台——返回设备发现
0. 安全退出——停止尚未执行的工作

请明确回复：1、2 或 0。
```
