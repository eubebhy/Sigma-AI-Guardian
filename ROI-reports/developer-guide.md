# Hướng dẫn maintainer và developer

## TL;DR

Dùng Python trong `.pyvenv`, chạy từ project root, kiểm tra theo từng target Pyright,
và không chạy script desktop/hosts thật trừ manual session có chủ đích.

## Setup và smoke test

Chi tiết package OS nằm trong [`README.md`](../README.md). Sau khi tạo venv và cài
`requirements.txt`, chạy:

```bash
./.pyvenv/bin/python -m pip check
./.pyvenv/bin/python src/main.py status
```

Windows thay đường dẫn Python bằng `.\.pyvenv\Scripts\python.exe`. `status` an toàn:
nó không sửa hosts, grab input, kill process hay mở browser.

## Quy trình thay đổi

1. Đọc [`../AGENTS.md`](../AGENTS.md), [architecture-overview.md](architecture-overview.md),
   module docstring và test liên quan.
2. Nêu behavior hiện tại, expected behavior và boundary side effect trước khi sửa.
3. Viết regression test fake nếu sửa bug; không dùng desktop/process/hosts thật.
4. Thay đổi nhỏ nhất, không đổi public API ngoài scope.
5. Chạy test/type check mục tiêu, sau đó cập nhật tài liệu và `TODO.md` khi có debt mới.

## Debug

| Triệu chứng | Kiểm tra trước |
| --- | --- |
| `status` không chạy | OS phải Linux/Windows; đọc exception factory và Python venv. |
| Window/input không hoạt động | Xorg/desktop session, `xdotool`/`xinput`, `/dev/input`, `/dev/uinput`, quyền user. |
| Hosts bị từ chối | Path platform, quyền Administrator/root, marker hosts có đầy đủ không. |
| Classifier chậm/sai | strict level, input length, cache, runner report; không dùng report hiện tại làm quality gate. |
| Pyright khác môi trường | `pyright` và `jq` hiện lấy từ PATH global, không phải venv. |

## Không làm trong routine development

- Không chạy `tests/test_web_blocker.py`, `tests/test_screen_locker.py`,
  `tests/test_window_tracker.py`, input control/logger hoặc benchmark capture như một
  phần unit test.
- Không gọi `run_shell`, auto-elevation, network transport hoặc remote desktop vào
  Agent hiện tại.
- Không sửa model `Ritchie.pkl` trực tiếp; train theo quy trình reproducibility khi
  roadmap đó được duyệt.
