# Mục tiêu

Kiểm tra config TOML có thể dùng một root `ConfigObject` và section typed để feature
truy cập bằng `config.webblocker.block_porn`.

# Giả thuyết

Class typed theo section giúp schema rõ, kiểm tra type được và `load()` chỉ thay
config sau khi TOML mới đã hợp lệ.

# Chạy

```bash
./.pyvenv/bin/python experiments/config_prototype/prototype.py
```

# Kết quả

Prototype tạo được một `ConfigObject`, đọc `config.toml`, truy cập nested config qua
attribute và chặn sửa trực tiếp từ bên ngoài. `load()` validate trước khi thay
`webblocker`, nên config cũ được giữ nếu TOML mới lỗi.
