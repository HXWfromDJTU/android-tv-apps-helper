"""Shared click controller. Transports cannot run device commands or invent evidence."""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .presentation import _presentation_id, _question_rows, render_context_markdown
from .questions import AnswerError, Question
from .session import SessionStore
from .workflow import WorkflowEngine

HTML_HOSTS = {"codex", "claude-desktop", "workbuddy", "doubao-work"}
_LOCKS: dict[str, threading.RLock] = {}
_LOCKS_GUARD = threading.Lock()


@contextmanager
def session_lock(path: Path):
    """Serialize browser/MCP processes, including all intermediate workflow writes."""
    with path.with_suffix(path.suffix + '.html.lock').open('a+b') as lock:
        if os.name == 'nt':
            import msvcrt
            if lock.tell() == 0:
                lock.write(b'0'); lock.flush()
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == 'nt':
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def html_presentation(question: Question, session: dict[str, Any]) -> dict[str, Any]:
    if session.get("host_platform") not in HTML_HOSTS:
        raise ValueError("HTML requires a supported desktop host, not Claude Code.")
    opened = bool((session.get("interaction_ui") or {}).get("input_open"))
    options = [asdict(option) for option in question.options]
    if question.kind == "short_text":
        options[0] = {**options[0], "value": "ui:submit_input" if opened else "ui:input",
                      "label": question.options[0].label if opened else "填写所需信息"}
    content = {"prompt": question.component_prompt(), "options": options, "input_open": opened}
    instance = str(session.get("question_instance_id", "preview")) + json.dumps(session.get("interaction_ui", {}), sort_keys=True)
    return {
        "mode": "html_required", "question_id": question.question_id,
        "presentation_id": _presentation_id(question, session["host_platform"], "html_choice", content, instance),
        "prompt": question.component_prompt(), "kind": question.kind, "options": options,
        "context_markdown": render_context_markdown(question),
        "rows": [asdict(row) for row in _question_rows(question)],
        "blocker": question.blocker_summary, "guidance": list(question.remediation_guidance),
        "accepts_free_input": opened and question.kind == "short_text",
        "selected": (session.get("interaction_ui") or {}).get("selected", []),
        "input_prefix": question.input_prefix, "response_delivery": "html_callback",
    }


class HtmlController:
    def __init__(self, store: SessionStore):
        self.store = store
        with session_lock(store.path):
            data = store.read()
        if data.get("host_platform") not in HTML_HOSTS or data.get("interaction_surface") != "html":
            raise ValueError("Use --surface html on a supported desktop host (or resume-html) first.")
        with _LOCKS_GUARD:
            self.lock = _LOCKS.setdefault(str(store.path.resolve()), threading.RLock())

    def snapshot(self) -> dict[str, Any]:
        with self.lock, session_lock(self.store.path):
            return self._snapshot()

    def _snapshot(self) -> dict[str, Any]:
        data = self.store.read()
        question = Question.from_dict(data["pending_question"]) if data.get("pending_question") else None
        revision = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
        result = {
            "revision": revision, "host_platform": data["host_platform"],
            "state": data["current_state"],
            "presentation": html_presentation(question, data) if question else None,
            "action_required": data.get("pending_action"),
            "terminal": not question and not data.get("pending_action") and str(data["current_state"]).startswith("END"),
            "latest_answer": data.get("history", [])[-1] if data.get("history") else None,
        }
        if result["terminal"]:
            from .report import render_final_report
            result["final_report"] = render_final_report(data)
        return result

    def submit(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self.lock, session_lock(self.store.path):
            view = self._snapshot()["presentation"]
            if not view or payload.get("question_id") != view["question_id"] or payload.get("presentation_id") != view["presentation_id"]:
                raise AnswerError("页面已过期或当前操作正在执行，请刷新后重新选择。")
            values = payload.get("values")
            if not isinstance(values, list) or not values or not all(isinstance(v, str) for v in values):
                raise AnswerError("请先点选选项，再点击确认。")
            allowed = {o["value"] for o in view["options"] if o["enabled"]}
            if len(values) != len(set(values)) or any(v not in allowed for v in values):
                raise AnswerError("请选择当前页面中有效且不重复的选项。")
            if view["kind"] != "multi_choice" and len(values) != 1:
                raise AnswerError("当前问题只能选择一项。")
            text = payload.get("text", "")
            note = payload.get("note", "")
            if not isinstance(note, str) or len(note) > 8192:
                raise AnswerError("补充说明格式不正确。")
            if not isinstance(text, str) or len(text) > 8192:
                raise AnswerError("补充输入格式不正确。")
            if text and values != ["ui:submit_input"]:
                raise AnswerError("请先选择填写信息；补充说明不能代替选择。")
            if values == ["ui:input"]:
                data = self.store.read()
                self.store.update_interaction_ui({**data.get("interaction_ui", {}), "input_open": True})
                return {**self._snapshot(), "accepted": True, "ui_only": True}
            if values == ["ui:submit_input"]:
                if not view["accepts_free_input"]:
                    raise AnswerError("请先选择填写信息。")
                raw = (view["input_prefix"] or "") + text.strip()
            else:
                raw = ",".join(values)
            result = WorkflowEngine(self.store).submit(raw, question_id=view["question_id"])
            if result["accepted"] and note.strip():
                data = self.store.read()
                data["history"][-1]["note"] = note.strip()
                self.store._write(data)
            return {**self._snapshot(), "accepted": result["accepted"], "error": result.get("error")}

    def wait(self, after: str, timeout: float = 25) -> dict[str, Any]:
        deadline = time.monotonic() + max(0, min(timeout, 30))
        while True:
            result = self.snapshot()
            if result["revision"] != after or time.monotonic() >= deadline:
                return {**result, "changed": result["revision"] != after}
            time.sleep(.1)


def html_document() -> str:
    return (Path(__file__).with_name("ui") / "choice.html").read_text(encoding="utf-8")
