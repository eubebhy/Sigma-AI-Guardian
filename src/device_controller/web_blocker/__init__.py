"""Primitive hosts cho WebBlocker.

File path: `src/device_controller/web_blocker/__init__.py`.
Input: domain iterable và tên marker SAG hợp lệ.
Output: số domain đã thêm hoặc gỡ trong đúng marker SAG được yêu cầu.
Nguyên lý: đọc hosts và source list theo stream, ghi temporary file rồi atomic replace
một lần trong mỗi operation; code không giữ toàn bộ category list trong RAM.
"""

import os
from collections.abc import Generator, Iterable
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TextIO, cast
from urllib.parse import urlsplit

from agent.platform_protocols import HostsPathOperations
from agent.platform import get_default_platform_services


LOOPBACK_ADDRESS = "127.0.0.1"
DEFAULT_HOSTS_PATH = str(get_default_platform_services().hosts.get_hosts_path())

MODULE_PATH = Path(__file__).resolve().parent
PORN_SITES_FILE_PATH = MODULE_PATH / "porn-sites.txt"
GORE_SITES_FILE_PATH = MODULE_PATH / "gore-sites.txt"
GAME_SITES_FILE_PATH = MODULE_PATH / "game-sites.txt"
SOCIAL_MEDIA_SITES_FILE_PATH = MODULE_PATH / "social-media-sites.txt"
MESSAGING_SITES_FILE_PATH = MODULE_PATH / "messaging-sites.txt"
ENTERTAINMENT_SITES_FILE_PATH = MODULE_PATH / "entertainment-sites.txt"

CATEGORY_PATHS = {
    "porn": PORN_SITES_FILE_PATH,
    "gore": GORE_SITES_FILE_PATH,
    "game": GAME_SITES_FILE_PATH,
    "social": SOCIAL_MEDIA_SITES_FILE_PATH,
    "messaging": MESSAGING_SITES_FILE_PATH,
    "entertainment": ENTERTAINMENT_SITES_FILE_PATH,
}

MARKER_PREFIX = "# SAG webblock "


def _validate_marker(marker: str) -> None:
    if not marker or not all(
        character.isascii()
        and (character.isalnum() or character in {":", "-", "_"})
        for character in marker
    ):
        raise ValueError(f"Invalid web blocker marker: {marker!r}")


def normalize_domain(value: str) -> str | None:
    """Chuẩn hóa một domain hoặc URL thành hostname lowercase."""

    cleaned = value.split("#", 1)[0].strip().lower()
    if not cleaned or any(character.isspace() or ord(character) < 32 for character in cleaned):
        return None
    parsed = urlsplit(cleaned if "://" in cleaned else f"//{cleaned}")
    if parsed.username is not None or parsed.password is not None:
        return None
    hostname = parsed.hostname
    if hostname is None:
        return None
    normalized = hostname.rstrip(".")
    labels = normalized.split(".")
    if len(normalized) > 253 or any(
        not label
        or len(label) > 63
        or label.startswith("-")
        or label.endswith("-")
        or not all(character.isascii() and (character.isalnum() or character == "-") for character in label)
        for label in labels
    ):
        return None
    return normalized


def _marker_start(marker: str) -> str:
    _validate_marker(marker)
    return f"{MARKER_PREFIX}{marker} start"


def _marker_end(marker: str) -> str:
    _validate_marker(marker)
    return f"{MARKER_PREFIX}{marker} end"


def _marker_name_from_start(line: str) -> str | None:
    stripped = line.strip()
    if not stripped.startswith(MARKER_PREFIX) or not stripped.endswith(" start"):
        return None
    marker = stripped[len(MARKER_PREFIX) : -len(" start")]
    return marker or None


def _is_marker_end(line: str, marker: str) -> bool:
    return line.strip() == _marker_end(marker)


def _domain_from_hosts_line(line: str) -> str | None:
    parts = line.strip().split(maxsplit=1)
    if len(parts) != 2 or parts[0] != LOOPBACK_ADDRESS:
        return None
    return parts[1].lower()


def _hosts_path(operations: HostsPathOperations | Path | None) -> Path:
    if isinstance(operations, Path):
        return operations
    if operations is not None:
        return operations.get_hosts_path()
    return Path(DEFAULT_HOSTS_PATH)


@contextmanager
def file_lock(path: Path) -> Generator[None, None, None]:
    """Khóa sidecar để serialize transaction file giữa các process SAG."""

    lock_path = path.with_name(f".{path.name}.sag.lock")
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        if os.name == "nt":
            import msvcrt

            lock_file.seek(0)
            lock_file.write("0")
            lock_file.flush()
            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


@contextmanager
def _temporary_hosts_file(path: Path) -> Generator[tuple[TextIO, Path], None, None]:
    file = NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    )
    temp_path = Path(file.name)
    try:
        yield cast(TextIO, file), temp_path
    finally:
        file.close()
        temp_path.unlink(missing_ok=True)


def _commit_hosts_file(hosts_path: Path, temp_path: Path) -> None:
    os.chmod(temp_path, hosts_path.stat().st_mode)
    os.replace(temp_path, hosts_path)


def _copy_hosts(source: TextIO, target: TextIO, marker: str) -> tuple[bool, bool]:
    ended_with_newline = True
    marker_count = 0
    marker_open = False
    for line in source:
        target.write(line)
        ended_with_newline = line.endswith("\n")
        if line.strip() == _marker_start(marker):
            marker_count += 1
            marker_open = True
        elif marker_open and _is_marker_end(line, marker):
            marker_open = False
    if marker_open or marker_count > 1:
        raise ValueError(f"Web blocker marker is broken: {marker}")
    return ended_with_newline, marker_count == 1


def _append_marker(
    hosts_path: Path,
    marker: str,
    domains: Iterable[str],
) -> int:
    with _temporary_hosts_file(hosts_path) as (target, temp_path):
        with hosts_path.open(encoding="utf-8") as source:
            ended_with_newline, marker_exists = _copy_hosts(source, target, marker)
        if marker_exists:
            return 0
        if hosts_path.stat().st_size and not ended_with_newline:
            target.write("\n")
        target.write(f"{_marker_start(marker)}\n")
        count = 0
        for domain in domains:
            target.write(f"{LOOPBACK_ADDRESS} {domain}\n")
            count += 1
        target.write(f"{_marker_end(marker)}\n")
        target.flush()
        _commit_hosts_file(hosts_path, temp_path)
    return count


def marker_exists(hosts_path: Path, marker: str) -> bool:
    """Kiểm tra marker tồn tại và nguyên vẹn mà không ghi hosts."""

    with file_lock(hosts_path):
        marker_count = 0
        marker_open = False
        with hosts_path.open(encoding="utf-8") as source:
            for line in source:
                if line.strip() == _marker_start(marker):
                    marker_count += 1
                    marker_open = True
                elif marker_open and _is_marker_end(line, marker):
                    marker_open = False
        if marker_open or marker_count > 1:
            raise ValueError(f"Web blocker marker is broken: {marker}")
        return marker_count == 1


def marker_names(hosts_path: Path) -> frozenset[str]:
    """Trả marker SAG nguyên vẹn; marker lồng hoặc hỏng sẽ raise ValueError."""

    with file_lock(hosts_path):
        names: set[str] = set()
        current_marker: str | None = None
        with hosts_path.open(encoding="utf-8") as source:
            for line in source:
                marker = _marker_name_from_start(line)
                if marker is not None:
                    if current_marker is not None or marker in names:
                        raise ValueError("Web blocker markers are broken")
                    names.add(marker)
                    current_marker = marker
                    continue
                if current_marker is not None and _is_marker_end(line, current_marker):
                    current_marker = None
        if current_marker is not None:
            raise ValueError("Web blocker markers are broken")
        return frozenset(names)


def block(
    domains: Iterable[str],
    marker: str,
    hosts_operations: HostsPathOperations | Path | None = None,
) -> int:
    """Thêm domain vào marker mới; marker đã có sẽ không bị ghi lại."""

    hosts_path = _hosts_path(hosts_operations)
    normalized = {domain for value in domains if (domain := normalize_domain(value))}
    with file_lock(hosts_path):
        return _append_marker(hosts_path, marker, sorted(normalized))


def block_file(
    file_path: Path,
    marker: str,
    allowed_domains: frozenset[str],
    hosts_path: Path,
) -> int:
    with file_lock(hosts_path):
        def domains() -> Generator[str, None, None]:
            with file_path.open(encoding="utf-8") as source:
                for line in source:
                    domain = normalize_domain(line)
                    if domain is not None and domain not in allowed_domains:
                        yield domain

        return _append_marker(hosts_path, marker, domains())


def _remove_marker(hosts_path: Path, marker: str) -> int:
    with _temporary_hosts_file(hosts_path) as (target, temp_path):
        removed = 0
        skipping = False
        found = False
        with hosts_path.open(encoding="utf-8") as source:
            for line in source:
                if skipping:
                    if _is_marker_end(line, marker):
                        skipping = False
                    else:
                        removed += int(_domain_from_hosts_line(line) is not None)
                    continue
                if line.strip() == _marker_start(marker):
                    if found:
                        raise ValueError(f"Web blocker marker is duplicated: {marker}")
                    skipping = True
                    found = True
                    continue
                target.write(line)
        if skipping:
            raise ValueError(f"Web blocker marker is broken: {marker}")
        if not found:
            return 0
        target.flush()
        _commit_hosts_file(hosts_path, temp_path)
    return removed


def unblock(
    marker: str,
    hosts_operations: HostsPathOperations | Path | None = None,
) -> int:
    """Xóa toàn bộ marker và domain của một policy/category."""

    hosts_path = _hosts_path(hosts_operations)
    with file_lock(hosts_path):
        return _remove_marker(hosts_path, marker)


def replace_marker(hosts_path: Path, marker: str, domains: Iterable[str]) -> int:
    """Thay marker custom trong một hosts transaction được khóa."""

    normalized = sorted(
        {domain for value in domains if (domain := normalize_domain(value))}
    )
    with file_lock(hosts_path):
        return _replace_marker(hosts_path, marker, normalized)


def _replace_marker(hosts_path: Path, marker: str, domains: list[str]) -> int:
    with _temporary_hosts_file(hosts_path) as (target, temp_path):
        found = False
        skipping = False
        old_count = 0
        with hosts_path.open(encoding="utf-8") as source:
            for line in source:
                if skipping:
                    if _is_marker_end(line, marker):
                        skipping = False
                    else:
                        old_count += int(_domain_from_hosts_line(line) is not None)
                    continue
                if line.strip() == _marker_start(marker):
                    if found:
                        raise ValueError(f"Web blocker marker is duplicated: {marker}")
                    found = True
                    skipping = True
                    continue
                target.write(line)
        if skipping:
            raise ValueError(f"Web blocker marker is broken: {marker}")
        if domains:
            if found or hosts_path.stat().st_size:
                target.write("\n")
            target.write(f"{_marker_start(marker)}\n")
            for domain in domains:
                target.write(f"{LOOPBACK_ADDRESS} {domain}\n")
            target.write(f"{_marker_end(marker)}\n")
        if not found and not domains:
            return 0
        target.flush()
        _commit_hosts_file(hosts_path, temp_path)
    return old_count


def remove_domains(hosts_path: Path, domains: frozenset[str]) -> int:
    """Gỡ domain khỏi mọi marker SAG trong một hosts transaction được khóa."""

    with file_lock(hosts_path):
        return _remove_domains(hosts_path, domains)


def _remove_domains(hosts_path: Path, domains: frozenset[str]) -> int:
    with _temporary_hosts_file(hosts_path) as (target, temp_path):
        current_marker: str | None = None
        removed = 0
        with hosts_path.open(encoding="utf-8") as source:
            for line in source:
                marker = _marker_name_from_start(line)
                if marker is not None:
                    if current_marker is not None:
                        raise ValueError(
                            f"Web blocker marker is broken: {current_marker}"
                        )
                    current_marker = marker
                    target.write(line)
                    continue
                if current_marker is not None and _is_marker_end(line, current_marker):
                    current_marker = None
                    target.write(line)
                    continue
                domain = _domain_from_hosts_line(line)
                if current_marker is not None and domain in domains:
                    removed += 1
                    continue
                target.write(line)
        if current_marker is not None:
            raise ValueError(f"Web blocker marker is broken: {current_marker}")
        if not removed:
            return 0
        target.flush()
        _commit_hosts_file(hosts_path, temp_path)
    return removed


def remove_all_markers(hosts_path: Path) -> int:
    """Gỡ mọi marker SAG trong một hosts transaction được khóa."""

    with file_lock(hosts_path):
        return _remove_all_markers(hosts_path)


def _remove_all_markers(hosts_path: Path) -> int:
    with _temporary_hosts_file(hosts_path) as (target, temp_path):
        current_marker: str | None = None
        removed = 0
        found = False
        with hosts_path.open(encoding="utf-8") as source:
            for line in source:
                marker = _marker_name_from_start(line)
                if marker is not None:
                    if current_marker is not None:
                        raise ValueError(
                            f"Web blocker marker is broken: {current_marker}"
                        )
                    current_marker = marker
                    found = True
                    continue
                if current_marker is not None:
                    if _is_marker_end(line, current_marker):
                        current_marker = None
                    else:
                        removed += int(_domain_from_hosts_line(line) is not None)
                    continue
                target.write(line)
        if current_marker is not None:
            raise ValueError(f"Web blocker marker is broken: {current_marker}")
        if not found:
            return 0
        target.flush()
        _commit_hosts_file(hosts_path, temp_path)
    return removed


from device_controller.web_blocker.manager import WebBlocker

__all__ = [
    "WebBlocker",
    "block",
    "normalize_domain",
    "unblock",
]
