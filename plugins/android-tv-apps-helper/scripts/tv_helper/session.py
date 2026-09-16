from __future__ import annotations

import json
import os
import uuid
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
        if interaction_surface not in {"auto", "structured_form", "text_menu"}:
            raise ValueError("interaction_surface must be auto, structured_form or text_menu")
        supported_platforms = {"claude", "codex", "workbuddy", "doubao-work"}
        if host_platform not in supported_platforms:
            raise ValueError(f"Unsupported host_platform: {host_platform}")
        if execution_context != "local_computer":
            raise ValueError(
                "Android TV ADB requires execution_context=local_computer; "
                "a cloud computer cannot reach the local TV safely."
            )
        requested_surface = interaction_surface
        resolved_surface = "structured_form" if interaction_surface == "auto" else interaction_surface
        store = cls(path)
        store._write(
            {
                "schema_version": 3,
                "created_at": _timestamp(),
                "updated_at": _timestamp(),
                "host_platform": host_platform,
                "execution_context": execution_context,
                "interaction_surface": resolved_surface,
                "interaction_surface_requested": requested_surface,
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
                "workflow_revision": "v0.3.1",
                "session_sequence": 0,
                "interaction_capabilities": {
                    "native_status": "pending" if resolved_surface == "structured_form" else "unavailable",
                    **(
                        {"fallback_reason": "legacy_text_menu"}
                        if resolved_surface == "text_menu"
                        else {}
                    ),
                },
                "update_check": {},
                "update_state_path": None,
                "precheck": {},
                "device_identity": {},
                "device_guide_match": None,
                "compatibility_matches": [],
                "selected_launcher_actions": [],
                "selected_apps": [],
                "installed_apps": {},
                "emotn_runtime": {},
                "download_confirmation": None,
                "verified_downloads": [],
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
        changed = False
        if "interaction_surface_requested" not in data:
            data["interaction_surface_requested"] = data.get("interaction_surface", "text_menu")
            changed = True
        if "interaction_capabilities" not in data:
            data["interaction_capabilities"] = {}
            changed = True
        if data.get("pending_question") and not data.get("question_instance_id"):
            data["question_instance_id"] = uuid.uuid4().hex
            changed = True
        if changed:
            self._write(data)
        return data

    @staticmethod
    def _migrate_schema_two(data: dict[str, Any]) -> dict[str, Any]:
        migrated = dict(data)
        migrated["schema_version"] = 3
        defaults = {
            "workflow_revision": "v0.3.1",
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
            "installed_apps": {},
            "emotn_runtime": {},
            "download_confirmation": None,
            "verified_downloads": [],
            "wallpaper_asset": None,
            "evidence_records": [],
            "summary_rows": [],
            "finish_safety": {},
            "pending_action": None,
            "candidate_ip": None,
            "interaction_surface_requested": data.get("interaction_surface", "text_menu"),
        }
        for key, value in defaults.items():
            migrated.setdefault(key, value)
        migrated["updated_at"] = _timestamp()
        if isinstance(migrated.get("approved_plan"), dict):
            migrated["approved_plan"] = {
                **migrated["approved_plan"],
                "requires_revalidation": True,
                "revalidation_reason": "Session migrated to workflow revision v0.3.1.",
            }
        return migrated

    def record_surface_failure(
        self,
        reason: str,
        *,
        detail: str,
        question_id: str,
        presentation_id: str,
        tool_name: str,
    ) -> None:
        allowed_reasons = {
            "native_tool_not_exposed",
            "native_tool_call_failed",
            "native_tool_render_failed",
        }
        if reason not in allowed_reasons:
            raise ValueError(f"Unsupported native surface failure reason: {reason}")
        if not detail.strip():
            raise ValueError("Native surface failure detail cannot be empty.")
        data = self.read()
        if not data.get("pending_question"):
            raise AnswerError("没有待答问题时不能降级交互界面。")
        if data.get("interaction_surface") != "structured_form":
            raise AnswerError("当前会话已经不是原生组件模式。")
        from .presentation import build_host_presentation

        pending = Question.from_dict(data["pending_question"])
        expected = build_host_presentation(pending, data)
        if expected.get("mode") != "native_required":
            raise AnswerError("当前问题没有待记录的原生组件展示。")
        if question_id != pending.question_id:
            raise AnswerError("交互失败回调与当前待答问题不匹配。")
        if presentation_id != expected.get("presentation_id"):
            raise AnswerError("交互失败回调属于过期或不匹配的展示。")
        if tool_name != expected.get("tool_name"):
            raise AnswerError("交互失败回调的工具名与当前展示不匹配。")
        failure = {
            "native_status": "failed",
            "fallback_reason": reason,
            "failure_detail": detail.strip(),
            "failed_at": _timestamp(),
            "question_id": question_id,
            "presentation_id": presentation_id,
            "tool_name": tool_name,
        }
        if reason == "native_tool_not_exposed":
            data["interaction_surface"] = "text_menu"
        else:
            failure["fallback_question_id"] = data["pending_question"]["question_id"]
        data["interaction_capabilities"] = failure
        data["updated_at"] = _timestamp()
        self._write(data)

    def set_question(self, question: Question) -> None:
        data = self.read()
        if data.get("pending_action"):
            raise AnswerError("待执行操作尚未回传证据，不能创建新问题。")
        pending = data.get("pending_question")
        if pending:
            raise AnswerError(f"问题 {pending['question_id']} 尚未回答，不能覆盖待答问题。")
        data["current_state"] = question.state_id
        data["pending_question"] = question.to_dict()
        data["question_instance_id"] = uuid.uuid4().hex
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
        capabilities = data.get("interaction_capabilities") or {}
        if capabilities.get("fallback_question_id") == question.question_id:
            data["interaction_capabilities"] = {
                "native_status": "pending",
                "last_failure": capabilities,
            }
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
            "adb_path",
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
            "installed_apps",
            "emotn_runtime",
            "download_confirmation",
            "verified_downloads",
            "wallpaper_asset",
            "evidence_records",
            "summary_rows",
            "finish_safety",
        }
        unknown = set(fields) - allowed
        if unknown:
            raise ValueError(f"Unsupported session fields: {', '.join(sorted(unknown))}")
        pending = data.get("pending_question")
        if pending and "current_state" in fields and fields["current_state"] != pending["state_id"]:
            raise AnswerError("待答问题存在时不能单独改变 current_state。")
        pending_action = data.get("pending_action")
        if pending_action and "current_state" in fields and fields["current_state"] != pending_action["action_id"]:
            raise AnswerError("待执行操作存在时不能单独改变 current_state。")
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
