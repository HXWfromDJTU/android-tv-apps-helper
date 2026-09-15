from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .adb import AdbError, AdbRunner, find_adb
from .apk import ApkError, approve_plan, create_install_plan, inspect_apk, install_approved
from .catalog import CatalogError, eligible_downloads, load_catalog, validate_catalog
from .compatibility import match_or_default
from .guides import match_device_guide
from .questions import AnswerError, Question
from .report import render_final_report
from .precheck import run_passive_precheck
from .session import SessionStore
from .update import UpdateStateStore, fetch_latest_stable_release
from .workflow import WorkflowEngine, render_question


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tv-helper")
    subcommands = parser.add_subparsers(dest="command", required=True)

    init = subcommands.add_parser("init-session")
    init.add_argument("session", type=Path)
    init.add_argument("--surface", required=True, choices=("structured_form", "text_menu"))
    init.add_argument(
        "--host-platform",
        default="codex",
        choices=("claude", "codex", "workbuddy", "doubao-work"),
    )
    init.add_argument(
        "--execution-context",
        default="local_computer",
        choices=("local_computer", "cloud_computer"),
    )
    init.add_argument("--skill-root")
    init.add_argument("--python-command", default="python3")

    show = subcommands.add_parser("show-session")
    show.add_argument("session", type=Path)

    set_question = subcommands.add_parser("set-question")
    set_question.add_argument("session", type=Path)
    set_question.add_argument("--question", required=True, type=Path)

    answer = subcommands.add_parser("answer")
    answer.add_argument("session", type=Path)
    answer.add_argument("--question-id", required=True)
    answer.add_argument("--value", required=True)

    workflow_start = subcommands.add_parser("workflow-start")
    workflow_start.add_argument("session", type=Path)
    workflow_start.add_argument("--precheck", required=True, type=Path)

    workflow_answer = subcommands.add_parser("workflow-answer")
    workflow_answer.add_argument("session", type=Path)
    workflow_answer.add_argument("--question-id", required=True)
    workflow_answer.add_argument("--value", required=True)

    workflow_entry = subcommands.add_parser("workflow-entry")
    workflow_entry.add_argument("session", type=Path)
    workflow_entry.add_argument("--installed-version", required=True)
    workflow_entry.add_argument("--precheck", type=Path)
    workflow_entry.add_argument("--latest-release", type=Path)
    workflow_entry.add_argument("--update-state", type=Path)
    workflow_entry.add_argument("--adb", type=Path)

    workflow_action = subcommands.add_parser("workflow-action-result")
    workflow_action.add_argument("session", type=Path)
    workflow_action.add_argument("--action-id", required=True)
    workflow_action.add_argument(
        "--status", required=True, choices=("completed", "failed", "attention")
    )
    workflow_action.add_argument("--evidence", required=True, type=Path)

    prepare_device = subcommands.add_parser("prepare-device-context")
    prepare_device.add_argument("session", type=Path)
    prepare_device.add_argument("--identity", required=True, type=Path)
    prepare_device.add_argument("--guides", required=True, type=Path)
    prepare_device.add_argument("--compatibility", required=True, type=Path)

    final_report = subcommands.add_parser("final-report")
    final_report.add_argument("session", type=Path)
    final_report.add_argument("--out", type=Path)

    catalog = subcommands.add_parser("catalog")
    catalog.add_argument("--catalog", required=True, type=Path)
    catalog.add_argument("--eligible", action="store_true")

    adb_list = subcommands.add_parser("adb-list")
    adb_list.add_argument("--adb", type=Path)

    adb_inspect = subcommands.add_parser("adb-inspect")
    adb_inspect.add_argument("--adb", type=Path)
    adb_inspect.add_argument("--serial", required=True)
    adb_inspect.add_argument("--state", required=True)

    apk_inspect = subcommands.add_parser("apk-inspect")
    apk_inspect.add_argument("apk", type=Path)
    apk_inspect.add_argument("--sha256")

    plan_install = subcommands.add_parser("plan-install")
    plan_install.add_argument("session", type=Path)
    plan_install.add_argument("--app-id", required=True)
    plan_install.add_argument("--serial", required=True)
    plan_install.add_argument("--apk", required=True, type=Path)
    plan_install.add_argument("--sha256", required=True)
    plan_install.add_argument("--out", required=True, type=Path)

    approve_install = subcommands.add_parser("approve-install")
    approve_install.add_argument("session", type=Path)
    approve_install.add_argument("--plan", required=True, type=Path)
    approve_install.add_argument("--confirmation", required=True)

    install = subcommands.add_parser("install-approved")
    install.add_argument("session", type=Path)
    install.add_argument("--plan", required=True, type=Path)
    install.add_argument("--adb", type=Path)
    install.add_argument("--state", required=True)
    return parser


def _print_session(store: SessionStore) -> None:
    print(json.dumps(store.read(), ensure_ascii=False, indent=2))


def _print_json(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _read_plan(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not value.get("plan_id"):
        raise ApkError("Install plan is missing a plan_id.")
    return value


def _question_payload(question: Question | None) -> dict[str, object] | None:
    return question.to_dict() if question else None


def main(arguments: Sequence[str] | None = None) -> int:
    try:
        args = _parser().parse_args(arguments)
        if args.command == "init-session":
            store = SessionStore.create(
                args.session,
                interaction_surface=args.surface,
                host_platform=args.host_platform,
                execution_context=args.execution_context,
                skill_root=args.skill_root,
                python_command=args.python_command,
            )
            _print_session(store)
        elif args.command in {"show-session", "set-question", "answer"}:
            store = SessionStore(args.session)
            if args.command == "set-question":
                question = Question.from_dict(
                    json.loads(args.question.read_text(encoding="utf-8"))
                )
                store.set_question(question)
            elif args.command == "answer":
                store.answer(args.value, submitted_question_id=args.question_id)
            _print_session(store)
        elif args.command == "workflow-start":
            precheck = json.loads(args.precheck.read_text(encoding="utf-8"))
            if not isinstance(precheck, dict):
                raise ValueError("Precheck input must be a JSON object.")
            question = WorkflowEngine(SessionStore(args.session)).start(precheck)
            _print_json(
                {"accepted": True, "question": question.to_dict(), "rendered": render_question(question)}
            )
        elif args.command == "workflow-entry":
            if args.precheck:
                precheck = json.loads(args.precheck.read_text(encoding="utf-8"))
                if not isinstance(precheck, dict):
                    raise ValueError("Precheck input must be a JSON object.")
            else:
                precheck = run_passive_precheck(adb_path=str(args.adb) if args.adb else None)
            latest_release = None
            update_error = None
            try:
                if args.latest_release:
                    latest_release = json.loads(args.latest_release.read_text(encoding="utf-8"))
                    if not isinstance(latest_release, dict):
                        raise ValueError("Latest release fixture must be a JSON object.")
                else:
                    latest_release = fetch_latest_stable_release()
            except (OSError, ValueError) as error:
                update_error = str(error)
                precheck = {
                    **precheck,
                    "rows": [
                        *precheck.get("rows", []),
                        {
                            "status": "attention",
                            "item": "Skill 更新检查",
                            "result": "暂时无法连接 GitHub，继续使用当前版本",
                        },
                    ],
                }
            store = SessionStore(args.session)
            question = WorkflowEngine(store).enter(
                precheck,
                installed_version=args.installed_version,
                latest_release=latest_release,
                update_state_store=UpdateStateStore(
                    args.update_state,
                    platform=store.read()["host_platform"],
                ),
            )
            _print_json(
                {
                    "accepted": True,
                    "update_error": update_error,
                    "question": question.to_dict(),
                    "rendered": render_question(question),
                }
            )
        elif args.command == "workflow-answer":
            result = WorkflowEngine(SessionStore(args.session)).submit(
                args.value, question_id=args.question_id
            )
            question = result.get("question")
            payload = {
                "accepted": bool(result["accepted"]),
                "error": result.get("error"),
                "question": _question_payload(question),
                "rendered": render_question(question) if question else None,
                "action_required": result.get("action_required"),
            }
            _print_json(payload)
            if not result["accepted"]:
                return 2
        elif args.command == "workflow-action-result":
            evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
            if not isinstance(evidence, dict):
                raise ValueError("Action evidence must be a JSON object.")
            result = WorkflowEngine(SessionStore(args.session)).record_action(
                args.action_id,
                status=args.status,
                evidence=evidence,
            )
            question = result.get("question")
            _print_json(
                {
                    "accepted": bool(result["accepted"]),
                    "record": result.get("record"),
                    "question": _question_payload(question),
                    "rendered": render_question(question) if question else None,
                }
            )
            if not result["accepted"]:
                return 2
        elif args.command == "prepare-device-context":
            identity = json.loads(args.identity.read_text(encoding="utf-8"))
            guides_registry = json.loads(args.guides.read_text(encoding="utf-8"))
            compatibility_registry = json.loads(
                args.compatibility.read_text(encoding="utf-8")
            )
            if not all(
                isinstance(value, dict)
                for value in (identity, guides_registry, compatibility_registry)
            ):
                raise ValueError("Device identity and registries must be JSON objects.")
            guide = match_device_guide(identity, guides_registry.get("guides", ()))
            compatibility_match, rows = match_or_default(identity, compatibility_registry)
            SessionStore(args.session).update_fields(
                device_identity=identity,
                device_guide_match=guide,
                compatibility_matches=rows,
            )
            _print_json(
                {
                    "identity": identity,
                    "guide": guide,
                    "compatibility_match": compatibility_match,
                    "compatibility_rows": rows,
                }
            )
        elif args.command == "final-report":
            report = render_final_report(SessionStore(args.session).read())
            if args.out:
                args.out.parent.mkdir(parents=True, exist_ok=True)
                args.out.write_text(report, encoding="utf-8")
            print(report)
        elif args.command == "catalog":
            catalog = load_catalog(args.catalog)
            validate_catalog(catalog)
            _print_json(eligible_downloads(catalog) if args.eligible else catalog)
        elif args.command == "adb-list":
            runner = AdbRunner(find_adb(args.adb))
            _print_json([device.__dict__ for device in runner.list_devices()])
        elif args.command == "adb-inspect":
            runner = AdbRunner(find_adb(args.adb))
            _print_json(runner.inspect_device(args.serial, state=args.state))
        elif args.command == "apk-inspect":
            _print_json(inspect_apk(args.apk, expected_sha256=args.sha256))
        elif args.command == "plan-install":
            SessionStore(args.session).read()
            plan = create_install_plan(
                app_id=args.app_id,
                serial=args.serial,
                apk_path=args.apk,
                expected_sha256=args.sha256,
            )
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(
                json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            _print_json(plan)
        elif args.command == "approve-install":
            store = SessionStore(args.session)
            approve_plan(store, _read_plan(args.plan), confirmation=args.confirmation)
            _print_session(store)
        elif args.command == "install-approved":
            store = SessionStore(args.session)
            plan = _read_plan(args.plan)
            runner = AdbRunner(find_adb(args.adb))
            _print_json(
                {
                    "plan_id": plan["plan_id"],
                    "result": install_approved(
                        store,
                        runner,
                        plan,
                        device_state=args.state,
                    ),
                }
            )
        return 0
    except (
        AdbError,
        AnswerError,
        ApkError,
        CatalogError,
        ValueError,
        OSError,
        json.JSONDecodeError,
    ) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
