# Sigma AI Guardian

## DESCRIPTION

Sigma AI Guardian (SAG) hiện là Agent cục bộ trên máy học sinh. Entry point
`src/main.py` chỉ cung cấp command an toàn `status`; repository không có Server,
Teacher Console, LAN transport, remote desktop hoặc remote shell.

```bash
./.pyvenv/bin/python src/main.py status
```

Agent chọn adapter Linux hoặc Windows một lần khi khởi động. Classifier, browser,
process guard, web blocker, screen/input và window monitor là public API riêng; CLI
chưa dispatch các feature này.

## PRODUCT DIRECTION

SAG hoàn chỉnh hướng đến quản lý nội dung, ứng dụng và desktop trong phòng máy. Các
khả năng mạng, điều khiển từ xa và Server là định hướng, không phải capability hiện tại.

## REQUIREMENTS

- Python 3.11 trở lên; khuyến nghị 3.13.
- Windows 10/11 hoặc Linux desktop X11/Xorg. Wayland chưa được hỗ trợ đầy đủ.
- Dependency Python trong `requirements.txt`.
- Linux desktop feature có thể cần `ps`, `xdotool`, `xclip`, `evdev`, `/dev/uinput`
  và quyền phù hợp. Không giả định package manager hoặc init system cụ thể.
- `scripts/clean_pyright_check.sh` cần Bash, Pyright và `jq` trên `PATH`.

## INSTALLATION

Tạo virtual environment tại thư mục gốc rồi cài dependency:

```bash
python3 -m venv .pyvenv
./.pyvenv/bin/python -m pip install --upgrade pip
./.pyvenv/bin/python -m pip install -r requirements.txt
```

Trên Windows, dùng `py -3.13 -m venv .pyvenv` và
`.\.pyvenv\Scripts\python.exe` thay cho đường dẫn Python Linux.

Không chạy ứng dụng đồ họa bằng `sudo`. Web blocker cần quyền ghi hosts; Linux input
cần quyền device riêng. Xem README của feature trước khi chạy manual test.

## DOCUMENTATION

- [Kiến trúc Agent](docs/architecture.md)
- [Vai trò `src/agent/`](docs/agent-directory-guide.md)
- [Test safety và commands](tests/README.md)
- [ROI reports, ADR và backlog](ROI-reports/index.md)

## INPUT COMPONENTS

- `src/device_controller/input_controller/`: gửi input và lifecycle virtual device.
- `src/utils/key_listener/`: lắng nghe event và đọc NumLock.

Xem README của từng package để biết API, điều kiện platform và side effect.
