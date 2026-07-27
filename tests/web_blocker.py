"""Manual test web blocker bang system hosts mac dinh, khong dung hosts fake."""

import argparse
import socket
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from device_controler import web_blocker


def _blocked_domains() -> set[str]:
    """Lay cac domain dang bi SAG block trong system hosts mac dinh."""

    # system hosts -> block state hien tai
    hosts = Path(web_blocker.default_hoster).read_text(encoding="utf-8")
    _, marker, rest = hosts.partition(web_blocker.START_MARKER)
    if not marker:
        return set()
    section, end_marker, _ = rest.partition(web_blocker.END_MARKER)
    if not end_marker:
        raise AssertionError("Web blocker marker is broken")
    # bo redirect, giu domain
    return {
        line.split()[1]
        for line in section.splitlines()
        if line.strip().startswith(f"{web_blocker.redirect} ")
    }


def _resolved_ips(domain: str) -> set[str]:
    """Resolve domain bang resolver he thong de check hosts co tac dung."""

    # resolver he thong doc system hosts
    return {
        address
        for *_, sockaddr in socket.getaddrinfo(domain, None)
        if isinstance((address := sockaddr[0]), str)
    }


def _domain_from_url(url: str) -> str:
    """Rut domain tu url/host CLI de dem vao resolver."""

    # url -> host thuan
    return url.split("://", 1)[-1].split("/", 1)[0].split(":", 1)[0].lower()


def _block_default_lists() -> None:
    """Block toan bo blocklist co san cua he thong."""

    for block_list_path in web_blocker.DEFAULT_BLOCK_LIST_PATHS:
        web_blocker.block(block_list_path)


def _unblock_default_lists() -> None:
    """Unblock toan bo blocklist co san cua he thong."""

    for block_list_path in web_blocker.DEFAULT_BLOCK_LIST_PATHS:
        web_blocker.unblock(block_list_path)


def _assert_blocked(domain: str) -> None:
    """Check hosts state va resolver deu da block domain."""

    # state truoc, resolver sau
    assert domain in _blocked_domains()
    assert web_blocker.redirect in _resolved_ips(domain)


def test_blocker_edits_dev_hosts(domain: str = "pornhub.com") -> None:
    """Manual: block default list, verify domain, roi cleanup."""

    blocked = False
    try:
        # block bang list he thong
        _block_default_lists()
        blocked = True
        _assert_blocked(domain)
    finally:
        # da ghi thi phai go
        if blocked:
            _unblock_default_lists()

    assert domain not in _blocked_domains()


def _build_parser() -> argparse.ArgumentParser:
    """Tao CLI flags cho automatic/block/unblock/custom url."""

    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--automatic", action="store_true")
    mode.add_argument("--block", action="store_true")
    mode.add_argument("--unblock", action="store_true")
    parser.add_argument("--url", default="pornhub.com")
    return parser


def main() -> None:
    """Chon flow CLI va chay tren system hosts mac dinh."""

    args = _build_parser().parse_args()
    print("WARNING: This manual script modifies the default system hosts file.")
    domain = _domain_from_url(str(args.url))
    if args.block:
        _block_default_lists()
        _assert_blocked(domain)
    elif args.unblock:
        _unblock_default_lists()
        assert domain not in _blocked_domains()
    else:
        test_blocker_edits_dev_hosts(domain)


if __name__ == "__main__":
    main()
    print("PASS: web blocker edits dev hosts")
