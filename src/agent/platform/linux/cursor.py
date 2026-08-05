from Xlib import X
from Xlib.display import Display


class LinuxCursorOperations:
    """Điều khiển con trỏ chuột trên X11."""

    def hide_cursor(self) -> None:
        display = Display()

        try:
            root = display.screen().root
            pixmap = root.create_pixmap(1, 1, 1)

            try:
                hidden_cursor = pixmap.create_cursor(
                    pixmap,
                    (0, 0, 0),
                    (0, 0, 0),
                    0,
                    0,
                )

                try:
                    root.change_attributes(cursor=hidden_cursor)
                    display.sync()
                finally:
                    hidden_cursor.free()
            finally:
                pixmap.free()
        finally:
            display.close()

    def show_cursor(self) -> None:
        display = Display()

        try:
            root = display.screen().root
            root.change_attributes(cursor=X.NONE)
            display.sync()
        finally:
            display.close()
