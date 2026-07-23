# Web Blocker

`src/device_controler/web_blocker` chan website bang cach them domain vao hosts
file cua he dieu hanh.

## Dau vao

- `block(file_path)`: nhan file text chua domain hoac URL, moi dong mot gia tri.
- `unblock(file_path)`: nhan cung dinh dang file de xoa domain khoi trang thai block.

## Dau ra

- Hosts file duoc cap nhat trong block nam giua marker cua SAG.
- Neu noi dung khong doi, module khong ghi lai hosts file.

## Nguyen ly

Module doc danh sach domain, chuan hoa ve hostname, doc hosts hien tai, thay doi
block cua SAG trong bo nho roi ghi atomic replace. Cach nay giu phan hosts ben
ngoai marker khong thuoc quyen quan ly cua module.

## Quyen he thong

- Linux: thuong can quyen ghi `/etc/hosts`.
- Windows: thuong can quyen admin de ghi `C:\Windows\System32\drivers\etc\hosts`.

Cho coding agent:
File rat lon, khong doc: `./porn-sites.txt`.
