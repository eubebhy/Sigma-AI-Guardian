# Bo cuc source

`src/` chua cac package runtime cua Sigma AI Guardian. Code trong thu muc nay
duoc import boi ung dung, script ho tro va test.

## Entry point va runtime Agent

`main.py` là entry point duy nhất của SAG Agent. Package `agent/` sở hữu runtime,
contract và chọn adapter Windows/Linux một lần; `agent/platform/` là nơi duy nhất
giữ lệnh/API riêng OS. Feature chỉ import contract chung hoặc nhận adapter từ
runtime. Chi tiết tại `docs/architecture.md`.

## `device_controler`

Nhom module dieu khien may hoc sinh hoac moi truong desktop.

- `browser_tab`: mo URL bang browser phu hop.
- `process_killer`: kill process theo blacklist.
- `screen_capture`: chup man hinh bang MSS.
- `screenlocker`: khoa man hinh va chan input.
- `web_blocker`: them/xoa domain trong hosts file.

Dau vao/dau ra chi tiet nam trong docstring dau tung module.

## `system_monitor`

Cung cap API thu thap trang thai he thong.

- `clipboard_tracker`: doc clipboard hien tai.
- `keylogger`: gom phim thanh chuoi text tam thoi.
- `windows_tracker`: doc tieu de cua so active va cac cua so dang mo.

## `utils`

Chua chuc nang dung lai cho nhieu package, khong phu thuoc feature cap cao.

- `input_blocker`: chan/mo chan input theo OS.
- `input_controller`: gui va lang nghe input da nen tang.

Cac package trong thu muc nay duoc thiet ke de package khac import. Chung khong nen import package feature hoac phu thuoc thanh phan cap cao hon cua project.
Dat chuc nang moi o day khi nhieu hon mot package can dung no.

## Quy tac

* API chinh cua moi plugin va package khong duoc chan main thread.
* Tac vu chay lau phai chay trong daemon thread voi `daemon=True`.
* Module phuc tap phai co docstring dau file neu `file path`, input, output va nguyen ly hoat dong.
