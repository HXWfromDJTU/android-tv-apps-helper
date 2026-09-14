from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .questions import AnswerError, Question
from .session import SessionStore


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tv-helper")
    subcommands = parser.add_subparsers(dest="command", required=True)

    init = subcommands.add_parser("init-session")
    init.add_argument("session", type=Path)
    init.add_argument("--surface", required=True, choices=("structured_form", "text_menu"))

    show = subcommands.add_parser("show-session")
    show.add_argument("session", type=Path)

    set_question = subcommands.add_parser("set-question")
    set_question.add_argument("session", type=Path)
    set_question.add_argument("--question", required=True, type=Path)

    answer = subcommands.add_parser("answer")
    answer.add_argument("session", type=Path)
    answer.add_argument("--question-id", required=True)
    answer.add_argument("--value", required=True)
    return parser


def _print_session(store: SessionStore) -> None:
    print(json.dumps(store.read(), ensure_ascii=False, indent=2))


def main(arguments: Sequence[str] | None = None) -> int:
    try:
        args = _parser().parse_args(arguments)
        if args.command == "init-session":
            store = SessionStore.create(args.session, interaction_surface=args.surface)
        else:
            store = SessionStore(args.session)
            if args.command == "set-question":
                question = Question.from_dict(
                    json.loads(args.question.read_text(encoding="utf-8"))
                )
                store.set_question(question)
            elif args.command == "answer":
                store.answer(args.value, submitted_question_id=args.question_id)
        _print_session(store)
        return 0
    except (AnswerError, ValueError, OSError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
