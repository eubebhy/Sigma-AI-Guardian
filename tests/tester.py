"""Runner hàng loạt cho mọi file ``tests/test_*.py``.

File path: ``tests/tester.py``.
Input: safe mode positional ``fake mock smoke`` hoặc ``--help``.
Output: im lặng và exit code 0 khi pass; lỗi in một dòng và exit code 1.
Nguyên lý: tự nạp mọi test feature phẳng, bỏ qua file hỗ trợ này. Lệnh real chỉ
được chạy trực tiếp: ``test_<feature>.py real [feature arguments ...]``.
"""

from __future__ import annotations

from pathlib import Path
import sys

from test_support import parse_modes, run_files


TEST_DIRECTORY = Path(__file__).resolve().parent
EXCLUDED_FILES = {"test_support.py"}


def _test_files() -> list[Path]:
    return [
        file_path
        for file_path in TEST_DIRECTORY.glob("test_*.py")
        if file_path.name not in EXCLUDED_FILES
    ]


def main(arguments: list[str] | None = None) -> int:
    """Chạy toàn bộ test feature ở thư mục ``tests``."""

    modes = parse_modes(arguments, __doc__)
    return run_files(_test_files(), modes)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
