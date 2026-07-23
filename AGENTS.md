# AGENTS.md
## Mission
Phần mềm quản lý phòng tin học dành cho giáo viên, tích hợp AI Agent để phân tích và thực thi tool calling trong ứng dụng.

## Scope Rules
* **Đúng yêu cầu:** Chỉ thực hiện chính xác những gì được giao. Không tự ý mở rộng phạm vi công việc.
* **Giới hạn biên:** Phát hiện vấn đề ngoài phạm vi task phải dừng lại và báo cáo, tuyệt đối không tự sửa.
* **Xử lý dependency phụ thuộc:** Nếu task phụ thuộc vào tính năng chưa tồn tại, chỉ viết phần tối thiểu để hoàn thành task hiện tại và để lại ghi chú `TODO`.

## Authority
* Không tự ý refactor mã nguồn.
* Không thay đổi kiến trúc hệ thống (architecture).
* Không thêm thư viện ngoài (dependency) trừ khi có yêu cầu cụ thể.
* Không chỉnh sửa các file nằm ngoài phạm vi task được giao.

## Coding Rules
### General
* **Tối giản:** Ưu tiên thay đổi ít nhất có thể để đạt mục tiêu hiện tại. Không tạo ra các lớp trừu tượng (abstraction) mới khi chưa cần thiết.
* **Tính nhất quán:** Không thay đổi tên các Public API hiện có.
* **Tài liệu hóa (Bằng tiếng Việt):** 
  * Tại mỗi package/module phức tạp, phải ghi chú rõ: Đường dẫn file (`file path`), chuẩn `input`, chuẩn `output` và nguyên lý hoạt động đi kèm với các chuẩn đó.
* **Tính di động (Portable):** Mã nguồn phải đảm bảo tính độc lập, sao chép sang thư mục khác vẫn hoạt động bình thường.

### Python
* **Chuẩn mực:** Tuân thủ nghiêm ngặt PEP 8.
* **Type Hinting cực đoan:** Khai báo kiểu dữ liệu đầy đủ và chặt chẽ cho mọi thành phần để vượt qua bộ kiểm tra cấu trúc ở chế độ nghiêm ngặt (`Pyright strict mode`). Không làm phức tạp hóa logic chỉ để phục vụ type hint.
* **Import:** Bắt buộc sử dụng Absolute Import (Import tuyệt đối).
* **Nội hàm hóa (Inline hàm ngắn):** Các hàm hoặc thành phần bổ trợ có độ dài `< 5 dòng` không được tách riêng biệt. Phải gộp trực tiếp vào hàm chính/phương thức gọi nó và viết ghi chú giải thích bằng tiếng Việt.

### Module & Class
* **Module:**
  * Mỗi module đảm nhận một trách nhiệm duy nhất và có một entry point chính.
  * Hàm nội bộ bắt đầu bằng dấu gạch dưới `_`. Hàm public đặt tên bình thường.
  * Module quá nhỏ phải gộp thẳng vào `__init__.py`, không tạo file mới.
* **Class:**
  * Chỉ giữ lại các phương thức thực sự cần truy cập hoặc thao tác với trạng thái (state) của đối tượng.
  * Các hàm không phụ thuộc vào trạng thái đối tượng phải đưa ra cấp module.

# Output
## Normal output
- Only answer exactly what is asked. (Strict)
- DO NOT answer anything user does not asked for. (Strict)
- Do not expand, infer, or suggest improvements beyond the question scope.
- No non-essential content.
- Do not provide solutions or over-explain unless explicitly requested, to prevent spoiling the answer for the user.


## Workflow
Sau dung workflow mac dinh cua m, sau khi lam xong thi buoc cuoi la chay lenh benh duoi de check va fix den khi xong
   ```bash
   scripts/clean_pyright_check.sh <path_to_python_file_or_directory>
   ```

Virtual environment của dự án: `./.pyvenv`.
