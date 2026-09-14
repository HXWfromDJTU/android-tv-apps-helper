from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .questions import Answer, AnswerError, Question, validate_answer


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


class SessionStore:
    def __init__(self, path: Path):
        self.path = Path(path)

    @classmethod
    def create(cls, path: Path, *, interaction_surface: str) -> "SessionStore":
        if interaction_surface not in {"structured_form", "text_menu"}:
            raise ValueError("interaction_surface must be structured_form or text_menu")
        store = cls(path)
        store._write(
            {
                "schema_version": 1,
                "created_at": _timestamp(),
                "updated_at": _timestamp(),
                "interaction_surface": interaction_surface,
                "current_state": "S0",
                "pending_question": None,
                "target_serial": None,
                "approved_plan": None,
                "history": [],
            }
        )
        return store

    def read(self) -> dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def set_question(self, question: Question) -> None:
        data = self.read()
        data["current_state"] = question.state_id
        data["pending_question"] = question.to_dict()
        data["updated_at"] = _timestamp()
        self._write(data)

    def answer(
        self,
        raw: str | None,
        *,
        submitted_question_id: str | None = None,
    ) -> Answer:
        data = self.read()
        pending = data.get("pending_question")
        if not pending:
            raise AnswerError("当前没有待回答的问题。")
        question = Question.from_dict(pending)
        try:
            answer = validate_answer(
                question,
                raw,
                submitted_question_id=submitted_question_id,
            )
        except AnswerError:
            pending["attempts"] = int(pending.get("attempts", 0)) + 1
            data["pending_question"] = pending
            data["updated_at"] = _timestamp()
            self._write(data)
            raise

        data["history"].append(
            {
                "question_id": question.question_id,
                "state_id": question.state_id,
                "answer": answer.value,
                "answered_at": _timestamp(),
            }
        )
        data["current_state"] = answer.next_state
        data["pending_question"] = None
        data["updated_at"] = _timestamp()
        self._write(data)
        return answer

    def _write(self, value: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, self.path)
