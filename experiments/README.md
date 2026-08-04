```text
project/
├── src/
├── tests/
├── docs/
├── experiments/
│   ├── README.md
│   ├── x11_cursor/
│   ├── new_classifier/
│   └── thread_model/
└── tmp/
```

## Phân biệt

* `tests/`: test tự động cho code thật. Nên commit.
* `experiments/` hoặc `playground/`: thử ý tưởng, benchmark, prototype. Có thể commit chọn lọc.
* `tmp/`: file tạm, output, dữ liệu rác. Nên `.gitignore`.

```gitignore
/tmp/
/experiments/**/output/
/experiments/**/.cache/
```

Không nên ignore toàn bộ `experiments/` ngay từ đầu. Một thử nghiệm hữu ích thường cần giữ lại:

```text
experiments/new_architecture/
├── README.md
├── prototype.py
├── benchmark.py
└── results.md
```

`README.md` chỉ cần ghi:

```md
# Mục tiêu

Kiểm tra kiến trúc X có giải quyết Y không.

# Giả thuyết

X nhanh hơn hoặc đơn giản hơn Y.

# Chạy

python prototype.py

# Kết quả

Thành công / thất bại và lý do.
```

Workflow hợp lý:

```text
ý tưởng mới
→ experiments/<name>/
→ prototype độc lập
→ đo/test
→ thất bại: xóa hoặc lưu kết luận
→ thành công: refactor vào src/
→ viết test thật trong tests/
→ xóa prototype thừa
```

Tên thư mục phù hợp nhất:

```text
experiments/
playground/
sandbox/
spikes/
research/
```

Với dự án lớn, `experiments/` rõ nghĩa và dễ quản lý nhất.
