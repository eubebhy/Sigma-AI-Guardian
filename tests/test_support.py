"""Hỗ trợ chung cho test SAG Agent.

File path: ``tests/test_support.py``.
Input: mode từ CLI và các ``unittest.TestCase`` có decorator ``test_modes``.
Output: exit code 0 khi mọi test pass; khi fail chỉ in feature, mode và lỗi ngắn.
Nguyên lý: runner lọc test theo mode trước khi chạy, nên test feature không cần kiểm
tra OS hay tự xử lý output.
"""

from __future__ import annotations

import argparse
import ast
import inspect
import sys
import unittest
from collections.abc import Iterable, Sequence
from pathlib import Path
from types import ModuleType
from types import TracebackType
from typing import Callable, NamedTuple, TypeAlias, TypeVar, cast


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"
DEFAULT_MODES = ("fake", "mock", "smoke")
VALID_MODES = (*DEFAULT_MODES, "real")
_TestFunction = TypeVar("_TestFunction", bound=Callable[..., object])
_ErrorInfo: TypeAlias = tuple[type[BaseException], BaseException, TracebackType]
_OptionalErrorInfo: TypeAlias = _ErrorInfo | tuple[None, None, None]
_SubTestErrorInfo: TypeAlias = _OptionalErrorInfo | None


class _RealCommand(NamedTuple):
    arguments: tuple[str, ...]


_FeatureCommand: TypeAlias = tuple[str, ...] | _RealCommand
_TEST_MODE_BY_ID: dict[str, str] = {}


def add_source_path() -> None:
    """Thêm ``src`` để test chạy trực tiếp từ project root."""

    if str(SRC_ROOT) not in sys.path:
        sys.path.insert(0, str(SRC_ROOT))


def test_modes(*modes: str) -> Callable[[_TestFunction], _TestFunction]:
    """Đánh dấu mode hợp lệ của một test method."""

    invalid_modes = set(modes).difference(VALID_MODES)
    if not modes or invalid_modes:
        raise ValueError(f"Invalid test modes: {sorted(invalid_modes)}")

    def _decorate(test: _TestFunction) -> _TestFunction:
        setattr(test, "_sag_test_modes", tuple(modes))
        return test

    return _decorate


def parse_modes(
    arguments: Sequence[str] | None = None,
    help_description: str | None = None,
) -> tuple[str, ...]:
    """Đọc safe mode của bulk runner hoặc in trợ giúp chuẩn."""

    parser = _create_parser(
        "tests/tester.py [fake|mock|smoke ...]",
        help_description or "Chạy real qua: tests/test_<feature>.py real [feature arguments ...]",
    )
    values = tuple(arguments) if arguments is not None else tuple(sys.argv[1:])
    if values == ("--help",):
        parser.parse_args(values)
    if not values:
        return DEFAULT_MODES
    invalid_modes = set(values).difference(DEFAULT_MODES)
    if invalid_modes:
        parser.error(f"bulk runner only accepts: {', '.join(DEFAULT_MODES)}")
    return values


def _create_parser(usage: str, description: str) -> argparse.ArgumentParser:
    return argparse.ArgumentParser(usage=usage, description=description)


def _parse_feature_command(
    arguments: Sequence[str] | None,
    help_description: str,
) -> _FeatureCommand:
    parser = _create_parser(
        "test_<feature>.py [fake|mock|smoke ...] | real [feature arguments ...]",
        help_description,
    )
    values = tuple(arguments) if arguments is not None else tuple(sys.argv[1:])
    if values == ("--help",):
        parser.parse_args(values)
    if not values:
        return DEFAULT_MODES
    if values[0] == "real":
        return _RealCommand(values[1:])
    invalid_modes = set(values).difference(DEFAULT_MODES)
    if invalid_modes:
        parser.error(f"safe mode must use: {', '.join(DEFAULT_MODES)}")
    return values


def _method_modes(test: unittest.TestCase) -> tuple[str, ...]:
    method = getattr(test, test._testMethodName)
    return getattr(method, "_sag_test_modes", ("fake",))


def _filter_suite(
    suite: unittest.TestSuite,
    selected_modes: tuple[str, ...],
) -> unittest.TestSuite:
    filtered = unittest.TestSuite()
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            filtered.addTest(_filter_suite(item, selected_modes))
            continue
        matching_modes = tuple(mode for mode in _method_modes(item) if mode in selected_modes)
        if matching_modes:
            _TEST_MODE_BY_ID[item.id()] = matching_modes[0]
            filtered.addTest(item)
    return filtered


def _failure_message(error: _OptionalErrorInfo) -> str:
    exception = error[1]
    if exception is None:
        return "Unknown test error"
    message = str(exception).strip()
    if message:
        return message.splitlines()[-1]
    return exception.__class__.__name__


def run_feature(feature: str, mode: str, action: Callable[[], object]) -> int:
    """Chạy action feature và chỉ in lỗi ngắn khi action thất bại."""

    try:
        action()
    except Exception as error:
        message = str(error).strip() or error.__class__.__name__
        print(f"[{feature}][{mode}] {message.splitlines()[-1]}", file=sys.stderr)
        return 1
    return 0


class _QuietResult(unittest.TestResult):
    """Chỉ lưu lỗi để in một dòng ngắn sau cùng."""

    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []

    def addError(
        self,
        test: unittest.case.TestCase,
        err: _OptionalErrorInfo,
    ) -> None:
        super().addError(test, err)
        self.messages.append(_format_failure(test, err))

    def addFailure(
        self,
        test: unittest.case.TestCase,
        err: _OptionalErrorInfo,
    ) -> None:
        super().addFailure(test, err)
        self.messages.append(_format_failure(test, err))

    def addSubTest(
        self,
        test: unittest.case.TestCase,
        subtest: unittest.case.TestCase,
        err: _SubTestErrorInfo,
    ) -> None:
        super().addSubTest(test, subtest, err)
        if err is not None and err[1] is not None:
            self.messages.append(_format_failure(test, err))


def _format_failure(
    test: unittest.case.TestCase,
    error: _OptionalErrorInfo,
) -> str:
    module_name = test.__class__.__module__.removeprefix("test_")
    mode = _TEST_MODE_BY_ID.get(test.id(), "fake")
    return f"[{module_name}][{mode}] {_failure_message(error)}"


def run_suite(suite: unittest.TestSuite, modes: tuple[str, ...]) -> int:
    """Chạy suite theo mode và chỉ in failure."""

    _TEST_MODE_BY_ID.clear()
    result = _QuietResult()
    _filter_suite(suite, modes).run(result)
    for message in result.messages:
        print(message, file=sys.stderr)
    return 0 if result.wasSuccessful() else 1


def run_module(module: ModuleType, arguments: Sequence[str] | None = None) -> int:
    """Chạy trực tiếp một file test feature."""

    help_description = inspect.getdoc(module) or "Test feature không có mô tả."
    command = _parse_feature_command(arguments, help_description)
    if isinstance(command, _RealCommand):
        return _run_real(module, command.arguments)
    suite = unittest.defaultTestLoader.loadTestsFromModule(module)
    return run_suite(suite, command)


def _run_real(module: ModuleType, arguments: tuple[str, ...]) -> int:
    handler = getattr(module, "run_real", None)
    feature = _feature_name(module)
    if not callable(handler):
        print(f"[{feature}][real][error] missing run_real handler", file=sys.stderr)
        return 1
    try:
        return cast(Callable[[Sequence[str]], int], handler)(arguments)
    except Exception as error:
        message = str(error).strip() or error.__class__.__name__
        print(f"[{feature}][real][error] {message.splitlines()[-1]}", file=sys.stderr)
        return 1


def _feature_name(module: ModuleType) -> str:
    file_name = getattr(module, "__file__", None)
    if isinstance(file_name, str):
        return Path(file_name).stem.removeprefix("test_")
    return module.__name__.removeprefix("test_")


def load_module(file_path: Path) -> ModuleType:
    """Nạp một file ``test_*.py`` độc lập để runner tổng có thể chạy."""

    import importlib.util

    specification = importlib.util.spec_from_file_location(file_path.stem, file_path)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"Cannot load test file: {file_path}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[file_path.stem] = module
    specification.loader.exec_module(module)
    return module


def run_files(file_paths: Iterable[Path], modes: tuple[str, ...]) -> int:
    """Nạp và chạy các file test feature theo thứ tự tên file."""

    combined_suite = unittest.TestSuite()
    for file_path in sorted(file_paths):
        validation_error = validate_test_file(file_path)
        if validation_error is not None:
            print(f"[{file_path.stem.removeprefix('test_')}][cli] {validation_error}", file=sys.stderr)
            return 1
        try:
            module = load_module(file_path)
        except Exception as error:
            feature_name = file_path.stem.removeprefix("test_")
            print(f"[{feature_name}][load] {error}", file=sys.stderr)
            return 1
        combined_suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
    return run_suite(combined_suite, modes)


def validate_test_file(file_path: Path) -> str | None:
    """Kiểm tra file feature giữ entry point CLI chung trước khi runner nạp nó."""

    source = file_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError as error:
        return f"syntax error: {error.msg}"
    if ast.get_docstring(tree) is None:
        return "thiếu module docstring mô tả vai trò test"
    imports_run_module = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "test_support"
        and any(alias.name == "run_module" and alias.asname is None for alias in node.names)
        for node in tree.body
    )
    if not imports_run_module:
        return "không dùng run_module của test_support"
    shadows_run_module = any(_shadows_run_module(node) for node in tree.body)
    if shadows_run_module:
        return "không được ghi đè run_module của test_support"
    for node in tree.body:
        if not isinstance(node, ast.If) or ast.unparse(node.test) != "__name__ == '__main__'":
            continue
        if _is_standard_entry_point(node):
            return None
    return "entry point phải là SystemExit(run_module(sys.modules[__name__]))"


def _is_standard_entry_point(node: ast.If) -> bool:
    if len(node.body) != 1 or node.orelse:
        return False
    statement = node.body[0]
    if not isinstance(statement, ast.Raise) or not isinstance(statement.exc, ast.Call):
        return False
    exit_call = statement.exc
    if not isinstance(exit_call.func, ast.Name) or exit_call.func.id != "SystemExit":
        return False
    if len(exit_call.args) != 1 or not isinstance(exit_call.args[0], ast.Call):
        return False
    runner_call = exit_call.args[0]
    if not isinstance(runner_call.func, ast.Name) or runner_call.func.id != "run_module":
        return False
    if len(runner_call.args) != 1 or runner_call.keywords:
        return False
    module_reference = runner_call.args[0]
    if not isinstance(module_reference, ast.Subscript):
        return False
    if not isinstance(module_reference.value, ast.Attribute):
        return False
    if not isinstance(module_reference.value.value, ast.Name):
        return False
    if module_reference.value.value.id != "sys" or module_reference.value.attr != "modules":
        return False
    return isinstance(module_reference.slice, ast.Name) and module_reference.slice.id == "__name__"


def _shadows_run_module(node: ast.stmt) -> bool:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return node.name == "run_module"
    if isinstance(node, ast.Import):
        return any(alias.asname == "run_module" for alias in node.names)
    if isinstance(node, ast.ImportFrom) and node.module != "test_support":
        return any(
            alias.name == "run_module" or alias.asname == "run_module"
            for alias in node.names
        )
    if isinstance(node, ast.Assign):
        return any(isinstance(target, ast.Name) and target.id == "run_module" for target in node.targets)
    return isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "run_module"
