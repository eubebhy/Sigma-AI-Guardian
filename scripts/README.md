# Scripts

## DESCRIPTION

Các script phục vụ phát triển, huấn luyện model và kiểm tra cục bộ; chúng không là API
runtime công khai. Chạy từ project root để relative path trỏ đúng dữ liệu repository.

## COMMANDS

| Script | Input | Output / side effect |
| --- | --- | --- |
| `record_clip_board.py` | Clipboard hiện tại | Ghi dữ liệu clipboard vào file; xem là dữ liệu nhạy cảm, không commit. |
| `train_model.py` | Dữ liệu training | Tạo hoặc thay model artifact trong `data/`. |
| `prepare_training_data.sh --training-dir DIR` | Thư mục chứa các category training | Trim, bỏ dòng rỗng, deduplicate không phân biệt hoa thường và chia file theo độ dài. |
| `clean_pyright_check.sh <target>` | Một file hoặc directory Python | Chạy Pyright strict và rút gọn JSON result. |

Ví dụ:

```bash
scripts/clean_pyright_check.sh src
scripts/prepare_training_data.sh --training-dir data/training --threshold 15
scripts/prepare_training_data.sh --training-dir data/training --threshold 15 --dry-run
```

Mỗi category sau khi chuẩn bị chỉ còn `short_<category>.txt` và
`long_<category>.txt`. Dòng ngắn hơn `--threshold` được ghi vào file `short`; các
dòng còn lại được ghi vào file `long`. `--training-dir` là bắt buộc.

## REQUIREMENTS

Shell scripts dùng cú pháp POSIX `sh`. Checker cần Pyright và `jq` trên `PATH`.
Script chuẩn bị data cần các POSIX utilities cùng `mktemp`. Script ghi dữ liệu hoặc
train model có thể thay đổi `data/`; kiểm tra diff trước khi stage.
