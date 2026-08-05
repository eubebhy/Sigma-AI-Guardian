# Kiểm thử SAG Agent

## DESCRIPTION

`tests/` là thư mục phẳng. `tests/tester.py` nạp `test_*.py` và chỉ chạy các mode
an toàn mặc định. Test tự động không được đọc hosts, process, input, desktop hoặc
browser thật.

## COMMANDS

```bash
# Toàn bộ safe suite.
./.pyvenv/bin/python tests/tester.py

# Một feature và metadata manual command của nó.
./.pyvenv/bin/python tests/test_browser.py
./.pyvenv/bin/python tests/test_browser.py --help
```

`fake`, `mock` và `smoke` là safe mode. Runner trả `0` khi pass và `1` khi fail.
`real` chỉ chạy trực tiếp một file test; đọc `--help` trước vì command có thể thay đổi
hệ thống.

## LỘ TRÌNH ĐỌC

Đọc theo thứ tự này trước khi viết test mới:

1. Feature cần test, ví dụ `src/device_controller/browser_tab/__init__.py`.
2. Contract feature dùng trong `src/agent/contracts.py`.
3. Adapter được runtime cung cấp trong `src/agent/platform/__init__.py`.
4. Test feature tương tự, ví dụ `tests/test_browser.py` hoặc
   `tests/test_screen_locker.py`.
5. `tests/test_support.py` để hiểu command, mode và runner.

Luồng cần giữ trong test:

```text
Feature
    ↓ nhận contract hoặc PlatformServices
Fake / Mock adapter
    ↓
unittest assertion
```

Test feature không import Linux/Windows adapter khi chỉ cần kiểm tra logic chung.

## UNITTEST CƠ BẢN

Mỗi test nằm trong một `unittest.TestCase`. Method bắt đầu bằng `test_` được runner
phát hiện tự động. Dùng bố cục Arrange – Act – Assert:

```python
import unittest


class Counter:
    def __init__(self) -> None:
        self.value = 0

    def increase(self) -> None:
        self.value += 1


class CounterTests(unittest.TestCase):
    def test_increase_adds_one(self) -> None:
        # Arrange
        counter = Counter()

        # Act
        counter.increase()

        # Assert
        self.assertEqual(counter.value, 1)
```

Lưu đoạn trên vào file Python rồi chạy:

```bash
./.pyvenv/bin/python -m unittest <tên_module>
```

Assertion dùng nhiều nhất:

```python
self.assertEqual(actual, expected)
self.assertTrue(condition)
self.assertFalse(condition)
self.assertIsNone(value)

with self.assertRaisesRegex(ValueError, "invalid"):
    parse_value("bad")
```

`assertRaisesRegex` kiểm tra cả loại lỗi và message. Không bắt exception rồi bỏ qua,
vì test sẽ che mất behavior lỗi cần bảo vệ.

## FAKE TEST

Fake là implementation nhỏ của contract. Nó thay OS/API thật bằng state có thể quan
sát. Dùng fake khi feature gọi dependency nhiều lần hoặc dependency có lifecycle.

```python
class _FakeCursorOperations:
    def __init__(self) -> None:
        self.events: list[str] = []

    def hide_cursor(self) -> None:
        self.events.append("hide")

    def show_cursor(self) -> None:
        self.events.append("show")


class CursorFeature:
    def __init__(self, cursor: _FakeCursorOperations) -> None:
        self._cursor = cursor

    def lock_then_unlock(self) -> None:
        self._cursor.hide_cursor()
        self._cursor.show_cursor()


class CursorFeatureTests(unittest.TestCase):
    def test_lock_then_unlock_uses_cursor_lifecycle(self) -> None:
        cursor = _FakeCursorOperations()

        CursorFeature(cursor).lock_then_unlock()

        self.assertEqual(cursor.events, ["hide", "show"])
```

Cơ chế:

```text
Feature gọi CursorOperations
→ fake lưu lời gọi vào events
→ assertion kiểm tra lifecycle
```

Project dùng mẫu này trong `tests/test_browser.py`, `tests/test_process_guard.py` và
`tests/test_screen_locker.py`. Fake test không được gọi desktop, input, browser,
hosts hay process thật.

## MOCK TEST VÀ PATCH

Mock phù hợp khi chỉ cần kiểm tra dependency có được gọi đúng input hay không. Dùng
`patch.object()` để thay reference đúng nơi production code đang lookup dependency.
Khi kết thúc `with`, reference cũ tự được restore.

```python
from unittest.mock import patch


class Launcher:
    def open(self, url: str) -> bool:
        return self._run(url)

    def _run(self, url: str) -> bool:
        raise NotImplementedError


class LauncherTests(unittest.TestCase):
    def test_open_calls_runner_with_url(self) -> None:
        launcher = Launcher()

        with patch.object(launcher, "_run", return_value=True) as run:
            result = launcher.open("https://example.com")

        self.assertTrue(result)
        run.assert_called_once_with("https://example.com")
```

Không patch adapter ở nơi adapter được định nghĩa nếu feature đã import reference đó
ở module khác. Patch nơi feature thực sự đọc reference.

## SETUP, TEARDOWN VÀ CLEANUP

`setUp()` chạy trước mỗi test; `tearDown()` chạy sau mỗi test, kể cả khi assertion
fail. Dùng chúng để reset module state, `sys.modules`, Event hoặc thread fake.

```python
class StateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.values: list[str] = []

    def tearDown(self) -> None:
        self.values.clear()

    def test_adds_value(self) -> None:
        self.values.append("value")

        self.assertEqual(self.values, ["value"])
```

Không để test sau phụ thuộc global state do test trước tạo ra. Với patch, ưu tiên
`with patch.object(...)`; với module cache, dùng `patch.dict(sys.modules, ...)`.

## TEST MODE

| Mode | Mục tiêu | Resource thật |
| --- | --- | --- |
| `fake` | Logic và lifecycle với fake stateful | Không |
| `mock` | Interaction, argument và error path với mock/patch | Không |
| `smoke` | Public API, import an toàn và flow cơ bản | Không |
| `real` | Desktop/OS API, permission và integration thật | Có, chỉ manual |

Đánh dấu safe test bằng `test_modes`:

```python
from test_support import test_modes


@test_modes("fake")
def test_feature_uses_fake(self) -> None:
    ...


@test_modes("mock", "smoke")
def test_public_api_exists(self) -> None:
    ...
```

`tests/tester.py` chỉ chạy `fake`, `mock`, `smoke`:

```bash
./.pyvenv/bin/python tests/tester.py
./.pyvenv/bin/python tests/test_browser.py fake
./.pyvenv/bin/python tests/test_browser.py mock smoke
```

`real` không chạy unittest suite. Runner gọi riêng `run_real(arguments)` trong file
test, nên real command phải được test bằng fake/mock ở safe mode.

## PLATFORM-SPECIFIC TEST

Linux test chỉ dùng resource Linux; Windows test chỉ dùng resource Windows. Dùng
decorator chuẩn `unittest.skipUnless()` cho test chỉ thuộc một OS:

```python
import sys
import unittest


@unittest.skipUnless(sys.platform.startswith("linux"), "Linux only")
def test_linux_adapter(self) -> None:
    from agent.platform.linux.processes import LinuxProcessOperations

    self.assertIsNotNone(LinuxProcessOperations())
```

Import native adapter bên trong test platform tương ứng. Khi chạy Linux,
Windows-only test bị skip trước khi thân method chạy; trên Windows thì ngược lại.

```text
Linux tester.py   → Linux test chạy, Windows test skip
Windows tester.py → Windows test chạy, Linux test skip
```

Cross-platform test chỉ dùng contract, `PlatformServices` fake hoặc public API; nó
không gọi X11, evdev, UInput, WinAPI, browser hay input thật.

## REAL MODE

```bash
# Mở browser thật.
./.pyvenv/bin/python tests/test_browser.py real open https://example.com

# Sửa hosts thật; automatic cleanup, block giữ policy khi được xác nhận.
sudo ./.pyvenv/bin/python tests/test_web_blocker.py real automatic https://example.com
```

Real mode có thể mở browser, sửa hosts, đọc/phát input, đọc màn hình hoặc khóa desktop.
Chạy trên session test có chủ đích; không gọi từ CI hoặc safe suite.

Ví dụ real screen locker trên Linux:

```bash
sudo ./.pyvenv/bin/python tests/test_screen_locker.py real lock 0 5
```

Đọc `--help` trước khi chạy. Module docstring của real test phải mô tả prerequisite,
side effect, cách dừng và cleanup behavior.

## TEST CONTRACT

- Test public API/contract dùng fake deterministic.
- Test side effect hoặc race dùng fake, temporary path, `Event` hoặc barrier; không
  dùng `sleep` dài hay OS thật.
- `real` command phải mô tả prerequisite, side effect, cách dừng và cleanup trong
  `--help`.
- File test mới tên `test_<feature>.py`, dùng `add_source_path`, `run_module` và
  `test_modes` từ `test_support`.

## TEMPLATE TEST MỚI

Tạo `tests/test_<feature>.py` theo template sau. Đây là file test hoàn chỉnh, chạy
được với `./.pyvenv/bin/python tests/test_<feature>.py fake` sau khi thay feature và
fake dependency đúng với code thực.

```python
"""Kiểm tra <feature> bằng fake dependency."""

from __future__ import annotations

import sys
import unittest

from test_support import add_source_path, run_module, test_modes


add_source_path()


class _FakeOperations:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def run(self) -> None:
        self.calls.append("run")


class FeatureTests(unittest.TestCase):
    @test_modes("fake")
    def test_feature_calls_operation(self) -> None:
        operations = _FakeOperations()

        # Thay dòng này bằng public API feature thật.
        operations.run()

        self.assertEqual(operations.calls, ["run"])


if __name__ == "__main__":
    raise SystemExit(run_module(sys.modules[__name__]))
```

Checklist trước khi hoàn thành test mới:

```text
1. Test public behavior trước private helper.
2. Inject fake cho OS/platform dependency.
3. Chọn fake, mock hoặc smoke; không dùng OS thật.
4. Dùng skipUnless cho adapter chỉ thuộc Linux hoặc Windows.
5. Restore mọi global state và resource fake.
6. Chạy file test riêng, sau đó chạy tests/tester.py.
```

## TYPE CHECK

```bash
scripts/clean_pyright_check.sh tests
```

Script nhận đúng một target.
