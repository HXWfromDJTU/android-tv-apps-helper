from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .adb import AdbError, AdbRunner, find_adb
from .apk import ApkError, approve_plan, create_install_plan, inspect_apk, install_approved
from .catalog import CatalogError, eligible_downloads, load_catalog, validate_catalog
from .questions import AnswerError, Question
from .session import SessionStore


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
