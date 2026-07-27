# Tài liệu kiến trúc

## TL;DR

Đọc [`architecture.md`](architecture.md) để biết code Agent đang có. Đọc các tài liệu
đích dưới đây khi hoàn tất Agent local và bắt đầu xây Server trong LAN.

## Thứ tự đọc để build Server

1. [target-architecture.md](target-architecture.md): mục tiêu, boundary và sơ đồ tổng thể.
2. [server-blueprint.md](server-blueprint.md): entry point Server, tree và trách nhiệm.
3. [agent-server-contract.md](agent-server-contract.md): dữ liệu vào/ra giữa Server và Agent.
4. [build-server-after-agent.md](build-server-after-agent.md): thứ tự build nhỏ, vừa làm vừa học.

## Phân biệt tài liệu

- [`architecture.md`](architecture.md) mô tả **code hiện tại**: Agent local chỉ có
  `status`, chưa có dispatcher hoặc network.
- Các tài liệu đích mô tả **kiến trúc cần xây dần**. Chúng không chọn framework,
  library, protocol cụ thể hoặc hướng dẫn triển khai cryptography.
