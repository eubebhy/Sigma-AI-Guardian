# ADR 0002: Giữ repository trong boundary local Agent

## TL;DR

Chỉ xây Agent local có command allowlist tương lai; không đưa transport, remote desktop
hay remote shell vào repository trước security/lifecycle boundary.

## Trạng thái

Accepted.

## Bối cảnh và vấn đề

Code hiện tại thao tác desktop/OS cục bộ nhưng chỉ có `status` CLI. Mở network hoặc
remote shell trước command lifecycle, readiness, policy và audit sẽ tạo attack surface
lớn và làm scope classroom-management phình to.

## Quyết định

Repository này chỉ xây dựng SAG Agent local. Server, Teacher Console, LAN, transport,
remote desktop, remote input và `run_shell` không thuộc implementation hiện tại.
Command tương lai phải là structured local allowlist, không phải shell string.

## Lựa chọn thay thế và trade-off

- Xây network/console ngay: demo rộng hơn nhưng không có authorization/audit boundary;
  không chọn.
- Expose generic shell command: linh hoạt nhưng rủi ro privilege cao; không chọn.

## Hệ quả

Ưu tiên lifecycle, command result, readiness và fake test. Khi cần Server, nó là caller
đã xác thực của Agent dispatcher, không chứa native adapter.

## Xem xét lại khi

Agent có command contract, capability/readiness, ownership shutdown, authorization và
audit design đã được review. Files: `TODO.md`, `src/main.py`, `docs/architecture.md`.
