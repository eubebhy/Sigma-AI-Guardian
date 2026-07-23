# Kiểm thử

Thư mục này chứa các script test chạy trực tiếp bằng Python:

```bash
python3 tests/<file>.py
```

Một số test là unit test an toàn, một số test là CLI/manual test có tác động tới
hệ thống thật. Đọc mô tả từng file trước khi chạy.

## Danh sách file

| File | Mục đích | Cách chạy chính | Ghi chú |
| --- | --- | --- | --- |
| `browser_tab.py` | Test mở tab browser bằng monkeypatch, không mở browser thật. | `python3 tests/browser_tab.py` | Có `--case`. |
| `process_killer.py` | Test logic blacklist/whitelist của process killer, không kill process thật. | `python3 tests/process_killer.py` | Có `--case`. |
| `screen_locker.py` | Test contract shortcut unlock; chế độ manual mới khóa màn hình thật. | `python3 tests/screen_locker.py` | `--manual --seconds 5` sẽ khóa thật. |
| `web_blocker.py` | Test web blocker trên hosts dev/thật tùy cấu hình module. | `python3 tests/web_blocker.py` | Có block/unblock và cleanup. |
| `input_controller/` | Unit test và CLI/manual test cho input controller Linux. | Xem `input_controller/README.md`. | Tách riêng test giả và test thiết bị thật. |
| `benchmark_screen_capture.py` | Benchmark FPS cho screen capture. | `python3 tests/benchmark_screen_capture.py` | Có `--seconds`, `--sharpness`. |
| `window_tracker_guard.py` | Quét cửa sổ thật, phân loại nội dung, khóa màn hình nếu phát hiện rủi ro. | `python3 tests/window_tracker_guard.py` | Manual/integration, có thể khóa màn hình. |

## Quy tắc chung

- Test tự động phải ưu tiên fake/mock, không đụng thiết bị thật nếu không cần.
- Test manual/CLI phải có flag rõ ràng và in thông tin trước khi thao tác.
- Test có tác động hệ thống phải cleanup bằng `finally` khi có thể.
- Test phát input thật hoặc khóa màn hình phải được xem là manual test.
- Sau khi sửa test Python, chạy:

```bash
scripts/clean_pyright_check.sh tests/<file>.py
```
