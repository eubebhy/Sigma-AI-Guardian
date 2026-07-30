# ADR 0001: Platform abstraction bằng contract nhỏ

## TL;DR

Giữ native code trong adapter Windows/Linux và cho feature phụ thuộc vào bốn protocol
nhỏ để test bằng fake, không dùng một backend khổng lồ.

## Trạng thái

Accepted.

## Bối cảnh và vấn đề

SAG cần process, browser, window và hosts trên Windows/Linux nhưng feature không nên
chứa `ps`, `taskkill`, đường dẫn hosts hay nhánh OS. Một backend lớn sẽ gom capability
có permission/lifecycle khác nhau và làm fake test nặng.

## Quyết định

Dùng bốn `Protocol` trong `src/agent/contracts.py`; `PlatformServices` immutable được
factory tạo một lần từ `src/agent/platform/<os>/`. Feature dùng protocol hoặc runtime
service; compatibility caller có thể dùng singleton process-wide.

## Lựa chọn thay thế và trade-off

- Một `PlatformBackend` lớn: ít field hơn nhưng coupling/fake lớn hơn; không chọn.
- Mỗi feature tự detect OS: đơn giản tức thời nhưng duplicate native logic; không chọn.
- DI framework/registry động: không cần cho bốn capability hiện có; không chọn.

## Hệ quả

Test được fake dễ hơn và OS unsupported fail rõ. Đổi lại, compatibility singleton vẫn
phải được kiểm soát khi thêm lifecycle command; không để command tạo service riêng.

## Xem xét lại khi

Có capability mới cần lifecycle chung thực sự, hoặc support OS mới chứng minh bốn
contract không đủ. Files: `src/agent/contracts.py`, `src/agent/platform/__init__.py`.
