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


def _native_compatible(question: Any, platform: str) -> bool:
    options = question.component_options()
    capabilities = NATIVE_CAPABILITIES_BY_PLATFORM[platform]
    if not 2 <= len(options) <= int(capabilities["max_options"]):
        return False
    if any(not item.get("enabled", True) for item in options):
        return False
    if question.kind == "short_text":
        return False
    if question.kind == "multi_choice" and not capabilities["multi_choice"]:
        return False
    return question.kind in {"single_choice", "multi_choice", "explicit_consent"}


def _tool_input(question: Any, platform: str) -> dict[str, Any]:
    options = []
    for item in question.component_options():
        label = str(item["label"])
        if item.get("recommended"):
            label += "（推荐）"
        options.append(
            {
                "label": label,
                "description": str(item.get("description") or "请选择后继续"),
            }
        )
    common = {
        "question": question.component_prompt(),
        "header": _friendly_header(question),
        "options": options,
    }
    if platform == "codex":
        return {
            "questions": [
                {
                    **common,
                    "id": re.sub(r"[^a-z0-9]+", "_", question.question_id.lower()).strip("_"),
                }
            ]
        }
    return {
        "questions": [
            {
                **common,
                "multiSelect": question.kind == "multi_choice",
            }
        ]
    }


def _presentation_id(question: Any, platform: str, tool_name: str, tool_input: dict[str, Any], instance_id: str) -> str:
    payload = {
        "platform": platform,
        "question_instance_id": instance_id,
        "question": question.to_dict(),
        "tool_name": tool_name,
        "tool_input": tool_input,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "PRES-" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:20]


def build_host_presentation(question: Any, session: dict[str, Any]) -> dict[str, Any]:
    """Build one deterministic host UI directive for the pending question."""
    platform = str(session.get("host_platform", "codex"))
    surface = str(session.get("interaction_surface", "text_menu"))
    capabilities = session.get("interaction_capabilities") or {}
    current_failure = capabilities.get("fallback_question_id") == question.question_id
    if surface == "structured_form" and current_failure:
        reason = str(capabilities.get("fallback_reason") or "native_tool_call_failed")
        return {
            "mode": "text_fallback",
            "tool_name": None,
            "tool_input": None,
            "answer_value_map": {},
            "question_id": question.question_id,
            "fallback_reason": reason,
            "rendered": render_question_markdown(question, fallback_reason=reason),
        }
    if surface == "structured_form" and _native_compatible(question, platform):
        tool_name = NATIVE_TOOL_BY_PLATFORM[platform]
        tool_input = _tool_input(question, platform)
        answer_value_map: dict[str, str] = {}
        for item in question.component_options():
            label = str(item["label"])
            answer_value_map[label] = str(item["value"])
            if item.get("recommended"):
                answer_value_map[f"{label}（推荐）"] = str(item["value"])
        return {
            "mode": "native_required",
            "tool_name": tool_name,
            "tool_input": tool_input,
            "presentation_id": _presentation_id(question, platform, tool_name, tool_input, str(session.get("question_instance_id", "preview"))),
            "answer_value_map": answer_value_map,
            "question_id": question.question_id,
            "context_markdown": render_context_markdown(question),
            "rendered": None,
        }
    if surface == "structured_form":
        reason = "question_not_native_compatible"
    else:
        reason = str(capabilities.get("fallback_reason") or "legacy_text_menu")
    return {
        "mode": "text_fallback",
        "tool_name": None,
        "tool_input": None,
        "answer_value_map": {},
        "question_id": question.question_id,
        "fallback_reason": reason,
        "rendered": render_question_markdown(question, fallback_reason=reason),
    }
