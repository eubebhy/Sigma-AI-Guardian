import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


class ColoredFormatter(logging.Formatter):
    """Thêm màu RGB cho log xuất ra terminal."""

    RESET = "\033[0m"

    COLORS = {
        logging.DEBUG: "#5555ff",  # Xanh +  tim
        logging.INFO: "#55ff55",  # xanh la
        logging.WARNING: "#ffff55",  # vang
        logging.ERROR: "#ff5555",  # Do
        logging.CRITICAL: "#aa0000",  # Do dam
    }

    @staticmethod
    def _hex_to_ansi(hex_color: str) -> str:
        """Chuyển màu #RRGGBB thành ANSI true color."""

        hex_color = hex_color.lstrip("#")

        red = int(hex_color[0:2], 16)
        green = int(hex_color[2:4], 16)
        blue = int(hex_color[4:6], 16)

        return f"\033[38;2;{red};{green};{blue}m"

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        hex_color = self.COLORS.get(record.levelno)

        if hex_color is None:
            return message

        color = self._hex_to_ansi(hex_color)
        return f"{color}{message}{self.RESET}"


def configure_logging() -> None:
    """Cấu hình logging chung cho toàn bộ ứng dụng."""

    project_root = Path(__file__).resolve().parents[1]
    log_dir = project_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "app.log"

    log_format = (
        "%(asctime)s [%(levelname).1s][%(name)s] %(filename)s:%(lineno)d %(message)s"
    )

    file_formatter = logging.Formatter(
        fmt=log_format,
        datefmt="%H:%M:%S",
    )

    console_formatter = ColoredFormatter(
        fmt=log_format,
        datefmt="%H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=64 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(console_formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        handler.close()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
