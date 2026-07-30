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
./.pyvenv/bin/python tests/test_browser.py --info
```

`fake`, `mock` và `smoke` là safe mode. Runner trả `0` khi pass và `1` khi fail.
`real` chỉ chạy trực tiếp một file test; đọc `--info` trước vì command có thể thay đổi
hệ thống.

## REAL MODE

```bash
# Mở browser thật.
./.pyvenv/bin/python tests/test_browser.py real open https://example.com

# Sửa hosts thật; automatic cleanup, block giữ policy khi được xác nhận.
sudo ./.pyvenv/bin/python tests/test_web_blocker.py real automatic https://example.com
```

Real mode có thể mở browser, sửa hosts, đọc/phát input, đọc màn hình hoặc khóa desktop.
Chạy trên session test có chủ đích; không gọi từ CI hoặc safe suite.

## TEST CONTRACT

- Test public API/contract dùng fake deterministic.
- Test side effect hoặc race dùng fake, temporary path, `Event` hoặc barrier; không
  dùng `sleep` dài hay OS thật.
- `real` command phải mô tả prerequisite, side effect, cách dừng và cleanup trong
  `--info`.
- File test mới tên `test_<feature>.py`, dùng `add_source_path`, `run_module` và
  `test_modes` từ `test_support`.

## TYPE CHECK

```bash
scripts/clean_pyright_check.sh tests
```

Script nhận đúng một target. Xem [testing strategy](../ROI-reports/testing-strategy.md)
để biết test matrix và command an toàn đã xác nhận.
