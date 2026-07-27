# Chiến lược kiểm thử

## TL;DR

Automated test phải fake side effect. `unittest discover` hiện có 22 test sau regression
process-killer nhưng không thu test trong thư mục con không phải package; không coi
con số này là coverage toàn repository.

## Test matrix

| Nhóm | Mục tiêu | Cách chạy | Trạng thái/rủi ro |
| --- | --- | --- | --- |
| Agent contract/runtime | Factory, status, adapter fake | `python -m unittest tests/test_agent_runtime.py tests/test_agent_platform.py` | An toàn. |
| Feature unit | Keylogger, screen capture, screenlocker fake, process killer | `python -m unittest discover -s tests -p 'test*.py' -v` | An toàn nếu không thêm manual script. |
| Classifier unit nhỏ | `clean_text`, rule smoke | Chạy hai file riêng | An toàn, không phải evaluation đầy đủ. |
| Input facade | Import/API fake | `python tests/test_input_controller_facade.py` | An toàn. |
| Input backend con | Windows/Linux mock | Chạy trực tiếp từng file | Window facade contract pass sau khi đồng bộ 17 API. |
| Manual/system | Hosts, lock, event logger, UInput, window guard | Chỉ theo session có chủ đích | Có thể sửa hosts, lock máy, đọc input hoặc phát input. |
| Benchmark | Screen capture/classifier | Chạy ngoài CI | Đọc màn hình/CPU; không là test correctness. |

Thay `python` bằng `./.pyvenv/bin/python` trên Linux. Đặt
`PYTHONDONTWRITEBYTECODE=1` khi cần giữ tree sạch.

## Lệnh an toàn đã xác nhận

```bash
./.pyvenv/bin/python -m pip check
./.pyvenv/bin/python src/main.py status
./.pyvenv/bin/python -m unittest discover -s tests -p 'test*.py' -v
./.pyvenv/bin/python tests/content_classifier/test_clean_text.py
./.pyvenv/bin/python tests/content_classifier/test_rule_based.py
./.pyvenv/bin/python tests/browser_tab.py
./.pyvenv/bin/python tests/process_killer.py
scripts/clean_pyright_check.sh src
scripts/clean_pyright_check.sh tests
scripts/clean_pyright_check.sh scripts
```

`scripts/clean_pyright_check.sh` nhận **một target mỗi lần**. Không chạy
`scripts/clean_pyright_check.sh src tests`.

## Quy tắc test mới

- Public API/contract: unit test deterministic với fake adapter.
- Bug side effect/concurrency: tái hiện bằng fake, `Event`/barrier thay vì `sleep`
  dài hoặc OS thật.
- Test manual phải nằm ngoài command test mặc định, in cảnh báo và có cleanup.
- Assertion phải kiểm tra effect/value/error contract, không chỉ không-crash.
- Test Windows/Linux facade phải derive expected API từ một contract chung, không
  hard-code count dễ stale.

## Khoảng trống ưu tiên

Xem [technical-debt.md](technical-debt.md): process guard lifecycle/failure, screen
locker cleanup, hosts concurrent writer, classifier input budget, input queue và
model provenance. Trước khi thêm CI, cần quyết định test classifier nào là quality
