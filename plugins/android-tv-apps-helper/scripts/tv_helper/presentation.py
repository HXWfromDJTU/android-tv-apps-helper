from __future__ import annotations

import json
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


STATUS_SYMBOLS = {
    "completed": "✅",
    "failed": "❌",
    "attention": "⚠️",
    "pending": "⏳",
    "skipped": "⏭️",
}


@dataclass(frozen=True)
class SummaryRow:
    status: str
    item: str
    result: str
    evidence: str = ""


@dataclass(frozen=True)
class InteractionFrame:
    rows: tuple[SummaryRow, ...]
    blocker: str
    guidance: tuple[str, ...]
    question_id: str
    question: str
    options: tuple[tuple[str, str, str] | tuple[str, str, str, str | None], ...]
    accepted_answer: str


def status_symbol(status: str) -> str:
    try:
        return STATUS_SYMBOLS[status]
    except KeyError as error:
        raise ValueError(f"Unsupported summary status: {status}") from error


def _copy_registry() -> dict[str, object]:
    path = Path(__file__).parents[2] / "data" / "copy.zh-CN.json"
    return json.loads(path.read_text(encoding="utf-8"))


def friendly_plan_name(sequence: int, action: str) -> str:
    if sequence < 1 or sequence > 99:
        raise ValueError("Plan sequence must be between 1 and 99.")
    actions = _copy_registry()["actions"]
    if not isinstance(actions, dict) or action not in actions:
        raise ValueError(f"Unsupported action label: {action}")
    return f"方案 {sequence:02d}：{actions[action]}"


def render_markdown(frame: InteractionFrame) -> str:
    lines = [
        "| 状态 | 项目 | 结果 | 依据 |",
        "| --- | --- | --- | --- |",
    ]
    for row in frame.rows:
        lines.append(
            f"| {status_symbol(row.status)} | {row.item} | {row.result} | {row.evidence or '—'} |"
        )
    if frame.blocker:
        lines.extend(("", f"当前阻塞：{frame.blocker}"))
    if frame.guidance:
        lines.extend(("", "处理指引："))
        lines.extend(f"{index}. {item}" for index, item in enumerate(frame.guidance, 1))
    lines.extend(("", f"问题 {frame.question_id}：{frame.question}", ""))
    for index, option in enumerate(frame.options, 1):
        _, label, description = option[:3]
        shortcut = option[3] if len(option) == 4 else None
        suffix = f"——{description}" if description else ""
        display_index = shortcut or str(index)
        lines.append(f"{display_index}. {label}{suffix}")
    lines.extend(("", frame.accepted_answer))
    return "\n".join(lines) + "\n"


NATIVE_TOOL_BY_PLATFORM = {
    "claude": "AskUserQuestion",
    "workbuddy": "AskUserQuestion",
    "doubao-work": "AskUserQuestion",
    "codex": "request_user_input",
}

NATIVE_CAPABILITIES_BY_PLATFORM = {
    "claude": {"max_options": 4, "multi_choice": True},
    "workbuddy": {"max_options": 4, "multi_choice": True},
    "doubao-work": {"max_options": 4, "multi_choice": True},
    "codex": {"max_options": 3, "multi_choice": False},
}

FALLBACK_LABELS = {
    "native_tool_not_exposed": "当前执行模式没有向 Skill 提供原生选择组件",
    "native_tool_call_failed": "原生选择组件调用失败",
    "native_tool_render_failed": "原生选择组件未能正常显示",
    "question_not_native_compatible": "当前问题超出原生组件支持的题型或选项数量",
    "legacy_text_menu": "旧会话使用文字菜单；新会话会重新检测原生组件",
}

HEADER_BY_STATE = {
    "PRECHECK-WIFI": "网络预检查",
    "PRECHECK_WIFI": "网络预检查",
    "PRECHECK-ADB": "ADB预检查",
    "PRECHECK_ADB": "ADB预检查",
    "DISCOVERY-NONE": "发现电视",
    "TARGET": "确认电视",
    "TASK": "选择任务",
    "APPS": "选择应用",
    "DOWNLOAD-CONFIRM": "确认下载",
    "HOME": "设置桌面",
    "WALLPAPER": "设置壁纸",
    "FINISH-SAFETY": "安全收尾",
}


def _friendly_header(question: Any) -> str:
    return HEADER_BY_STATE.get(str(question.state_id), "下一步")[:12]


def _question_rows(question: Any) -> tuple[SummaryRow, ...]:
    rows = tuple(
        SummaryRow(
            str(row.get("status", "pending")),
            str(row.get("item", "事项")),
            str(row.get("result", "")),
            str(row.get("evidence", "")),
        )
        for row in question.summary_rows
    )
    if question.previous_result_summary:
        rows = (
            SummaryRow("completed", "上一轮/当前进度", question.previous_result_summary),
            *rows,
        )
    return rows or (SummaryRow("pending", "当前进度", "等待处理"),)


def render_question_markdown(question: Any, *, fallback_reason: str | None = None) -> str:
    rows = _question_rows(question)
    if fallback_reason:
        rows = (
            SummaryRow(
                "attention",
                "交互方式",
                FALLBACK_LABELS.get(fallback_reason, "原生选择组件不可用，已降级为文字选择"),
                fallback_reason,
            ),
            *rows,
        )
    numbered = [
        option.shortcut or str(index)
        for index, option in enumerate(question.options, 1)
        if option.enabled
    ]
    if question.kind == "multi_choice":
        accepted = "请用原生多选，或回复编号并用分隔符连接，例如：1、2；返回/退出须单独选择。"
    elif question.kind == "short_text":
        accepted = f"请按“{question.input_prefix}…”格式回答，或明确回复：" + "、".join(numbered[1:]) + "。"
    else:
        accepted = "请明确回复：" + "、".join(numbered) + "。"
    frame_options = []
    start = 2 if question.kind == "short_text" else 1
    visible_options = question.options[1:] if question.kind == "short_text" else question.options
    for original_index, option in enumerate(visible_options, start=start):
        label = option.label
        description = option.description
        if option.recommended:
            label += "（推荐）"
        if not option.enabled:
            label += "（不可选）"
            description = option.unavailable_reason or description
        frame_options.append((option.value, label, description, option.shortcut or str(original_index)))
    return render_markdown(
        InteractionFrame(
            rows=rows,
            blocker=question.blocker_summary,
            guidance=question.remediation_guidance,
            question_id=question.question_id,
            question=question.prompt,
            options=tuple(frame_options),
            accepted_answer=accepted,
        )
    )


def render_context_markdown(question: Any) -> str:
    """Render the evidence context that must stay adjacent to a native control."""
    frame = InteractionFrame(
        rows=_question_rows(question),
        blocker=question.blocker_summary,
        guidance=question.remediation_guidance,
        question_id="",
        question="",
        options=(),
        accepted_answer="",
    )
    lines = [
        "| 状态 | 项目 | 结果 | 依据 |",
        "| --- | --- | --- | --- |",
    ]
    for row in frame.rows:
        lines.append(
            f"| {status_symbol(row.status)} | {row.item} | {row.result} | {row.evidence or '—'} |"
        )
    if frame.blocker:
        lines.extend(("", f"当前阻塞：{frame.blocker}"))
    if frame.guidance:
        lines.extend(("", "处理指引："))
        lines.extend(f"{index}. {item}" for index, item in enumerate(frame.guidance, 1))
    return "\n".join(lines) + "\n"


def _choice_page(question: Any, platform: str, ui: dict[str, Any]) -> tuple[list[dict[str, Any]], bool, bool, int]:
    """Adapt choices without replacing the user's decision with a text menu."""
    limit = int(NATIVE_CAPABILITIES_BY_PLATFORM[platform]["max_options"])
    selected = set(ui.get("selected", ()))
    items = [dict(item) for item in question.component_options() if item.get("enabled", True)]
    free_input = question.kind == "short_text" and ui.get("input_open", False)
    if question.kind == "short_text":
        if free_input:
            items = [
                {"value": "ui:cancel_input", "label": "返回选项", "description": "不提交输入"},
                *[item for item in items if item["value"] == "safe_exit"],
            ]
        else:
            items.insert(0, {"value": "ui:input", "label": "填写信息", "description": question.prompt})
    native_multi = (
        question.kind == "multi_choice"
        and NATIVE_CAPABILITIES_BY_PLATFORM[platform]["multi_choice"]
        and len(items) <= limit
    )
    if question.kind == "multi_choice" and not native_multi:
        for item in items:
            if item["value"] not in {"back", "safe_exit"}:
                value = item["value"]
                item["value"] = "ui:toggle:" + value
                item["label"] = ("取消选择：" if value in selected else "选择：") + item["label"]
        items.append({"value": "ui:done", "label": "完成选择", "description": "下一步按应用名称确认；此处不下载"})
    if len(items) <= limit:
        if len(items) == 1:
            items.insert(0, {"value": "ui:refresh", "label": "重新查看", "description": "保持当前问题"})
        return items, native_multi, free_input, 1
    # Exit remains visible on every page. Navigation never submits a workflow answer.
    exits = [item for item in items if item["value"] == "safe_exit"]
    content = [item for item in items if item["value"] != "safe_exit"]
    size = limit - 1 - len(exits)
    pages = (len(content) + size - 1) // size
    page = int(ui.get("page", 0)) % pages
    visible = content[page * size:(page + 1) * size]
    visible.append({"value": "ui:next", "label": f"更多选项（{page + 1}/{pages}）", "description": "翻页查看其他选项；不会执行操作"})
    return [*visible, *exits], False, free_input, pages


def _presentation_id(question: Any, platform: str, tool_name: str, tool_input: dict[str, Any], instance_id: str) -> str:
    payload = {
        "platform": platform, "question_instance_id": instance_id,
        "question": question.to_dict(), "tool_name": tool_name, "tool_input": tool_input,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "PRES-" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:20]


def build_host_presentation(question: Any, session: dict[str, Any]) -> dict[str, Any]:
    """All decisions require a native control; missing controls pause, never downgrade."""
    platform = str(session.get("host_platform", "codex"))
    capabilities = session.get("interaction_capabilities") or {}
    ui = session.get("interaction_ui") or {}
    context = render_context_markdown(question)
    note_header = "\n| 状态 | 项目 | 结果 | 依据 |\n| --- | --- | --- | --- |\n"
    disabled = [item for item in question.options if not item.enabled]
    if disabled:
        context += note_header
    for item in disabled:
        context += f"| ⏭️ | {item.label}（不可选） | {item.unavailable_reason or '当前不可用'} | — |\n"
    selected = set(ui.get("selected", ()))
    if question.kind == "multi_choice":
        names = [item.label for item in question.options if item.value in selected]
        context += "\n已选应用：" + ("、".join(names) or "尚未选择") + "。\n"
    reason = capabilities.get("fallback_reason")
    failed_here = capabilities.get("question_id") == question.question_id
    blocked = capabilities.get("native_status") == "blocked" or (
        reason == "native_tool_not_exposed" and capabilities.get("native_status") == "failed"
    )
    if blocked:
        context += note_header + "| ⚠️ | 原生组件不可用 | 当前问题已保留，请恢复宿主组件后重试；不会改为输入编号 | " + str(reason or "host_unavailable") + " |\n"
        return {
            "mode": "native_blocked", "question_id": question.question_id,
            "tool_name": None, "tool_input": None, "answer_value_map": {},
            "context_markdown": context, "rendered": context,
            "blocked_reason": reason or "host_unavailable",
        }
    if failed_here and reason:
        context += note_header + "| ⚠️ | 原生组件重试 | 上次调用未成功，仍使用原生选择组件 | " + str(reason) + " |\n"
    items, multi, free_input, pages = _choice_page(question, platform, ui)
    options, answer_map = [], {}
    for item in items:
        label = item["label"] + ("（推荐）" if item.get("recommended") else "")
        options.append({"label": label, "description": item.get("description") or "请选择后继续"})
        answer_map[label] = item["value"]
        answer_map[item["label"]] = item["value"]
    prompt = question.component_prompt()
    if question.kind == "short_text" and not free_input:
        prompt = "请选择填写信息或其他操作。"
    if free_input:
        context += f"\n已选择填写信息：请使用组件末尾的补充输入框，格式为 {question.input_prefix}…；也可选择返回或退出。\n"
    tool_question = {"question": prompt, "header": _friendly_header(question), "options": options}
    if platform == "codex":
        tool_question["id"] = re.sub(r"[^a-z0-9]+", "_", question.question_id.lower()).strip("_")
    else:
        tool_question["multiSelect"] = multi
    tool_input = {"questions": [tool_question]}
    tool_name = NATIVE_TOOL_BY_PLATFORM[platform]
    instance = str(session.get("question_instance_id", "preview")) + json.dumps(
        [ui, capabilities.get("failure_count", 0)], sort_keys=True, ensure_ascii=False
    )
    return {
        "mode": "native_required", "tool_name": tool_name, "tool_input": tool_input,
        "presentation_id": _presentation_id(question, platform, tool_name, tool_input, instance),
        "answer_value_map": answer_map, "question_id": question.question_id,
        "context_markdown": context, "rendered": None, "page_count": pages,
        "accepts_free_input": free_input, "native_multi": multi,
        "supplemental_input": "host_native_other",
    }
