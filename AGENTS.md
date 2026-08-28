# AGENTS.md
## Mission
Phần mềm quản lý phòng tin học dành cho giáo viên, tích hợp AI Agent để phân tích và thực thi tool calling trong ứng dụng.

## Đọc trước khi sửa
* Đọc module docstring, test liên quan và ADR phù hợp trước khi thay đổi behavior,
  lifecycle, platform hoặc public API.
* Repository hiện là **SAG Agent cục bộ**. Server, Teacher Console, LAN, remote
  desktop, remote input và remote shell không thuộc scope hiện tại.

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
* **Ngôn ngữ output:** Runtime logs, CLI output, test output và error messages phải
  viết bằng English để thống nhất khi debug, tìm kiếm và tích hợp tooling.
* **Ngôn ngữ code nội bộ (tạm thời):** Docstring, comment và ghi chú dành cho dev
  trong source code viết bằng tiếng Việt. Quy tắc này chỉ áp dụng cho nội bộ code,
  không áp dụng cho output người dùng.
* **Tính di động (Portable):** Mã nguồn phải đảm bảo tính độc lập, sao chép sang thư mục khác vẫn hoạt động bình thường.
* **Side effect:** Test tự động không được ghi hosts thật, kill process thật, mở
  browser, đọc/phát input thật, khóa desktop hoặc đọc dữ liệu người dùng. Dùng fake,
  mock hoặc temporary path; manual test phải được gọi có chủ đích.

### Python
* Follow PEP 8 extreme strictly.
* Use complete type hints compatible with Pyright strict mode.
* Không dùng `object` trong type hint khi có thể khai báo type cụ thể hơn.
* Do not complicate logic only to satisfy typing.
* Use absolute imports.
* Avoid unnecessarily complex, obscure, or high-level Python syntax and tools.
* Prefer explicit code when it is easier for beginners to understand.
* Always use junior python syntax instead of senior syntax

## Modules and Packages

* Each module should have one primary responsibility.
* Internal functions start with `_`.
* Public functions use normal names.
* Do not create a new module when the code is too small to justify one.
* Merge very small package-level helpers into the most relevant existing module or `__init__.py` only when this matches the existing project structure.

## Classes

* Keep methods only when they require object state.
* Move state-independent logic to module-level functions.
* Do not introduce a class when functions are sufficient.

## Functions

* Keep functions at or below 20 lines when this does not make the code harder to understand.
* Split longer functions into clear single-responsibility functions.
* Extract a main code block longer than 10 lines only when extraction improves clarity.
* Do not create a helper shorter than five lines unless it removes duplication, names an important concept, or matches existing architecture.
* Otherwise, inline short logic and add a concise explanatory comment when necessary.

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

Script trên nhận một target mỗi lần. Chạy riêng `src`, `tests` và `scripts` khi phạm
vi thay đổi liên quan. Chỉ chạy các test ngoài unit test an toàn khi có chủ đích.

Virtual environment của dự án: `./.pyvenv`.
