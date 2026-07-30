# Scripts

## DESCRIPTION

Các script phục vụ phát triển, huấn luyện model và kiểm tra cục bộ; chúng không là API
runtime công khai. Chạy từ project root để relative path trỏ đúng dữ liệu repository.

## COMMANDS

| Script | Input | Output / side effect |
| --- | --- | --- |
| `record_clip_board.py` | Clipboard hiện tại | Ghi dữ liệu clipboard vào file; xem là dữ liệu nhạy cảm, không commit. |
| `train_model.py` | Dữ liệu training | Tạo hoặc thay model artifact trong `data/`. |
| `clean_pyright_check.sh <target>` | Một file hoặc directory Python | Chạy Pyright strict và rút gọn JSON result. |

Ví dụ:

```bash
scripts/clean_pyright_check.sh src
```

## REQUIREMENTS

Checker cần Bash, Pyright và `jq` trên `PATH`. Script ghi dữ liệu hoặc train model có
thể thay đổi `data/`; kiểm tra diff trước khi stage.
