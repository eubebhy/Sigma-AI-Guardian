# Web Blocker

## DESCRIPTION

`src/device_controler/web_blocker/` quản lý domain SAG trong hosts file. Module chỉ
sở hữu nội dung giữa `START_MARKER` và `END_MARKER`; nội dung ngoài marker được giữ.

## INPUT

`block(file_path)` và `unblock(file_path)` nhận text file gồm một domain hoặc URL mỗi
dòng. Comment bắt đầu bằng `#` bị bỏ qua.

```text
example.com
https://www.example.org/path
```

## OUTPUT

- `block()` trả `set[str]` domain được thêm mới.
- `unblock()` trả `None`.
- Module chỉ ghi hosts khi nội dung thay đổi. Marker lỗi raise `ValueError`.

## OPERATION

Module chuẩn hóa hostname, giữ sidecar lock trong toàn bộ giao dịch read-modify-write,
rồi ghi temporary file và `os.replace()`. Lock chỉ serialize writer SAG cùng dùng hosts
path; nó không điều khiển công cụ không dùng lock này và không bảo đảm durability khi
mất điện.

## PERMISSIONS

Linux thường cần quyền ghi `/etc/hosts`; Windows thường cần Administrator để ghi hosts.
Automated test phải truyền fake hosts adapter hoặc temporary path, không gọi public API
mặc định với hosts thật.
