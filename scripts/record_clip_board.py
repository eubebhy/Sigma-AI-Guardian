#!/usr/bin/env python3
# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Ghi các giá trị clipboard mới vào một file text.

File path: `scripts/record_clip_board.py`
Input: một đối số CLI `<output_file>` là file sẽ được append.
Output: mỗi nội dung clipboard mới, khác giá trị trước đó, được ghi thành một dòng.

Nguyên lý hoạt động: script poll clipboard bằng `pyperclip` mỗi 0.3 giây. Đây là
tool hỗ trợ tạo dữ liệu train thủ công, không phải module runtime của ứng dụng.
"""

import sys
import time
import pyperclip

if len(sys.argv) != 2:
    print(f"Usage: {sys.argv[0]} <output_file>")
    sys.exit(1)

output_file = sys.argv[1]
last_text = pyperclip.paste().strip()

print(f"Watching clipboard -> {output_file}")

while True:
    try:
        text = pyperclip.paste().strip()

        if text and text != last_text:
            with open(output_file, "a", encoding="utf-8") as f:
                f.write(text + "\n")

            print(f"Added: {text}")
            last_text = text

        time.sleep(0.3)

    except KeyboardInterrupt:
        print("\nStopped.")
        break
    except Exception as e:
        print(e)
        time.sleep(1)
