# Chiến lược kiểm thử

## TL;DR

Automated test phải fake side effect. Runner chuẩn là `tests/tester.py`; nó nạp mọi
file phẳng `tests/test_*.py`, chạy fake/mock/smoke mặc định và chỉ in failure. Không
chạy mode `real` trong workflow mặc định. Test gắn nhiều safe mode chỉ chạy một lần;
runner chọn mode khai báo đầu tiên khớp với mode caller chọn.

## Test matrix

| Nhóm | Mục tiêu | Cách chạy | Trạng thái/rủi ro |
| --- | --- | --- | --- |
| Safe suite | Mọi feature qua fake/mock/smoke | `python tests/tester.py` | An toàn, không đụng system hosts, desktop hay input thật. |
| Một feature | Fake/mock/smoke của feature đó | `python tests/test_<feature>.py` | An toàn. |
| Manual/system | Hosts, lock, input, window scan, browser/capture thật | `python tests/test_<feature>.py real <command>` | Gọi `run_real()` của feature, không chạy unittest `@test_modes("real")`; chỉ theo session có chủ đích, xem `--info` trước vì có thể side effect. |

Thay `python` bằng `./.pyvenv/bin/python` trên Linux. Đặt
`PYTHONDONTWRITEBYTECODE=1` khi cần giữ tree sạch.

## Lệnh an toàn đã xác nhận

```bash
./.pyvenv/bin/python -m pip check
./.pyvenv/bin/python src/main.py status
./.pyvenv/bin/python tests/tester.py
./.pyvenv/bin/python tests/test_browser.py
./.pyvenv/bin/python tests/test_classifier.py
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
