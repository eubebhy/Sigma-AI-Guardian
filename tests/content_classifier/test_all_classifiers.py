"""Test runner thu cong cho cac content classifier.

Note:
- File path:
  - Runner: `tests/content_classifier/test_all_classifiers.py`
  - Test case dir input: `tests/content_classifier/test_cases/`
  - Source dir duoc them vao `sys.path`: `src/`
- Chuan input:
  - CLI flags chon engine, strict level va cach lay sample.
  - `--custom-input` de phan loai truc tiep mot chuoi tuy chinh.
  - Moi test case la 1 dong text trong cac file `.txt`.
- Chuan output:
  - In tung dong PASS/FAIL neu case pass hoac co `--show-failures`.
  - In tong ket theo theme va tong so case o cuoi moi lan chay.

Cach code hoat dong:
- Tinh `PROJECT_ROOT` va `SRC_ROOT` tu vi tri file hien tai de project van chay
  khi duoc copy sang thu muc khac.
- Them `src/` vao `sys.path` roi import classifier package bang absolute import.
- Doc case tu `test_cases/`, map theme -> expected `ContentCategory`, sau do goi
  classifier duoc chon de so sanh ket qua thuc te voi ket qua ky vong.
"""

import argparse
import random
import sys
from pathlib import Path
from typing import Callable, Literal, TypeAlias, cast
import time

CASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CASE_DIR.parent.parent
SRC_ROOT = PROJECT_ROOT / "src"
TEST_CASE_DIR = CASE_DIR / "test_cases"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from content_classifier.tags import ContentCategory
from content_classifier.types import StrictLevel

ClassifierFunc: TypeAlias = Callable[[str, StrictLevel], ContentCategory]
TestCase: TypeAlias = tuple[str, ContentCategory, str]
DisplayMode: TypeAlias = Literal["summary", "failures", "successes", "all"]

THEME_ORDER = ("game", "porn", "gore", "unknown")
THEME_TO_EXPECTED = {
    "game": ContentCategory.Game,
    "porn": ContentCategory.Pornography,
    "gore": ContentCategory.Gore,
    "unknown": ContentCategory.Unknown,
}
MODE_CHOICES = ("all", "game", "porn", "gore")
CASE_PICK_CHOICES = ("sequential", "random")
STRICT_LEVEL_CHOICES: tuple[StrictLevel, ...] = (
    "xlow",
    "low",
    "mid",
    "strict",
    "xstrict",
)


def parse_arguments() -> tuple[argparse.Namespace, list[str]]:
    _ = parser = argparse.ArgumentParser(
        description="Tester for all content classifiers"
    )
    _ = parser.add_argument(
        "--main-classifier",
        help="Test main combined classifier",
        action="store_true",
    )
    _ = parser.add_argument(
        "-r", "--rule-based-engine", help="Test rule-based engine", action="store_true"
    )
    _ = parser.add_argument(
        "-l",
        "--local-ai-classifier",
        help="Test local AI classifier",
        action="store_true",
    )
    _ = parser.add_argument(
        "-c",
        "--cloud-ai-classifier",
        help="Test cloud AI classifier",
        action="store_true",
    )

    display_group = parser.add_mutually_exclusive_group()
    _ = display_group.add_argument(
        "-f",
        "--show-failures",
        action="store_true",
        help="Show failed test cases and failure summary lines",
    )
    _ = display_group.add_argument(
        "-s",
        "--show-successes",
        action="store_true",
        help="Show passed test cases and success summary lines",
    )
    _ = display_group.add_argument(
        "-a",
        "--show-all",
        action="store_true",
        help="Show both passed and failed test cases",
    )
    _ = parser.add_argument(
        "-m",
        "--mode",
        choices=MODE_CHOICES,
        default="all",
        help="Select which theme set to test",
    )
    _ = parser.add_argument(
        "-p",
        "--pick-mode",
        choices=CASE_PICK_CHOICES,
        default="sequential",
        help="Choose cases sequentially or randomly from each selected theme",
    )
    _ = parser.add_argument(
        "-n",
        "--sample-size",
        type=int,
        default=10,
        help="Maximum number of cases to take from each selected theme",
    )
    _ = parser.add_argument(
        "-i",
        "--custom-input",
        help="Classify this text instead of loading test cases",
    )
    _ = parser.add_argument(
        "--strict-level",
        choices=STRICT_LEVEL_CHOICES,
        default="mid",
        help="Select classifier strictness (default: mid)",
    )

    return parser.parse_known_args()


args, _ = parse_arguments()
strict_level: StrictLevel = cast(StrictLevel, args.strict_level)


def _run_custom_input(
    engine_name: str,
    classifier_func: ClassifierFunc,
    text: str,
    selected_strict_level: StrictLevel,
) -> None:
    """Phan loai va in ket qua cua mot chuoi do nguoi dung cung cap."""

    actual_tag = classifier_func(text, selected_strict_level)
    print(f"=== {engine_name} | strict={selected_strict_level} ===")
    print(f"Input: {text}")
    print(f"Result: {actual_tag.name}")


def _load_cases_from_file(
    file_path: Path, expected_tag: ContentCategory
) -> list[TestCase]:
    test_cases: list[TestCase] = []

    with file_path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            text = raw_line.split("#", 1)[0].strip()
            if not text:
                continue
            test_cases.append((text, expected_tag, file_path.stem))

    return test_cases


def _select_theme_names(mode: str) -> tuple[str, ...]:
    if mode == "all":
        return THEME_ORDER
    return (mode,)


def _sample_cases(
    cases: list[TestCase],
    sample_size: int,
    pick_mode: str,
) -> list[TestCase]:
    if sample_size < 0:
        sample_size = 0

    limit = min(sample_size, len(cases))
    if pick_mode == "random":
        return random.sample(cases, limit)

    return cases[:limit]


def load_test_cases(mode: str, sample_size: int, pick_mode: str) -> list[TestCase]:
    test_cases: list[TestCase] = []

    for theme in _select_theme_names(mode):
        file_path = TEST_CASE_DIR / f"{theme}.txt"
        expected_tag = THEME_TO_EXPECTED[theme]
        cases = _load_cases_from_file(file_path, expected_tag)
        test_cases.extend(_sample_cases(cases, sample_size, pick_mode))

    return test_cases


class BaseClassifierTest:
    def _display_mode(self) -> DisplayMode:
        if args.show_all:
            return "all"
        if args.show_successes:
            return "successes"
        if args.show_failures:
            return "failures"
        return "summary"

    def _should_print_case(self, is_passed: bool) -> bool:
        mode = self._display_mode()
        if mode == "all":
            return True
        if mode == "successes":
            return is_passed
        if mode == "failures":
            return not is_passed
        return False

    def _run_test_case(
        self,
        classifier_func: ClassifierFunc,
        text: str,
        expected_tag: ContentCategory,
        selected_strict_level: StrictLevel,
    ) -> tuple[ContentCategory, bool]:
        actual_tag = classifier_func(text, selected_strict_level)
        return actual_tag, actual_tag == expected_tag

    def _update_theme_stats(
        self,
        theme_stats: dict[str, dict[str, int]],
        theme: str,
        is_passed: bool,
    ) -> None:
        theme_stats[theme]["total"] += 1
        if is_passed:
            theme_stats[theme]["passed"] += 1
            return
        theme_stats[theme]["failed"] += 1

    def _print_case_result(
        self,
        theme: str,
        text: str,
        actual_tag: ContentCategory,
        is_passed: bool,
    ) -> None:
        if not self._should_print_case(is_passed):
            return

        status = "PASS" if is_passed else "FAIL"
        print(f"[{status}][{theme}] {text} | got={actual_tag.name}")

    def _print_summary(
        self,
        total_cases: int,
        passed_count: int,
        failed_count: int,
        theme_stats: dict[str, dict[str, int]],
    ) -> None:
        print()
        print("Summary")
        print(f"Total: {total_cases} | Passed: {passed_count} | Failed: {failed_count}")

        for theme in THEME_ORDER:
            stats = theme_stats[theme]
            print(
                f"{theme:>5}: {stats['passed']}/{stats['total']} passed, {stats['failed']} failed"
            )

    def run_classifier_test(
        self,
        engine_name: str,
        classifier_func: ClassifierFunc,
        test_cases: list[TestCase],
        selected_strict_level: StrictLevel,
    ) -> None:
        total_cases = len(test_cases)
        passed_count = 0
        failed_count = 0
        theme_stats = {
            theme: {"total": 0, "passed": 0, "failed": 0} for theme in THEME_ORDER
        }
        failed_cases: list[tuple[str, str, ContentCategory, ContentCategory]] = []

        start_time = time.time()
        print(f"=== {engine_name} | strict={selected_strict_level} ===")

        for text, expected_tag, theme in test_cases:  # Tach cho nay ra lam 1 ham
            actual_tag, is_passed = self._run_test_case(
                classifier_func,
                text,
                expected_tag,
                selected_strict_level,
            )
            self._update_theme_stats(theme_stats, theme, is_passed)
            if is_passed:
                passed_count += 1
            else:
                failed_count += 1
                failed_cases.append((theme, text, expected_tag, actual_tag))
            self._print_case_result(theme, text, actual_tag, is_passed)

        self._print_summary(total_cases, passed_count, failed_count, theme_stats)
        print(f"DONE {time.time() - start_time}")


def run_selected_tests() -> None:
    tester = BaseClassifierTest()
    test_cases = (
        []
        if args.custom_input is not None
        else load_test_cases(args.mode, args.sample_size, args.pick_mode)
    )

    if args.main_classifier or not any(
        [args.rule_based_engine, args.local_ai_classifier, args.cloud_ai_classifier]
    ):
        from content_classifier import content_classifier

        if args.custom_input is not None:
            _run_custom_input(
                "main-classifier",
                content_classifier,
                args.custom_input,
                strict_level,
            )
        else:
            tester.run_classifier_test(
                "main-classifier",
                content_classifier,
                test_cases,
                strict_level,
            )

    if args.rule_based_engine:  # Cac phan test rieng module kieu nay tao mot ham rieng de test, tranh repeat code.
        try:
            from content_classifier.rule_based import rule_based_classifier
        except ModuleNotFoundError as exc:
            print("=== rule-based-engine ===")
            print(f"TODO: rule-based engine is unavailable: {exc}")
        else:
            if args.custom_input is not None:
                _run_custom_input(
                    "rule-based-engine",
                    rule_based_classifier,
                    args.custom_input,
                    strict_level,
                )
            else:
                tester.run_classifier_test(
                    "rule-based-engine",
                    rule_based_classifier,
                    test_cases,
                    strict_level,
                )

    if args.local_ai_classifier:
        try:
            from content_classifier.local import local_ai_classifier
        except ModuleNotFoundError as exc:
            print("=== local-ai-classifier ===")
            print(f"TODO: local AI backend is unavailable: {exc}")
        else:
            if args.custom_input is not None:
                _run_custom_input(
                    "local-ai-classifier",
                    local_ai_classifier,
                    args.custom_input,
                    strict_level,
                )
            else:
                tester.run_classifier_test(
                    "local-ai-classifier",
                    local_ai_classifier,
                    test_cases,
                    strict_level,
                )

    if args.cloud_ai_classifier:
        print("=== cloud-ai-classifier ===")
        print("TODO: cloud AI backend is not wired into this test harness yet.")


if __name__ == "__main__":
    run_selected_tests()
