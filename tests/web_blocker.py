"""Test an toan cho web blocker.

File path: `tests/web_blocker.py`
Input contract:
- Chay truc tiep bang `python3 tests/web_blocker.py`.
Output contract:
- Test block/unblock list mac dinh va custom tren hosts file tam, khong dung `/etc/hosts`.
Operating principle:
- Kiem tra domain trong block section tro ve localhost va ket noi localhost that bai.
"""

import socket
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from device_controler import web_blocker


def _blocked_domains(hosts_path: Path) -> set[str]:
    # doc hosts tam, chi lay block state cua SAG
    hosts = hosts_path.read_text(encoding="utf-8")
    section = hosts.split(web_blocker.START_MARKER, 1)[1].split(
        web_blocker.END_MARKER,
        1,
    )[0]
    # section -> domain set, bo redirect
    return {
        line.split()[1] for line in section.splitlines() if line.startswith("127.0.0.1")
    }


def _assert_connection_blocked(hosts_path: Path, domain: str) -> None:
    # truoc het domain phai co trong hosts tam
    assert domain in _blocked_domains(hosts_path)
    try:
        # domain bi day ve localhost nen port rong phai fail
        socket.create_connection(("127.0.0.1", 9), timeout=0.1)
    except OSError:
        return
    raise AssertionError("Blocked domain unexpectedly connected to localhost")


def test_default_and_custom_lists_use_temp_hosts() -> None:
    # giu hosts that, test chi doi sang file tam
    old_hoster = web_blocker.default_hoster
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        hosts_path = temp_path / "hosts"
        custom_path = temp_path / "custom-sites.txt"
        # seed dong an toan de check khong bi pha
        hosts_path.write_text("127.0.0.1 safe.local\n", encoding="utf-8")
        # custom co url day du, blocker se rut ve domain
        custom_path.write_text("https://custom.local/path\n", encoding="utf-8")
        web_blocker.default_hoster = str(hosts_path)
        try:
            # nap het list mac dinh vao hosts tam
            for default_path in web_blocker.DEFAULT_BLOCK_LIST_PATHS:
                web_blocker.block(default_path)
            # nap them list custom de test path nguoi dung
            web_blocker.block(custom_path)
            assert "127.0.0.1 safe.local\n" in hosts_path.read_text(encoding="utf-8")
            # check mau: porn/gore/default va custom deu bi day localhost
            _assert_connection_blocked(hosts_path, "pornhub.com")
            _assert_connection_blocked(hosts_path, "bestgore.com")
            _assert_connection_blocked(hosts_path, "custom.local")
            # go custom, default list van con
            web_blocker.unblock(custom_path)
            assert "custom.local" not in _blocked_domains(hosts_path)
        finally:
            # tra lai hosts path that ke ca test fail
            web_blocker.default_hoster = old_hoster


if __name__ == "__main__":
    test_default_and_custom_lists_use_temp_hosts()
    print("PASS: default and custom web block lists")
