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
    def create(
        cls,
        path: Path,
        *,
        interaction_surface: str,
        host_platform: str = "codex",
        execution_context: str = "local_computer",
        skill_root: str | None = None,
        python_command: str = "python3",
    ) -> "SessionStore":
        if interaction_surface not in {"structured_form", "text_menu"}:
            raise ValueError("interaction_surface must be structured_form or text_menu")
        supported_platforms = {"claude", "codex", "workbuddy", "doubao-work"}
        if host_platform not in supported_platforms:
            raise ValueError(f"Unsupported host_platform: {host_platform}")
        if execution_context != "local_computer":
            raise ValueError(
                "Android TV ADB requires execution_context=local_computer; "
                "a cloud computer cannot reach the local TV safely."
            )
        store = cls(path)
        store._write(
            {
                "schema_version": 3,
                "created_at": _timestamp(),
                "updated_at": _timestamp(),
                "host_platform": host_platform,
                "execution_context": execution_context,
                "interaction_surface": interaction_surface,
                "skill_root": skill_root,
                "python_command": python_command,
                "adb_path": None,
                "runtime_ready": True,
                "current_state": "S0",
                "pending_question": None,
                "target_serial": None,
                "approved_plan": None,
                "history": [],
                "workflow_revision": "v0.3.0",
                "session_sequence": 0,
                "interaction_capabilities": {},
                "update_check": {},
                "precheck": {},
                "device_identity": {},
                "device_guide_match": None,
                "compatibility_matches": [],
                "selected_apps": [],
                "download_confirmation": None,
                "wallpaper_asset": None,
                "evidence_records": [],
                "summary_rows": [],
                "finish_safety": {},
            }
        )
        return store

    def read(self) -> dict[str, Any]:
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if data.get("schema_version") == 2:
            data = self._migrate_schema_two(data)
            self._write(data)
        if data.get("schema_version") != 3:
            raise ValueError("Unsupported session schema version.")
        return data

    @staticmethod
    def _migrate_schema_two(data: dict[str, Any]) -> dict[str, Any]:
        migrated = dict(data)
        migrated["schema_version"] = 3
        defaults = {
            "workflow_revision": "v0.3.0",
            "session_sequence": 0,
            "interaction_capabilities": {},
            "update_check": {},
            "precheck": {},
            "device_identity": {},
            "device_guide_match": None,
            "compatibility_matches": [],
            "selected_apps": [],
            "download_confirmation": None,
            "wallpaper_asset": None,
            "evidence_records": [],
            "summary_rows": [],
            "finish_safety": {},
        }
        for key, value in defaults.items():
            migrated.setdefault(key, value)
        migrated["updated_at"] = _timestamp()
        return migrated

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

    def set_approved_plan(self, plan: dict[str, Any]) -> None:
        data = self.read()
        data["approved_plan"] = plan
        data["updated_at"] = _timestamp()
        self._write(data)

    def _write(self, value: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, self.path)
