# Quy ước logging

Log level không bị giới hạn theo file hay layer. `main.py`, feature và adapter đều
có thể log `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` khi ý nghĩa sự kiện phù
hợp.

## Layer quyết định recovery

```text
Adapter
  │
  +─ Khắc phục được: log phù hợp, xử lý và trả kết quả
  │
  +─ Không khắc phục được: giữ thông tin lỗi và raise
  ▼
Feature
  │
  +─ Khắc phục được: warning + fallback/retry/skip
  │
  +─ Không khắc phục được: giữ thông tin lỗi và raise
  ▼
Main/Runtime
  │
  +─ Operation thất bại nhưng process tiếp tục: error
  │
  +─ Không thể tiếp tục process/nhiệm vụ chính: critical
```

Layer quyết định recovery là layer chịu trách nhiệm log kết quả recovery. Layer
không xử lý được lỗi phải raise lên layer trên.

Khong log o nhung noi yeu cau IO, hieu suat, loop nhieu gay spam

## Abstraction boundary và duplicate log

Object log hành động ở abstraction boundary đầu tiên mà nó biết. Không log lại
implementation bên trong của object được gọi.

```text
ProcessGuard: bắt đầu quét process
Platform adapter: không log lại việc đang quét process
```

Quy tắc:

1. Moi thai phan can log, vi du nhu ham, class,v.v chi log nhung thu no lam

```python
def main():
    logger.info("Creating runtime")
    runtime = create_runtime()
    logger.info("Created runtime")
    return 0

def create_runtime():
    # Khong log: logger.info("Creating runtime") tai dong nay; chi log nhung gi no lam
    logger.info("getting sustem services")
    system_service = get_sys_service()
    some_var = 1
    reutnr tuple(some_var, system_service)
```

```text
Creating runtime
getting system service
Created runtime
```
canh nay giup log clean

### `DEBUG`

Giá trị runtime, input/output chuẩn hóa, nhánh logic, retry, timeout và chi tiết debug.
Không ghi secret, token, password hoặc dữ liệu nhạy cảm.

### `INFO`

Sự kiện bình thường, start, shutdown, operation bắt đầu hoặc hoàn tất.
Message theo dạng: `<Chuyện gì đang xảy ra> / <đang làm gì>`.

### `WARNING`

Bất thường nhưng flow vẫn tiếp tục nhờ fallback, retry, skip hoặc giá trị mặc định.
Message theo dạng: `<Chuyện gì đã xảy ra> + <đã làm gì để xử lý>`.

### `ERROR`

Operation thất bại nhưng process vẫn có thể tiếp tục. Khi có exception, giữ traceback
và lỗi gốc; message theo dạng: `<Chuyện gì đã xảy ra> + <đã làm gì nếu có>`.

### `CRITICAL`

Process hoặc nhiệm vụ chính không thể tiếp tục.
Message ghi rõ lỗi nghiêm trọng và traceback nếu có.

## Thông tin lỗi

Mỗi log lỗi cố gắng cung cấp đầy đủ:

- operation đang thực hiện;
- input hoặc định danh cần thiết;
- kết quả recovery/fallback;
- exception type, message và traceback gốc;
- file và dòng code do formatter cung cấp.

Ưu tiên `logger.exception(...)` bên trong `except`. Không dùng message mơ hồ như:

```python
logger.error("cleanup failed")
```

## Cleanup

Object log lifecycle của chính nó; Runtime log việc điều phối ở cấp Runtime. Không
in trực tiếp resource/object:

```python
try:
    resource.close()
except Exception:
    logger.exception(
        "AgentRuntime không thể đóng resource; tiếp tục cleanup resource khác",
    )
```

## Cach log
Module chỉ tạo logger:

```python
import logging

logger = logging.getLogger(__name__)
```

Không tự thêm handler trong feature hoặc adapter. `configure_logging()` là nơi cấu
hình handler chung để tránh log trùng.
