# Backlog ROI sau audit

## TL;DR

Ưu tiên làm guardrail và lỗi lifecycle trước feature/network. Mỗi item dưới đây có
thể giao cho maintainer hoặc model yếu vì scope, file và verification đã rõ.

| Thứ tự | Việc | Priority | Impact / effort / risk / ROI | Prerequisite và verification |
| --- | --- | --- | --- | --- |
| 1 | Command dispatcher local allowlist | P2 | Cao / M / trung bình / cao | Chỉ `agent.status`; fake request/result, không network. |
| 2 | Thiết kế readiness report tách capability | P2 | Cao / M / thấp / cao | Fake binary/permission/session; không side effect. |
| 3 | Xác định input/token budget classifier | P2 | Cao / M / trung bình / cao | Golden + adversarial corpus, latency/quality threshold. |
| 4 | Tạo reproducible dependency/tooling setup | P2 | Cao / M / thấp / cao | Chốt OS/Python matrix; clean venv Windows/Linux. |
| 5 | Deterministic training + model manifest/hash | P3 | Trung bình / M / thấp / cao | Dataset ownership, fixed trainer environment. |
| 6 | Bounded Windows input queue và UInput locking | P3 | Trung bình / M / trung bình / trung bình | Event ordering/loss policy; fake stress tests. |

## Không thuộc roadmap hiện tại

Server, Teacher Console, LAN discovery, WebSocket/HTTP API, remote desktop, remote
input, WebRTC, database và `run_shell` không được bắt đầu chỉ từ backlog này. Chúng
cần security/auth/audit design riêng sau khi Agent local có lifecycle và readiness
đáng tin cậy.

## Quy tắc chọn item tiếp theo

Chọn item ROI cao nhất có precondition đã đủ và có test fake được. Nếu sửa đòi đổi
public API, platform policy hoặc model behavior, tạo ADR/update ADR trước khi code.
