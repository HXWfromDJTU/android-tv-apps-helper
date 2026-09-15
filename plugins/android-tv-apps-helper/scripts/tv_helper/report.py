from __future__ import annotations

from typing import Any


SYMBOLS = {
    "completed": "✅",
    "failed": "❌",
    "attention": "⚠️",
    "pending": "⏳",
    "skipped": "⏭️",
}

ACTION_LABELS = {
    "UPDATE-ACTION": "Skill 更新",
    "DOWNLOAD-ACTION": "应用下载与包体验证",
    "INSTALL-ACTION": "应用安装",
    "HOME-ACTION": "Home 键默认桌面",
    "WALLPAPER-ACTION": "电视壁纸",
    "FINISH-CHECK": "ADB 关闭复核",
}


def _cell(value: Any) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", "<br>")


def render_final_report(session: dict[str, Any]) -> str:
    rows: list[tuple[str, str, str, str]] = []
    identity = session.get("device_identity") or {}
    model = identity.get("display_name") or identity.get("model")
    if model:
        rows.append(("completed", "目标电视", str(model), "只读设备身份"))

    for record in session.get("evidence_records", ()):
        status = str(record.get("status", "attention"))
        evidence = record.get("evidence") or {}
        rows.append(
            (
                status,
                ACTION_LABELS.get(str(record.get("action_id")), str(record.get("action_id", "操作"))),
                str(evidence.get("result", status)),
                str(evidence.get("evidence_level", evidence.get("sha256", "执行记录"))),
            )
        )

    onsite = next(
        (
            item for item in reversed(session.get("history", ()))
            if item.get("question_id") == "VERIFY-Q1"
        ),
        None,
    )
    if onsite:
        answer = onsite.get("answer")
        status = "completed" if answer == "all_normal" else "attention"
        rows.append((status, "电视现场验收", str(answer), "用户现场选择"))

    finish = session.get("finish_safety") or {}
    if finish.get("completed"):
        rows.append(("completed", "ADB 与开发者模式", "用户确认已关闭", "用户确认 + 只读冲突复核"))
    elif finish.get("user_confirmation") == "keep_enabled":
        rows.append(("attention", "ADB 与开发者模式", "用户选择暂时保持开启", "存在同网络访问风险"))
    elif session.get("target_serial") or (session.get("pending_action") or {}).get("action_id") == "FINISH-CHECK":
        rows.append(("pending", "ADB 与开发者模式", "尚未完成安全收尾", "等待用户确认"))

    if not rows:
        rows.append(("skipped", "电视变更", "本次未执行电视操作", "会话记录"))

    lines = [
        "# 最终结果",
        "",
        "| 状态 | 事项 | 最终结果 | 证据 |",
        "|---|---|---|---|",
    ]
    for status, item, result, evidence in rows:
        lines.append(
            f"| {SYMBOLS.get(status, '⚠️')} | {_cell(item)} | {_cell(result)} | {_cell(evidence)} |"
        )
    lines.extend(
        [
            "",
            "> ✅ 表示已完成；❌ 表示实际尝试后仍未完成；⚠️ 表示风险或等待现场确认；⏳ 表示待处理；⏭️ 表示未执行。",
            "",
        ]
    )
    return "\n".join(lines)
