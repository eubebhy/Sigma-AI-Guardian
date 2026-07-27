# Architecture Decision Records

## TL;DR

ADR ghi quyết định có ảnh hưởng dài hạn; không ghi chi tiết implementation nhỏ. Trạng
thái `Accepted` mô tả behavior hiện có được audit, `Proposed` cần approval trước code.

| ADR | Trạng thái | Quyết định |
| --- | --- | --- |
| [0001-platform-abstraction.md](0001-platform-abstraction.md) | Accepted | Contract nhỏ + adapter OS riêng. |
| [0002-local-agent-boundary.md](0002-local-agent-boundary.md) | Accepted | Repository là local Agent, không remote command transport. |
| [0003-hosts-marker-ownership.md](0003-hosts-marker-ownership.md) | Accepted | SAG chỉ sở hữu marker section hosts, ghi bằng replace. |
| [0004-hybrid-local-classification.md](0004-hybrid-local-classification.md) | Accepted | Clean text → rule trước → local model khi cần. |

Khi đảo quyết định, tạo ADR mới thay vì sửa lịch sử ADR cũ; liên kết supersedes rõ ràng.
