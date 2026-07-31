# pyright: reportPrivateUsage=false
"""Kiểm thử tự động cho content classifier.

File path: ``tests/test_classifier.py``.
Input: các case phẳng trong ``tests/test_classifier_cases.json`` và corpus quality
gate ``tests/test_classifier_*.txt``.
Output: runner trả exit code 1 khi case tự động thất bại.
Nguyên lý: case mặc định chỉ gọi clean text và rule-based engine; mode ``real corpus``
chạy đúng số case caller truyền. Dùng count ``1000000`` để chạy toàn bộ corpus.

Ví dụ real dùng bởi ``--help``:
``./.pyvenv/bin/python tests/test_classifier.py real text "rule 34" --engine rule
--strict-level strict``
``./.pyvenv/bin/python tests/test_classifier.py real corpus all 10 mid --engine main
--order sequential``
Toàn bộ corpus: ``./.pyvenv/bin/python tests/test_classifier.py real corpus all
1000000 mid --engine main --order sequential``.
"""

from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
import importlib
from io import StringIO
import json
from pathlib import Path
import random
import sys
import time
import traceback
from collections.abc import Callable, Sequence
from typing import Literal, NoReturn, NotRequired, TypeAlias, TypedDict, cast
import unittest
from unittest.mock import patch

from test_support import add_source_path, run_module, test_modes


CASE_FILE = Path(__file__).with_name("test_classifier_cases.json")
STRICT_LEVELS = ("xlow", "low", "mid", "strict", "xstrict")
THEMES = ("game", "porn", "gore", "unknown")

add_source_path()

from content_classifier import content_classifier
from content_classifier.clean_text import clean_text
from content_classifier.local.ai_assistant import LocalAI
from content_classifier.rule_based import rule_based_classifier
from content_classifier.tags import ContentCategory
from content_classifier.types import StrictLevel


EngineName: TypeAlias = Literal["main", "rule", "local", "cloud"]
Classifier: TypeAlias = Callable[[str, StrictLevel], ContentCategory]


QUALITY_CASE_FILES = {
    ContentCategory.Game: Path(__file__).with_name("test_classifier_game.txt"),
    ContentCategory.Pornography: Path(__file__).with_name("test_classifier_porn.txt"),
    ContentCategory.Gore: Path(__file__).with_name("test_classifier_gore.txt"),
    ContentCategory.Unknown: Path(__file__).with_name("test_classifier_unknown.txt"),
}


class _RealArgumentParser(argparse.ArgumentParser):
    """Parser real trả lỗi cho caller thay vì kết thúc safe test process."""

    def error(self, message: str) -> NoReturn:
        raise ValueError(message)


def _create_real_parser() -> argparse.ArgumentParser:
    parser = _RealArgumentParser(add_help=False)
    commands = parser.add_subparsers(dest="command", required=True)
    text = commands.add_parser("text", add_help=False)
    text.add_argument("text")
    text.add_argument(
        "--engine",
        choices=("main", "rule", "local", "cloud"),
        default="main",
    )
    text.add_argument("--strict-level", choices=STRICT_LEVELS, default="mid")
    corpus = commands.add_parser("corpus", add_help=False)
    corpus.add_argument("theme", choices=("all", *THEMES))
    corpus.add_argument("count", type=int)
    corpus.add_argument("strict_level", choices=STRICT_LEVELS)
    corpus.add_argument(
        "--engine",
        choices=("main", "rule", "local", "cloud"),
        default="main",
    )
    corpus.add_argument("--order", choices=("sequential", "random"), default="sequential")
    return parser


def _parse_real_arguments(arguments: Sequence[str]) -> argparse.Namespace | None:
    """Đọc command real, trả ``None`` khi input không hợp lệ."""

    try:
        command = _create_real_parser().parse_args(arguments)
    except (argparse.ArgumentError, ValueError):
        return None
    if command.command == "corpus" and command.count < 0:
        return None
    return command


class ClassifierCase(TypedDict):
    """Một case phẳng cho một target classifier."""

    target: str
    input: str
    expected: str
    strict_level: NotRequired[str]


def _load_cases(target: str) -> list[ClassifierCase]:
    raw_cases = cast(
        list[ClassifierCase],
        json.loads(CASE_FILE.read_text(encoding="utf-8")),
    )
    return [case for case in raw_cases if case["target"] == target]


def _load_quality_cases(case_file: Path) -> list[str]:
    return [
        line.partition("#")[0].strip()
        for line in case_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _get_engine(engine: EngineName) -> tuple[str, Classifier] | None:
    """Trả classifier được yêu cầu, hoặc ``None`` khi backend chưa có."""

    if engine == "main":
        return "main", content_classifier
    if engine == "rule":
        return "rule", rule_based_classifier
    if engine == "local":
        try:
            from content_classifier.local import local_ai_classifier
        except ModuleNotFoundError:
            return None
        return "local", local_ai_classifier
    try:
        cloud_module = importlib.import_module("content_classifier.cloud")
    except ModuleNotFoundError:
        return None
    cloud_classifier = getattr(cloud_module, "cloud_ai_classifier", None)
    if not isinstance(cloud_classifier, Callable):
        return None
    return "cloud", cast(Classifier, cloud_classifier)


def _selected_quality_cases(
    theme: str,
    count: int,
    order: str,
) -> list[tuple[str, ContentCategory, str]]:
    selected: list[tuple[str, ContentCategory, str]] = []
    for expected, case_file in QUALITY_CASE_FILES.items():
        case_theme = case_file.stem.removeprefix("test_classifier_")
        if theme not in ("all", case_theme):
            continue
        cases = _load_quality_cases(case_file)
        if order == "random":
            cases = random.sample(cases, min(count, len(cases)))
        else:
            cases = cases[:count]
        selected.extend((text, expected, case_theme) for text in cases)
    return selected


def _run_corpus(
    engine_name: str,
    classifier: Classifier,
    cases: list[tuple[str, ContentCategory, str]],
    strict_level: StrictLevel,
) -> int:
    started = time.monotonic()
    passed = 0
    print(f"=== {engine_name} | strict={strict_level} ===")
    for text, expected, theme in cases:
        try:
            actual = classifier(text, strict_level)
        except Exception as error:
            print(f"[FAIL][{theme}] {text} | error={error}")
            traceback.print_exc()
            print(f"Summary: {passed}/{len(cases)} passed, {len(cases) - passed} failed")
            print(f"Elapsed: {time.monotonic() - started:.3f}s")
            return 1
        is_passed = actual == expected
        if is_passed:
            passed += 1
        status = "PASS" if is_passed else "FAIL"
        print(f"[{status}][{theme}] {text} | expected={expected.name} got={actual.name}")
    failed = len(cases) - passed
    print(f"Summary: {passed}/{len(cases)} passed, {failed} failed")
    print(f"Elapsed: {time.monotonic() - started:.3f}s")
    return 0 if failed == 0 else 1


def run_real(arguments: Sequence[str]) -> int:
    """Chạy CLI classifier có chủ đích, không được gọi bởi safe suite."""

    command = _parse_real_arguments(arguments)
    if command is None:
        print("Invalid real command", file=sys.stderr)
        return 2
    engine = cast(EngineName, command.engine)
    selected_engine = _get_engine(engine)
    if selected_engine is None:
        print(f"Engine unavailable: {engine}", file=sys.stderr)
        return 2
    engine_name, classifier = selected_engine
    strict_level = cast(StrictLevel, command.strict_level)
    if command.command == "text":
        started = time.monotonic()
        try:
            result = classifier(command.text, strict_level)
        except Exception as error:
            print(f"Action failed: {error}", file=sys.stderr)
            traceback.print_exc()
            return 1
        print(f"=== {engine_name} | strict={strict_level} ===")
        print(f"Input: {command.text}")
        print(f"Result: {result.name}")
        print(f"Elapsed: {time.monotonic() - started:.3f}s")
        return 0
    try:
        cases = _selected_quality_cases(command.theme, command.count, command.order)
    except OSError as error:
        print(f"Action failed: {error}", file=sys.stderr)
        traceback.print_exc()
        return 1
    return _run_corpus(engine_name, classifier, cases, strict_level)


class ClassifierTests(unittest.TestCase):
    @test_modes("fake")
    def test_local_ai_close_joins_idle_monitor(self) -> None:
        ai = LocalAI("missing-model.pkl")

        ai.close()

        self.assertFalse(ai._monitor_thread.is_alive())

    """Hồi quy an toàn cho các thành phần classifier không gọi model."""

    @test_modes("fake", "mock", "smoke")
    def test_clean_text_cases(self) -> None:
        for case in _load_cases("clean_text"):
            with self.subTest(input=case["input"]):
                self.assertEqual(clean_text(case["input"]), case["expected"])

    @test_modes("fake", "mock", "smoke")
    def test_rule_based_cases(self) -> None:
        for case in _load_cases("rule_based_classifier"):
            strict_level = cast(StrictLevel, case.get("strict_level", "mid"))
            expected = ContentCategory[case["expected"]]
            with self.subTest(input=case["input"], strict_level=strict_level):
                self.assertEqual(rule_based_classifier(case["input"], strict_level), expected)

    @test_modes("real")
    def test_main_classifier_quality_gate(self) -> None:
        """Kiểm tra mọi case không phải comment trong corpus bằng classifier chính."""

        for expected, case_file in QUALITY_CASE_FILES.items():
            cases = _load_quality_cases(case_file)
            for text in cases:
                with self.subTest(category=expected.name, input=text):
                    self.assertEqual(content_classifier(text), expected)


class RealClassifierCommandTests(unittest.TestCase):
    """Kiểm tra parser và runner real bằng classifier giả."""

    def test_parse_real_text_command(self) -> None:
        command = _parse_real_arguments(
            ("text", "example text", "--engine", "rule", "--strict-level", "strict"),
        )

        self.assertIsNotNone(command)
        assert command is not None
        self.assertEqual(command.command, "text")
        self.assertEqual(command.text, "example text")
        self.assertEqual(command.engine, "rule")
        self.assertEqual(command.strict_level, "strict")

    def test_run_real_text_uses_selected_engine(self) -> None:
        calls: list[tuple[str, StrictLevel]] = []

        def fake_classifier(text: str, strict_level: StrictLevel) -> ContentCategory:
            calls.append((text, strict_level))
            return ContentCategory.Unknown

        with patch(
            __name__ + "._get_engine",
            return_value=("rule", fake_classifier),
        ), redirect_stdout(StringIO()):
            result = run_real(("text", "safe text", "--engine", "rule"))

        self.assertEqual(result, 0)
        self.assertEqual(calls, [("safe text", "mid")])

    def test_run_real_invalid_command_returns_two(self) -> None:
        with redirect_stderr(StringIO()):
            result = run_real(("corpus", "game", "bad", "mid"))
        self.assertEqual(result, 2)


if __name__ == "__main__":
    raise SystemExit(run_module(sys.modules[__name__]))
