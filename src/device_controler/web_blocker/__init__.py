"""Web blocker API cho phong tin hoc.

File path: `src/device_controler/web_blocker/__init__.py`
Input contract:
- block(file_path) va unblock(file_path) nhan path toi file domain/url, moi dong mot gia tri.
Output contract:
- Them/xoa domain trong khoi hosts nam giua marker cua ung dung.
- block() tra ve cac domain no da them moi, de cleanup chi xoa phan no so huu.
- Ghi lai hosts bang atomic write va bo qua ghi file neu noi dung khong doi.
Operating principle:
- Khoa sidecar theo hosts trong suot read-modify-write, sau do atomic replace hosts.
"""

import os
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Generator

from agent.contracts import HostsPathOperations
from agent.platform import get_default_platform_services


redirect = "127.0.0.1"
default_hoster = str(get_default_platform_services().hosts.get_hosts_path())

MODULE_PATH = Path(__file__).resolve().parent
PORN_SITES_FILE_PATH = MODULE_PATH / "porn-sites.txt"
GORE_SITES_FILE_PATH = MODULE_PATH / "gore-sites.txt"
GAME_SITES_FILE_PATH = MODULE_PATH / "game-sites.txt"
SOCIAL_MEDIA_SITES_FILE_PATH = MODULE_PATH / "social-media-sites.txt"
MESSAGING_SITES_FILE_PATH = MODULE_PATH / "messaging-sites.txt"
ENTERTAINMENT_SITES_FILE_PATH = MODULE_PATH / "entertainment-sites.txt"

DEFAULT_BLOCK_LIST_PATHS = (
    PORN_SITES_FILE_PATH,
    GORE_SITES_FILE_PATH,
    GAME_SITES_FILE_PATH,
    SOCIAL_MEDIA_SITES_FILE_PATH,
    MESSAGING_SITES_FILE_PATH,
    ENTERTAINMENT_SITES_FILE_PATH,
)

START_MARKER = "# SAG - Web block list start"
END_MARKER = "# SAG - Web block list end"


def _domain_from_line(line: str) -> str | None:
    # cat comment, lay domain sach
    value = line.split("#", 1)[0].strip().lower()
    if not value:
        return None
    # bo scheme, path, port, giu host
    domain = value.split("://", 1)[-1].split("/", 1)[0]
    return domain.split(":", 1)[0] or None


def _load_domains(file_path: str | Path) -> list[str]:
    domains: set[str] = set()
    # doc list mot lan, dedupe trong ram
    for line in Path(file_path).read_text(encoding="utf-8").splitlines():
        domain = _domain_from_line(line)
        if domain is not None:
            domains.add(domain)
    return sorted(domains)


def _parse_block_lines(lines: list[str]) -> list[str]:
    domains: set[str] = set()
    # chi nhan dong redirect cua minh
    for line in lines:
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2 and parts[0] == redirect:
            domains.add(parts[1].lower())
    return sorted(domains)


def _split_hosts(hosts_text: str) -> tuple[str, list[str], str]:
    # tach hosts thanh before/block/after
    before, marker, rest = hosts_text.partition(START_MARKER)
    if not marker:
        return hosts_text.rstrip("\n"), [], ""
    block_text, end_marker, after = rest.partition(END_MARKER)
    if not end_marker:
        raise ValueError("Web blocker marker is broken")
    return before.rstrip("\n"), _parse_block_lines(block_text.splitlines()), after


def _render_hosts(before: str, blocked_domains: list[str], after: str) -> str:
    # ghep lai block moi vao hosts cu
    lines = [before, START_MARKER]
    lines.extend(f"{redirect} {domain}" for domain in blocked_domains)
    lines.append(END_MARKER)
    return "\n".join(lines).lstrip("\n") + after


def _atomic_write(path: Path, content: str) -> None:
    # ghi temp cung thu muc roi swap
    with NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as file:
        file.write(content)
        temp_path = Path(file.name)
    try:
        # giu permission hosts cu
        os.chmod(temp_path, path.stat().st_mode)
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


@contextmanager
def _hosts_lock(hosts_path: Path) -> Generator[None, None, None]:
    """Khoa sidecar de cac process SAG cung serialize hosts transaction."""

    lock_path = hosts_path.with_name(f".{hosts_path.name}.sag.lock")
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


def _update_hosts(
    file_path: str | Path,
    is_blocking: bool,
    hosts_operations: HostsPathOperations | None = None,
) -> set[str]:
    hosts_path = (
        hosts_operations.get_hosts_path()
        if hosts_operations is not None
        else Path(default_hoster)
    )
    domains = set(_load_domains(file_path))
    with _hosts_lock(hosts_path):
        hosts_text = hosts_path.read_text(encoding="utf-8")
        before, current_domains, after = _split_hosts(hosts_text)
        blocked_domains = set(current_domains)
        added_domains: set[str] = set()
        if is_blocking:
            added_domains = domains.difference(blocked_domains)
            blocked_domains.update(domains)
        else:
            blocked_domains.difference_update(domains)
        new_hosts_text = _render_hosts(before, sorted(blocked_domains), after)
        if new_hosts_text != hosts_text:
            _atomic_write(hosts_path, new_hosts_text)
    return added_domains


def block(file_path: str | Path) -> set[str]:
    # them list vao block state
    return _update_hosts(file_path, is_blocking=True)


def unblock(file_path: str | Path) -> None:
    # go list khoi block state
    _update_hosts(file_path, is_blocking=False)


__all__ = [
    "block",
    "unblock",
    "PORN_SITES_FILE_PATH",
    "GORE_SITES_FILE_PATH",
    "GAME_SITES_FILE_PATH",
    "SOCIAL_MEDIA_SITES_FILE_PATH",
    "MESSAGING_SITES_FILE_PATH",
    "ENTERTAINMENT_SITES_FILE_PATH",
    "DEFAULT_BLOCK_LIST_PATHS",
]
