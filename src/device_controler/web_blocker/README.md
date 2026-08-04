# WebBlocker

## Mục tiêu

`WebBlocker` cung cấp policy block website cục bộ cho SAG Agent, với UX phù hợp cho
teacher command: bật/tắt category, custom block domain, custom allow domain và reset.

## API

```python
blocker.block_category("porn")
blocker.unblock_category("porn")
blocker.block_site("example-game.com")
blocker.allow_site("youtube.com")
blocker.remove_allowed_site("youtube.com")
blocker.get_status()
blocker.clear_all()
```

Module cũng export singleton `manager` để Agent command handler dùng chung policy state.

`allow_site()` có precedence cao nhất: nó gỡ domain khỏi tất cả marker SAG đang có.
`remove_allowed_site()` không tự block domain lại.

Category hợp lệ:

```text
porn, gore, game, social, messaging, entertainment
```

## Output

Mỗi action trả `WebBlockResult`:

```python
WebBlockResult(
    changed=True,
    blocked_domains=12,
    unblocked_domains=0,
    skipped_domains=1,
)
```

`changed` phản ánh thay đổi hosts hoặc policy runtime. `skipped_domains` là domain
đã tồn tại trong custom block hoặc bị custom allow override.

## Lưu trữ

Runtime policy được lưu tại `data/webblocker/policy.json`. File này khác
`sag_agent_config.toml`: TOML là cấu hình Agent, JSON là state policy giáo viên đang
áp dụng. Lần action đầu tiên sau restart tự khôi phục marker hosts thiếu từ policy.

## Errors

API raise `ValueError` khi category không hợp lệ, marker SAG hỏng hoặc policy JSON
không đọc/validate được. Lỗi hosts file và policy file được propagate để Agent caller
quyết định retry, report hoặc dừng action.

## Hiệu năng

Mỗi category có marker riêng trong hosts. Block category stream source list và hosts
một lần vào temporary file, rồi atomic replace đúng một lần. Unblock category xóa
nguyên marker, không đọc source list. Module không nạp full category list vào RAM.

Custom allow/block được kỳ vọng nhỏ và lưu bằng set để tra cứu O(1). Category source
phải được chuẩn hóa, loại trùng trước khi đóng gói; runtime không deduplicate full
list để giữ RAM thấp. Không gọi API theo từng domain của category vì mỗi action sẽ
rewrite hosts đúng một lần.
