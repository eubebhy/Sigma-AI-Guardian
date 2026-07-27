# ADR 0003: SAG chỉ sở hữu section hosts có marker

## TL;DR

SAG chỉ thêm/xóa domain trong marker section của hosts và replace file atomically cho
một writer; concurrent writer là debt được ghi riêng.

## Trạng thái

Accepted.

## Bối cảnh và vấn đề

Hosts file thuộc hệ điều hành và có thể chứa entry của người dùng/công cụ khác. SAG cần
thêm/xóa nhiều domain mà không phá nội dung ngoài phạm vi của mình.

## Quyết định

`web_blocker` chỉ parse/render domain giữa `START_MARKER`/`END_MARKER`. Nội dung ngoài
marker được giữ; update tính trong memory và ghi temporary file cùng directory rồi
`os.replace()`. Marker start không có marker end là lỗi `ValueError`.

## Lựa chọn thay thế và trade-off

- Rewrite toàn file: đơn giản nhưng phá ownership khác; không chọn.
- Mỗi domain ghi trực tiếp: nhiều I/O và khó cleanup; không chọn.
- Database/proxy DNS: ngoài scope local Agent hiện tại; không chọn.

## Hệ quả

Một writer không để hosts bị ghi dở và domain được dedupe/sort. Quyết định **không**
`technical-debt.md` trước khi thay semantics.

## Xem xét lại khi

Có policy multi-process hoặc cần preserve metadata/durability đã định nghĩa. File:
`src/device_controler/web_blocker/__init__.py`.
