# TODO
- Them he thong config.
- Lam he thong log
- Kiem tra lai tester cua classifier.
- Suy nghi ve he thong da nen tang.
- Web blocker: them canh bao khi unblock site khong ton tai.
- Nang cap classifier.

## TODO trong code hien tai
- `src/system_monitor/keylogger/__init__.py:19`: sau khi hoan thanh config system, dua cac gioi han keylogger vao config (`TODO: After finish config system, add this`).
- `tests/content_classifier/test_all_classifiers.py:314`: rule-based engine co thong bao TODO khi backend khong kha dung.
- `tests/content_classifier/test_all_classifiers.py:330`: local AI backend co thong bao TODO khi backend khong kha dung.
- `tests/content_classifier/test_all_classifiers.py:343`: cloud AI backend chua duoc noi vao test harness.

=== main-classifier | strict=mid ===
Tests / chất lượng
- pytest chưa được khai báo/cài trong .pyvenv, nên không chạy được pytest -q.
- python -m unittest discover chạy 0 tests.
- tests/web_blocker.py, browser_tab.py, process_killer.py, screen_locker.py không theo tên discover mặc định của pytest.
- Pyright báo lỗi import/symbol thực tế ở keylogger và dependency thiếu; nhiều lỗi type ở screen capture/window tracker.
- Workspace có nhiều thay đổi chưa commit; không chỉnh sửa chúng.
SUCCESS
Làm ngay
- Khai báo đủ dependency trong requirements.txt.
- Sửa import thiếu Final ở Linux listener.
- Sửa contract keylogger và input_controller để import/chạy được.
- Thêm smoke test import cho Linux và Windows facade.
- Đồng bộ SAG-config.toml với config.py.
Cần cân nhắc
- Tạo main.py làm entry point duy nhất.
- Chọn Windows/Linux backend một lần tại entry point.
- Truyền backend vào feature thay vì feature tự check OS.
- Bỏ khởi tạo MSS tại import; quản lý lifecycle ở entry point.
- Chuẩn hóa unsupported OS: fail rõ ràng, không fallback Linux.
Cần thận trọng
- Thiết kế PlatformBackend tối thiểu, tránh abstraction quá lớn.
- Đảm bảo screen lock thất bại thì không hiển thị trạng thái đã khóa.
- Đồng bộ/lifecycle cho local AI model và monitor thread.
- Bảo vệ file model trước joblib.load.
- Tách test khỏi hosts, input device và desktop thật.
