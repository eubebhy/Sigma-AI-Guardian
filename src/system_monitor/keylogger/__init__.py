"""Theo dõi phím đã gõ để gom thành chuỗi text tạm thời.

File path: `src/system_monitor/keylogger/__init__.py`
Input: tên phím và event type từ `utils.input_controller.listen_keys()`.
Output: cập nhật state module `typing_string` và `typed_strings` trong bộ nhớ.

Nguyên lý hoạt động: chỉ xử lý event `down` và `press`, nối tên phím vào chuỗi
đang gõ, rồi đẩy chuỗi cũ vào `typed_strings` khi khoảng cách thời gian vượt quá
ngưỡng. Đây là state tạm trong process, chưa phải storage bền vững.
"""

import time
from collections import deque

from utils.input_controller import keyboard, listen_keys, KeyboardEvent, KeyListener


# Config
# TODO: After finish config system, add this:
max_typing_string_lenth = 50  # Characters
max_typed_word_length = 50  # Words

max_typing_time_gap = 3.67
last_press_time: float = 0


# User pressing key
# Add key to pressed_keys
# if user press space bar or do something that mean type new words
# Remove all key pressed_keys and add new words to typed_words


"""
Why i use classmethod here?
-> Because no one gonna create a lot of Keylogger on a single device
But i also need to manage listener so class + @classmethod was the best choice
"""


class KeyLogger:
    _listener: KeyListener | None = None

    _typing_string: deque[str] = deque(
        maxlen=max_typing_string_lenth
    )  # Used to temp processing pressing character

    _typed_strings: deque[str] = deque(
        maxlen=max_typed_word_length
    )  # Used to storage typed words

    @classmethod
    def start(cls):
        if cls._listener is None:
            cls._listener = listen_keys(callback=cls._keylogger, typeable_only=True)

    @classmethod
    def stop(cls):
        if cls._listener is not None:
            cls._listener.stop()
            cls._listener = None

    @classmethod
    def _reset_buffer(cls) -> None:
        cls._typed_strings.append("".join(cls._typing_string))
        cls._typing_string.clear()  # method cua deque

    @classmethod
    def _keylogger(cls, e: KeyboardEvent):
        """Nhận một keyboard event đã normalize và cập nhật buffer đang gõ."""

        # e.text  = Noi dung that su duoc go
        # e.name = ten cua phim duoc bam
        # e.event_type = up / down/ press

        if not e.event_type in ["down", "press"]:
            return

        last_press_time = time.time()

        if e.name == keyboard.delete:
            cls._typing_string.pop()  # xOA PHan tu cuoi cung
            return

        not_typeable = e.text is None
        timeout = time.time() - last_press_time > max_typing_time_gap

        if timeout:
            cls._reset_buffer()
            return

        if not_typeable:
            cls._reset_buffer()
            return

        cls._typing_string.append(e.text)

    @classmethod
    def get_new_typed_words(cls) -> list[str]:
        """Tra ve nhung tu da duoc go moi  nhat, ko tra la nhung tu da go truoc day"""
        output = list(cls._typed_strings)
        cls._typed_strings.clear()
        return output
