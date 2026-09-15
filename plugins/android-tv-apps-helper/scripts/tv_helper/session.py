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
                "pending_action": None,
                "target_serial": None,
                "candidate_ip": None,
                "approved_plan": None,
                "history": [],
                "workflow_revision": "v0.3.0",
                "session_sequence": 0,
                "interaction_capabilities": {},
                "update_check": {},
                "update_state_path": None,
                "precheck": {},
                "device_identity": {},
                "device_guide_match": None,
                "compatibility_matches": [],
                "selected_launcher_actions": [],
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
            "update_state_path": None,
            "precheck": {},
            "device_identity": {},
            "device_guide_match": None,
            "compatibility_matches": [],
            "selected_launcher_actions": [],
            "selected_apps": [],
            "download_confirmation": None,
            "wallpaper_asset": None,
            "evidence_records": [],
            "summary_rows": [],
            "finish_safety": {},
            "pending_action": None,
            "candidate_ip": None,
        }
        for key, value in defaults.items():
            migrated.setdefault(key, value)
        migrated["updated_at"] = _timestamp()
        if isinstance(migrated.get("approved_plan"), dict):
            migrated["approved_plan"] = {
                **migrated["approved_plan"],
                "requires_revalidation": True,
                "revalidation_reason": "Session migrated to workflow revision v0.3.0.",
            }
        return migrated

    def set_question(self, question: Question) -> None:
        data = self.read()
        pending = data.get("pending_question")
        if pending:
            raise AnswerError(f"问题 {pending['question_id']} 尚未回答，不能覆盖待答问题。")
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

    def update_fields(self, **fields: Any) -> None:
        data = self.read()
        allowed = {
            "current_state",
            "target_serial",
            "candidate_ip",
            "update_check",
            "update_state_path",
            "precheck",
            "device_identity",
            "device_guide_match",
            "compatibility_matches",
            "selected_launcher_actions",
            "selected_apps",
            "download_confirmation",
            "wallpaper_asset",
            "evidence_records",
            "summary_rows",
            "finish_safety",
            "pending_action",
        }
        unknown = set(fields) - allowed
        if unknown:
            raise ValueError(f"Unsupported session fields: {', '.join(sorted(unknown))}")
        pending = data.get("pending_question")
        if pending and "current_state" in fields and fields["current_state"] != pending["state_id"]:
            raise AnswerError("待答问题存在时不能单独改变 current_state。")
        data.update(fields)
        data["updated_at"] = _timestamp()
        self._write(data)

    def set_pending_action(self, action: dict[str, Any]) -> None:
        data = self.read()
        if data.get("pending_question"):
            raise AnswerError("待答问题存在时不能开始操作。")
        if data.get("pending_action"):
            raise AnswerError("已有尚未提交结果的操作。")
        data["pending_action"] = action
        data["current_state"] = action["action_id"]
        data["updated_at"] = _timestamp()
        self._write(data)

    def complete_pending_action(
        self, action_id: str, *, status: str, evidence: dict[str, Any]
    ) -> dict[str, Any]:
        data = self.read()
        pending = data.get("pending_action")
        if not pending or pending.get("action_id") != action_id:
            raise AnswerError("操作结果与当前待执行操作不匹配。")
        if status not in {"completed", "failed", "attention"}:
            raise AnswerError("操作结果必须是 completed、failed 或 attention。")
        record = {**pending, "status": status, "evidence": evidence, "completed_at": _timestamp()}
        data["evidence_records"].append(record)
        data["pending_action"] = None
        data["updated_at"] = _timestamp()
        self._write(data)
        return record

    def replace_pending_context(self, question: Question) -> None:
        data = self.read()
        pending = data.get("pending_question")
        if not pending:
            raise AnswerError("当前没有可更新的待答问题。")
        original = Question.from_dict(pending)
        immutable = (
            "question_id",
            "state_id",
            "kind",
            "prompt",
            "options",
            "required",
            "input_prefix",
            "input_format",
        )
        if any(getattr(original, field) != getattr(question, field) for field in immutable):
            raise AnswerError("只能更新当前问题的证据和阻塞上下文，不能改变问题或选项。")
        replacement = question.to_dict()
        replacement["attempts"] = pending.get("attempts", 0)
        data["pending_question"] = replacement
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
