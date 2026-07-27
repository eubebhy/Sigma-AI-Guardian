# Chỉ mục bảo trì dài hạn

## TL;DR

Repository hiện là **SAG Agent cục bộ** cho Windows và Linux, không phải Server,
Teacher Console hay hệ thống điều khiển từ xa. Đọc tài liệu này trước khi sửa code;
các feature desktop có side effect và nhiều test cũ là manual-only.

## Phạm vi và mức độ tin cậy

Đợt audit này đọc source, test, script, cấu hình, dependency, dữ liệu model và tài
liệu đang được Git theo dõi. Nhận định có dẫn chứng là trạng thái đã xác nhận từ
code. Môi trường Windows, quyền Administrator, Wayland, X11 thật, `/dev/input`,
hosts thật và model artifact không được chạy trong đợt audit; các phần đó được ghi
riêng là chưa xác minh.

**Snapshot audit:** 26-07-2026, Linux, `.pyvenv` Python 3.13.5, commit gốc
`045393aa23719f30f6a3e821ee1ed97457045726`. Đã chạy `pip check`, `src/main.py status`,
safe unit tests, classifier unit nhỏ và Pyright theo từng target.
Pyright `scripts` còn warning không resolve `pyperclip`, được ghi tại
[dependency-analysis.md](dependency-analysis.md). Trước audit có xóa chưa commit
`docs/superpowers/plans/2026-07-26-sag-agent-cross-platform.md`; audit không khôi
phục hoặc thay đổi file đó.

## Thứ tự đọc

| Đối tượng | Đọc theo thứ tự |
| --- | --- |
| Maintainer mới | [architecture-overview.md](architecture-overview.md) → [module-map.md](module-map.md) → [developer-guide.md](developer-guide.md) → [testing-strategy.md](testing-strategy.md) |
| Contributor/junior | [coding-standards.md](coding-standards.md) → [platform-differences.md](platform-differences.md) → [failure-modes.md](failure-modes.md) |
| AI agent | [`../AGENTS.md`](../AGENTS.md) → tài liệu kiến trúc → [technical-debt.md](technical-debt.md) → [roadmap.md](roadmap.md) |
| Debugger | [failure-modes.md](failure-modes.md) → [testing-strategy.md](testing-strategy.md) → [knowledge-base.md](knowledge-base.md) |
| Chuẩn bị release | [dependency-analysis.md](dependency-analysis.md) → [security-review.md](security-review.md) → [performance-review.md](performance-review.md) → [maintainability-review.md](maintainability-review.md) |

## Danh mục

| Tài liệu | Mục đích |
| --- | --- |
| [architecture-overview.md](architecture-overview.md) | Kiến trúc, luồng dữ liệu/điều khiển và lifecycle hiện tại. |
| [module-map.md](module-map.md) | Ownership, API và state của từng khu vực source. |
| [platform-differences.md](platform-differences.md) | Điều kiện và khác biệt Windows/Linux/Xorg/Wayland. |
| [developer-guide.md](developer-guide.md) | Setup, chạy, debug và quy trình thay đổi an toàn. |
| [testing-strategy.md](testing-strategy.md) | Test matrix, lệnh an toàn và khoảng trống coverage. |
| [coding-standards.md](coding-standards.md) | Chuẩn code áp dụng cho repository này. |
| [technical-debt.md](technical-debt.md) | Backlog kỹ thuật có bằng chứng, ưu tiên và ROI. |
| [security-review.md](security-review.md) | Boundary, rủi ro và hardening cần thiết. |
| [dependency-analysis.md](dependency-analysis.md) | Dependency, reproducibility và khả năng cài đặt. |
| [performance-review.md](performance-review.md) | Baseline hiện có và kế hoạch benchmark. |
| [failure-modes.md](failure-modes.md) | Failure mode, recovery và cách xác minh. |
| [maintainability-review.md](maintainability-review.md) | Coupling, docs drift, workflow và onboarding. |
| [knowledge-base.md](knowledge-base.md) | Tri thức ngầm, invariant và điểm mở rộng. |
| [roadmap.md](roadmap.md) | Việc còn lại theo ROI; không phải cam kết feature. |
| [adr/index.md](adr/index.md) | Architecture Decision Records. |

## Quy tắc cập nhật

- Sửa hành vi, API, dependency, platform support hoặc lifecycle phải cập nhật tài
  liệu liên quan trong thư mục này cùng commit.
- Không biến phát hiện chưa xác minh thành fact. Nêu điều kiện tái hiện và môi
  trường cần thiết.
- Không dùng tài liệu này để nới scope: Server, LAN, remote desktop và remote
  shell vẫn ngoài repository Agent hiện tại.
