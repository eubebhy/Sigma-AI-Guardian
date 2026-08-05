import ctypes

"""Win api nay tat nguyen, that vi on & off thi no co he thong level chet tiet nao do"""

_user32 = ctypes.windll.user32


class WindowsCursorOperations:
    def hide_cursor(self) -> None:
        while _user32.ShowCursor(False) >= 0:
            pass

    def show_cursor(self) -> None:
        while _user32.ShowCursor(True) < 0:
            pass
