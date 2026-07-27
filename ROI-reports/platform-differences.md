# Khác biệt nền tảng

## TL;DR

Windows 10/11 và Ubuntu/Debian GNOME **trên Xorg** là target hiện tại. Capability
tĩnh không phải readiness; feature phải phản ánh lỗi permission/session thực tế.

| Khả năng | Linux | Windows | Điều chưa xác minh |
| --- | --- | --- | --- |
| Process | `ps -eo pid=,comm=`, `os.kill(pid, 9)` | `tasklist` CSV, `taskkill /F` | Lỗi list và exit code `taskkill` khác 0 được propagate; quyền kill process khác owner. |
| Browser | `subprocess.Popen`, `webbrowser` | `Popen` với creation flag, `webbrowser` | Browser/executable có sẵn. |
| Hosts | `/etc/hosts` | `C:\Windows\System32\drivers\etc\hosts` | Quyền ghi/admin và antivirus policy. |
| Window | PyWinCtl, fallback `xdotool` | PyWinCtl | Desktop session, PyWinCtl exception, title trùng. |
| Input send/listen | evdev, UInput, Xlib/XInput2 | pydirectinput-rgx, pynput | Privilege, driver, global hook. |
| Input block | exclusive evdev grab | Win32 `BlockInput` | Có đủ device/quyền để lock thật. |
| Capture/overlay | MSS, Tk/X11 | MSS, Tk/Win32 | Multi-monitor, DPI, compositor. |

## Điều kiện Linux

Theo [`README.md`](../README.md), cần GNOME on Xorg, `ps`, `xdotool`, `xclip`,
Tk/X11, `evdev` và `/dev/uinput`. Source virtual mouse còn gọi
`xinput` tại `src/device_controler/input_controller/linux/sendinput_mouse.py`; hướng dẫn cài
đặt phải có binary này trước khi coi sender Linux là ready. Wayland không được quảng
bá là hỗ trợ hoàn chỉnh.

`input_blocker.linux.block()` cố grab từng `/dev/input/event*`; một lỗi sẽ rollback
các descriptor đã mở và raise. `unblock()` thử release mọi descriptor trước khi raise
toàn bộ lỗi release. Không suy ra “locked” chỉ từ overlay hiển thị.

## Điều kiện Windows

Hosts và input block có thể cần Administrator. Input gửi vào application có privilege
cao hơn có thể không được nhận. `pynput` global hook và `PyWinCtl` phụ thuộc desktop
session. Không có test Windows thật trong audit này.

## Quy tắc code

- OS check/native binary chỉ thuộc `src/agent/platform/<os>/` hoặc backend input
  hiện có; feature không kiểm tra `sys.platform`/`os.name` rải rác.
- Không fallback sang OS khác. `NotImplementedError` là kết quả đúng với OS chưa hỗ trợ.
- Test platform code bằng fake adapter trước; manual verification ghi rõ OS, quyền,
  desktop session và cleanup.
