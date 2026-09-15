from __future__ import annotations

import ipaddress
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


class AnswerError(ValueError):
    """Raised when a reply does not satisfy the pending question contract."""


@dataclass(frozen=True)
class Option:
    value: str
    label: str
    next_state: str
    description: str = ""
    recommended: bool = False
    shortcut: str | None = None
    enabled: bool = True
    unavailable_reason: str = ""

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Option":
        return cls(**value)


@dataclass(frozen=True)
class Question:
    question_id: str
    state_id: str
    kind: str
    prompt: str
    options: tuple[Option, ...]
    required: bool = True
    input_prefix: str | None = None
    input_format: str | None = None
    attempts: int = 0
    previous_result_summary: str = ""
    progress_summary: str = ""
    blocker_summary: str = ""
    remediation_guidance: tuple[str, ...] = ()
    evidence: tuple[dict[str, Any], ...] = ()
    summary_rows: tuple[dict[str, Any], ...] = ()
    visual_aid: str | None = None
    accepted_attachment: str | None = None
    display_name: str | None = None

    def component_prompt(self) -> str:
        """Return a host-ready prompt that keeps context inside the question card."""
        parts: list[str] = []
        if self.previous_result_summary:
            parts.append(f"上一轮/当前进度：{self.previous_result_summary}")
        if self.summary_rows:
            compact = "；".join(
                f"{row.get('item', '事项')}：{row.get('result', '')}"
                for row in self.summary_rows[:6]
            )
            if compact:
                parts.append(f"检查结果：{compact}")
        if self.blocker_summary:
            parts.append(f"当前阻塞/风险：{self.blocker_summary}")
        if self.remediation_guidance:
            parts.append("处理方法：" + "；".join(self.remediation_guidance[:6]))
        parts.append(f"问题：{self.prompt}")
        return "\n".join(parts)

    def component_options(self) -> list[dict[str, Any]]:
        """Options suitable for native cards; omit the synthetic text-submit row."""
        start = 2 if self.kind == "short_text" else 1
        options = self.options[1:] if self.kind == "short_text" else self.options
        result = []
        for index, option in enumerate(options, start=start):
            item = asdict(option)
            item["display_index"] = option.shortcut or str(index)
            result.append(item)
        return result

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["options"] = [asdict(option) for option in self.options]
        value["component_prompt"] = self.component_prompt()
        value["component_options"] = self.component_options()
        value["native_card_compatible"] = len(value["component_options"]) <= 4
        return value

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Question":
        copy = dict(value)
        copy.pop("component_prompt", None)
        copy.pop("component_options", None)
        copy.pop("native_card_compatible", None)
        copy["options"] = tuple(Option.from_dict(item) for item in copy["options"])
        for field in ("remediation_guidance", "evidence", "summary_rows"):
            copy[field] = tuple(copy.get(field, ()))
        return cls(**copy)


@dataclass(frozen=True)
class Answer:
    value: str | tuple[str, ...]
    next_state: str
    option_values: tuple[str, ...]


def _normalized_choice(raw: str) -> str:
    return re.sub(r"^(?:选|选择)\s*", "", raw.strip(), count=1)


def _match_option(question: Question, token: str) -> Option:
    normalized = _normalized_choice(token)
    for index, option in enumerate(question.options, start=1):
        accepted = {str(index), option.value, option.label}
        if option.shortcut:
            accepted.add(option.shortcut)
        if normalized in accepted:
            if not option.enabled:
                reason = f"：{option.unavailable_reason}" if option.unavailable_reason else ""
                raise AnswerError(f"此选项当前不可选择{reason}")
            return option
    raise AnswerError("请明确选择当前问题中存在的一个选项。")


def _validate_short_text(question: Question, raw: str) -> Answer:
    normalized = _normalized_choice(raw)
    for index, option in enumerate(question.options[1:], start=2):
        accepted = {str(index), option.value, option.label}
        if option.shortcut:
            accepted.add(option.shortcut)
        if normalized in accepted:
            if not option.enabled:
                raise AnswerError(f"此选项当前不可选择：{option.unavailable_reason}")
            return Answer(
                value=option.value,
                next_state=option.next_state,
                option_values=(option.value,),
            )
    prefix = question.input_prefix
    if not prefix or not raw.strip().startswith(prefix):
        raise AnswerError(f"请使用 {prefix or '题目指定的'} 格式明确回答。")
    value = raw.strip()[len(prefix) :].strip()
    if not value:
        raise AnswerError("提交值不能为空。")
    if question.input_format == "ipv4":
        try:
            parsed = ipaddress.ip_address(value)
        except ValueError as error:
            raise AnswerError("请输入有效的 IPv4 地址。") from error
        if parsed.version != 4:
            raise AnswerError("请输入有效的 IPv4 地址。")
    elif question.input_format == "absolute_path" and not Path(value).is_absolute():
        raise AnswerError("请输入有效的绝对路径。")
    return Answer(value=value, next_state=question.options[0].next_state, option_values=(question.options[0].value,))


def validate_answer(
    question: Question,
    raw: str | None,
    *,
    submitted_question_id: str | None = None,
) -> Answer:
    if submitted_question_id and submitted_question_id != question.question_id:
        raise AnswerError("这不是当前问题的回答，请回答当前问题。")
    if raw is None or not raw.strip():
        raise AnswerError("请明确回答当前问题。")
    if question.kind == "short_text":
        return _validate_short_text(question, raw)
    if question.kind == "single_choice" or question.kind == "explicit_consent":
        if re.search(r"[,，、/]", raw):
            raise AnswerError("这是单选问题，请只选择一个选项。")
        option = _match_option(question, raw)
        return Answer(value=option.value, next_state=option.next_state, option_values=(option.value,))
    if question.kind == "multi_choice":
        tokens = [item.strip() for item in re.split(r"[,，、\s]+", raw) if item.strip()]
        if not tokens:
            raise AnswerError("请明确选择至少一个选项。")
        selected: list[Option] = []
        for token in tokens:
            option = _match_option(question, token)
            if option in selected:
                raise AnswerError(f"选项“{option.label}”重复，请每项只选择一次。")
            selected.append(option)
        next_states = {option.next_state for option in selected}
        if len(next_states) != 1:
            raise AnswerError("所选项目不能同时进入不同的下一状态。")
        return Answer(
            value=tuple(option.value for option in selected),
            next_state=selected[0].next_state,
            option_values=tuple(option.value for option in selected),
        )
    raise AnswerError(f"不支持的问题类型：{question.kind}")
