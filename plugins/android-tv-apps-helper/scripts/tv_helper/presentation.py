from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


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
