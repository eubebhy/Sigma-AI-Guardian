# Tri thức ngầm và checklist mở rộng

## TL;DR

Đây là các điều code dựa vào nhưng dễ bị mất khi maintainer mới sửa feature. Mọi thay
đổi liên quan phải kiểm tra precondition, postcondition và side effect tương ứng.

## Invariant theo khu vực

### Agent/platform

- Factory chỉ hỗ trợ Linux/Windows; adapter native không được import feature.
- `get_default_platform_services()` là compatibility singleton process-wide, không
  phải lifecycle owner cho command dài hạn.
- Capability static chỉ nói adapter có thể tạo; readiness phải kiểm tra binary,
  permission và desktop session ở thời điểm action.

### Process/browser/window

- Process name được lowercase; match blacklist là exact name và whitelist ưu tiên.
- List→kill có race tự nhiên; PID là không đủ identity để làm policy đặc quyền dài hạn.
- Browser chỉ nhận HTTP(S) prefix; feature không được nhận arbitrary command.
- Window API hiện trả `dict[title, process]`, nên title trùng là information-loss đã
  biết; không sử dụng nó cho policy cần window identity mạnh.

### Hosts

- Chỉ content giữa `# SAG - Web block list start` và `# SAG - Web block list end`
  thuộc SAG. Marker thiếu end phải fail, không repair tự động.
- `_atomic_write()` chỉ đảm bảo replace file không dở cho **một writer**; không đảm
  bảo concurrent update, toàn bộ metadata hay power-loss durability.
- Default public API chọn hosts thật khi import; automated test phải gọi internal seam
  với `HostsPathOperations` fake/temp path, không gọi `block()` mặc định.

### Screen/input

- `lock()` chờ overlay ready rồi mới block input; `unlock()` là con đường release.
- Linux input grab tồn tại khi `InputDevice` còn mở; không clear registry trước close.
- API sender input phải cân bằng `keyDown`/`keyUp` và `mouseDown`/`mouseUp`.
- Facade Linux/Windows có **17** export chung, gồm `get_num_lock_state`; tên package
  Windows giữ là `window` để compatibility, không đổi thành `windows` hàng loạt.

### Classifier/model

- `StrictLevel` chỉ là `xlow`, `low`, `mid`, `strict`, `xstrict`; giá trị lạ có thể
  làm rule threshold lookup lỗi.
- Main classifier clean text trước, rule trước, local AI sau; rule thắng nếu cả hai
  phát hiện nhãn cấm.
- Cache FIFO tối đa 256 là optimization, không phải persistent policy state.
- `joblib` model chỉ được tin nếu artifact nằm trong release/build trust boundary.

## Checklist thêm feature/category/backend

1. Xác định layer owner và contract; không đặt OS/native call vào feature chung.
2. Ghi input, output, permission, cleanup, failure mode và compatibility impact.
3. Thêm fake test để chứng minh success, invalid input và native failure.
4. Nếu classifier category: update enum, model map, trainer data, rule/phrase, test
   corpus, docs và model provenance cùng nhau.
5. Nếu thread: owner, start/stop idempotence, join/daemon rationale, cleanup và race
   test phải rõ trước code.
