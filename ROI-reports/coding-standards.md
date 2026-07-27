# Chuẩn code áp dụng

## TL;DR

Giữ Python PEP 8, Pyright strict, type hint đầy đủ và code junior-readable. Ưu tiên
module nhỏ, dependency direction rõ, fake-friendly side effect và comment giải thích
lý do.

## Quy tắc bắt buộc

- Dùng absolute import; public API giữ tên hiện có; internal function bắt đầu `_`.
- Không tạo class khi function đủ; method chỉ giữ khi cần state.
- Không thêm abstraction/framework/dependency nếu chưa giải quyết nhu cầu đã chứng minh.
- Module phức tạp có docstring nêu file path, input, output, nguyên lý.
- Type annotation tương thích Pyright strict. Suppression phải hẹp và giải thích lý do
  dependency native, không dùng để che code mới.
- Constant đặt uppercase; không dùng magic platform/path ngoài adapter phù hợp.

## Error và lifecycle

- Không nuốt exception nếu caller cần biết feature thất bại. Nếu cleanup best-effort,
  giới hạn exception cụ thể, dọn state và tài liệu hóa fail-open/fail-closed.
- Thread có owner, stop contract, cleanup và regression test. Không dùng daemon thread
  để thay ownership; daemon chỉ tránh treo process exit.
- Không giữ mutable global mới nếu instance injection/lifecycle owner đơn giản hơn.
- Đóng resource mở trong mọi nhánh, nhất là input descriptor, Tk overlay, MSS backend
  và temporary file.

## Platform và side effect

- Feature nhận protocol/runtime service. Không import `agent.platform.linux` hoặc
  `.windows` từ feature.
- Chạy native process bằng argv-list, không `shell=True`.
- Public command tương lai nhận structured data đã validate, không nhận shell string.
- Tests mặc định dùng temp path/fake cho hosts, process, browser, input và desktop.

## Documentation và compatibility

- Khi sửa `__all__`, signature, CLI flag, dependency hoặc OS prerequisite, cập nhật
  test contract và document cùng commit.
- Comment giải thích invariant/trade-off; không dịch lại từng dòng code.
- Không đổi marker hosts, model label, event format hoặc public input behavior nếu
  chưa có migration/test compatibility.
