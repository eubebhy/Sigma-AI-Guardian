# Script ho tro

Cac script trong thu muc nay phuc vu phat trien, huan luyen model va kiem tra cuc bo.
Chung khong phai API runtime cong khai cua ung dung.

## Tao du lieu huan luyen

- `dedupe_similar_lines.py`: xoa cac dong giong nhau theo nguong.
- `record_clip_board.py`: ghi noi dung clipboard vao file.
- `train_model.py`: huan luyen model tu du lieu huan luyen hien co.

## Khac

- `clean_pyright_check.sh`: chay Pyright theo cach rut gon de de doc loi.

## Ghi chu

- Chay script tu project root de cac duong dan tuong doi tro dung du lieu trong repo.
- Script ghi du lieu hoac huan luyen model co the tao/thay doi file trong `data/`.
- Khi sua file Python, dung `scripts/clean_pyright_check.sh <path>` de kiem tra rieng file do.
