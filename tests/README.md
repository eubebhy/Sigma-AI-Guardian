# Kiểm thử SAG Agent

`tests/` là thư mục phẳng. Mỗi feature có đúng một file tên
`test_<feature>.py`; xem tên các file này để biết feature đang có test.

## Chạy test

Chạy toàn bộ test an toàn:

```bash
./.pyvenv/bin/python tests/tester.py
```

Chạy một feature:

```bash
./.pyvenv/bin/python tests/test_browser.py
./.pyvenv/bin/python tests/test_browser.py fake smoke
./.pyvenv/bin/python tests/test_browser.py --info
```

`fake`, `mock` và `smoke` chạy mặc định. Pass không in gì và trả exit code `0`.
Khi lỗi, runner chỉ in dòng sau rồi trả exit code `1`:

```text
[web_blocker][fake] domain không được thêm vào hosts tạm
```

Một test gắn nhiều safe mode chỉ chạy một lần trong mỗi invocation; runner dùng mode
đầu tiên của test nằm trong mode caller chọn.

## Mode

- `fake`: thay dependency hệ điều hành bằng implementation giả.
- `mock`: kiểm tra dependency được gọi đúng.
- `smoke`: gọi luồng public API chính nhưng không tạo side effect hệ thống.
- `real`: gọi dependency hoặc desktop thật. Chỉ chạy trực tiếp từng feature, có output
  quan sát được và không được gọi bởi `tester.py`:

  ```bash
  ./.pyvenv/bin/python tests/test_screen_capture.py real benchmark 3 1.0
  ```

Không chạy `real` trong workflow mặc định. Nó có thể mở browser, sửa hosts, đọc màn
hình, đọc/phát input hoặc khóa desktop.

## Real mode và `--info`

Trước khi chạy real mode, luôn đọc hướng dẫn của đúng feature:

```bash
./.pyvenv/bin/python tests/test_classifier.py --info
./.pyvenv/bin/python tests/test_input_controller.py --info
./.pyvenv/bin/python tests/test_key_listener.py --info
```

`--info` mô tả command, quyền cần có, side effect, cách dừng và cleanup. Các real
command hiện có:

```bash
# Classifier: kiểm tra text hoặc corpus thật, có PASS/FAIL/summary.
./.pyvenv/bin/python tests/test_classifier.py real text "rule 34" --engine rule --strict-level strict
./.pyvenv/bin/python tests/test_classifier.py real corpus gore 20 strict --engine main --order sequential

# Agent: tạo runtime platform hiện tại và in status thật.
./.pyvenv/bin/python tests/test_agent.py real status

# Keylogger: ghi virtual buffer từ keyboard tự nguyện, dừng bằng Ctrl+C.
sudo ./.pyvenv/bin/python tests/test_keylogger.py real listen

# Process guard: fixture an toàn hoặc kill exact-name đã xác nhận.
./.pyvenv/bin/python tests/test_process_guard.py real fixture
./.pyvenv/bin/python tests/test_process_guard.py real kill PROCESS_NAME --confirm

# Input Linux/Xorg: phát input hoặc ghi event đến khi Ctrl+C.
sudo ./.pyvenv/bin/python tests/test_input_controller.py real control --move-to 500 300 --click left
sudo ./.pyvenv/bin/python tests/test_key_listener.py real logger --kb --mouse
# Lệnh logger cũ vẫn được chuyển tiếp để tương thích command manual đã công bố.
sudo ./.pyvenv/bin/python tests/test_input_controller.py real logger --kb --mouse

# Hosts: automatic luôn cleanup; block persistent cần xác nhận rõ.
sudo ./.pyvenv/bin/python tests/test_web_blocker.py real automatic https://pornhub.com
sudo ./.pyvenv/bin/python tests/test_web_blocker.py real block --keep-changes
sudo ./.pyvenv/bin/python tests/test_web_blocker.py real unblock

# Desktop.
./.pyvenv/bin/python tests/test_screen_capture.py real benchmark 3 1.0
./.pyvenv/bin/python tests/test_screen_locker.py real lock 3 15
./.pyvenv/bin/python tests/test_window_tracker.py real guard 1.0
./.pyvenv/bin/python tests/test_browser.py real open https://example.com
```

Real command trả exit `0` khi hoàn tất, `1` khi action/check fail và `2` khi command,
quyền hoặc prerequisite không hợp lệ. Hành vi `Ctrl+C` được mô tả trong `--info` của
từng feature: benchmark/browser trả `130`, còn logger/guard dừng clean và trả `0`.

## `unittest`

`unittest` là thư viện test có sẵn của Python. Một class kế thừa
`unittest.TestCase` chứa method tên `test_*`; method dùng assertion để kiểm tra kết
quả. `setUp()` và `tearDown()` dùng để chuẩn bị, cleanup state cho từng test.

`tester.py` dùng `unittest` để nạp các file `test_*.py`, kiểm tra chúng có entry point
CLI chung, sau đó lọc test theo mode và chuẩn hóa output. Không cần gọi `unittest
discover` trực tiếp.

Tài liệu chuẩn của Python:

- [`unittest`](https://docs.python.org/3/library/unittest.html)
- [`unittest.mock`](https://docs.python.org/3/library/unittest.mock.html)

## Chọn loại test

| Khi cần kiểm tra | Dùng mode | Cách làm |
| --- | --- | --- |
| Logic khi dependency không có thật | `fake` | Tạo object giả có method cần dùng và lưu dữ liệu lời gọi. |
| Feature gọi dependency đúng tham số/số lần | `mock` | Dùng `unittest.mock.patch()` rồi kiểm tra `assert_called_once_with()`. |
| Luồng public API chính chạy an toàn | `smoke` | Gọi public API với fake hoặc temporary path. |
| Tích hợp hệ điều hành/dependency thật | `real` | Chỉ chạy chủ đích trên máy test; cleanup trong `finally` hoặc `tearDown()`. |

Mỗi test method gắn `@test_modes(...)`. Không gắn decorator thì runner xem nó là
`fake`. Một test có thể thuộc nhiều mode, ví dụ `@test_modes("fake", "smoke")`.

Không đưa browser thật, hosts thật, input thật, desktop lock hoặc process thật vào
`fake`, `mock`, `smoke`.

## Ví dụ hoàn chỉnh

```python
"""Kiểm tra ví dụ feature bằng fake và smoke."""

from __future__ import annotations

import sys
import unittest

from test_support import add_source_path, run_module, test_modes

add_source_path()

from device_controler import example_feature


class _FakeBrowser:
    def __init__(self) -> None:
        self.urls: list[str] = []

    def open(self, url: str) -> bool:
        self.urls.append(url)
        return True


class ExampleFeatureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.browser = _FakeBrowser()

    def tearDown(self) -> None:
        self.browser.urls.clear()

    @test_modes("fake", "smoke")
    def test_open_url_uses_browser(self) -> None:
        result = example_feature.open_url("https://example.com", self.browser)

        self.assertTrue(result)
        self.assertEqual(self.browser.urls, ["https://example.com"])


if __name__ == "__main__":
    raise SystemExit(run_module(sys.modules[__name__]))
```

- `_FakeBrowser` thay dependency thật nên test không mở browser.
- `setUp()` tạo state mới trước mỗi test.
- `tearDown()` cleanup state, kể cả khi assertion fail.
- `assertTrue()` và `assertEqual()` làm test fail khi kết quả sai.
- Khi cần mock thay vì fake, dùng `patch()`:

  ```python
  from unittest.mock import patch

  with patch.object(service, "send", return_value=True) as send:
      feature.run()
  send.assert_called_once_with("expected value")
  ```

Ví dụ chỉ minh họa cấu trúc; thay `example_feature` bằng public API thật của feature.

## Thêm test mới

1. Tạo một file `test_<feature>.py`; không tạo thư mục con.
2. Import `add_source_path`, `run_module`, `test_modes` từ `test_support`.
3. Gắn `@test_modes("fake")`, `@test_modes("mock")` hoặc
   `@test_modes("smoke")` cho từng safe test method. Real command không chạy method
   có decorator; nó gọi hàm module-level `run_real(arguments)` trực tiếp.
4. Test mặc định phải dùng fake/mock hoặc temporary path, không thao tác desktop,
   input device, process hoặc system hosts thật.
5. Thêm entry point:

   ```python
   if __name__ == "__main__":
       raise SystemExit(run_module(sys.modules[__name__]))
   ```

6. CLI chung nhận safe mode positional hoặc `real [feature arguments ...]`. `--info`
   phải mô tả đầy đủ real command, prerequisite, side effect và cleanup của feature.
7. Chạy file đó, runner tổng và Pyright:

   ```bash
   ./.pyvenv/bin/python tests/test_<feature>.py
   ./.pyvenv/bin/python tests/tester.py
   scripts/clean_pyright_check.sh tests
   ```

Nếu thiếu module docstring, import `run_module` chuẩn hoặc entry point chuẩn, runner
tổng dừng trước khi chạy test đó và in lỗi `[feature][cli] ...`.
