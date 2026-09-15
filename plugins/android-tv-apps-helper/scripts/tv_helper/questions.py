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

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["options"] = [asdict(option) for option in self.options]
        return value

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Question":
        copy = dict(value)
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
