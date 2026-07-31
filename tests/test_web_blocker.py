"""Kiểm thử web blocker bằng hosts tạm và mode thật có chủ đích.

File path: ``tests/test_web_blocker.py``.
Input: safe mode kiểm tra hosts tạm; mode real nhận một trong các lệnh bên dưới.
Output: mode real in trạng thái block, kết quả DNS và trạng thái cleanup.
Nguyên lý: ``automatic`` block toàn bộ list mặc định, kiểm tra domain đã chọn rồi chỉ
xóa domain do nó thêm trong ``finally``, giữ nguyên state SAG có từ trước. ``block``
chỉ được giữ thay đổi khi có xác nhận rõ.

Real usage dùng bởi ``--help``:
``./.pyvenv/bin/python tests/test_web_blocker.py real automatic [URL]``
``./.pyvenv/bin/python tests/test_web_blocker.py real block --keep-changes``
``./.pyvenv/bin/python tests/test_web_blocker.py real unblock``

Prerequisites: chạy trên máy test cục bộ, có quyền ghi system hosts và DNS resolver
phải đọc hosts. ``automatic`` dùng ``pornhub.com`` nếu không truyền URL; URL tùy chọn
phải là domain có trong các list mặc định để DNS verification pass.
Side effects: ``automatic`` tạm sửa marker section SAG trong hosts rồi cleanup phần
nó thêm; nó có thể làm gián đoạn truy cập domain trong lúc chạy.
``block --keep-changes`` giữ các domain list mặc định trong hosts cho đến khi chạy
``unblock``. Không chạy mode real trong suite an toàn.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import multiprocessing
from pathlib import Path
import socket
import sys
import traceback
from tempfile import TemporaryDirectory
import threading
from typing import Any, NoReturn
import unittest
from unittest.mock import patch

from test_support import add_source_path, run_module, test_modes


add_source_path()

from device_controler import web_blocker


class _RealArgumentParser(argparse.ArgumentParser):
    """Parser real trả lỗi để safe test không dừng process."""

    def error(self, message: str) -> NoReturn:
        raise ValueError(message)


def _create_real_parser() -> argparse.ArgumentParser:
    parser = _RealArgumentParser(add_help=False)
    commands = parser.add_subparsers(dest="command", required=True)
    automatic = commands.add_parser("automatic", add_help=False)
    automatic.add_argument("url", nargs="?", default="pornhub.com")
    block = commands.add_parser("block", add_help=False)
    block.add_argument("--keep-changes", action="store_true", required=True)
    commands.add_parser("unblock", add_help=False)
    return parser


def _parse_real_arguments(arguments: Sequence[str]) -> argparse.Namespace | None:
    """Đọc command real mà không chạy hosts hay DNS."""

    try:
        return _create_real_parser().parse_args(arguments)
    except (argparse.ArgumentError, ValueError):
        return None


def _blocked_domains(hosts_path: Path) -> set[str]:
    hosts = hosts_path.read_text(encoding="utf-8")
    _, marker, rest = hosts.partition(web_blocker.START_MARKER)
    if not marker:
        return set()
    section, end_marker, _ = rest.partition(web_blocker.END_MARKER)
    if not end_marker:
        raise AssertionError("Web blocker marker is broken")
    return {
        line.split()[1]
        for line in section.splitlines()
        if line.strip().startswith(f"{web_blocker.redirect} ")
    }


def _resolved_ips(domain: str) -> set[str]:
    return {
        address
        for *_, sockaddr in socket.getaddrinfo(domain, None)
        if isinstance((address := sockaddr[0]), str)
    }


def _block_default_lists() -> set[str]:
    added_domains: set[str] = set()
    for block_list_path in web_blocker.DEFAULT_BLOCK_LIST_PATHS:
        added_domains.update(web_blocker.block(block_list_path))
    return added_domains


def _unblock_default_lists() -> None:
    cleanup_error: Exception | None = None
    for block_list_path in web_blocker.DEFAULT_BLOCK_LIST_PATHS:
        try:
            web_blocker.unblock(block_list_path)
        except Exception as error:
            cleanup_error = cleanup_error or error
    if cleanup_error is not None:
        raise cleanup_error


def _unblock_domains(domains: set[str]) -> None:
    if not domains:
        return
    with TemporaryDirectory() as directory:
        domains_path = Path(directory) / "automatic-domains.txt"
        domains_path.write_text("\n".join(sorted(domains)), encoding="utf-8")
        web_blocker.unblock(domains_path)


def _concurrent_block_worker(
    hosts_path_string: str,
    domains_path_string: str,
    barrier: Any,
) -> None:
    hosts_path = Path(hosts_path_string)
    original_read_text = Path.read_text

    def read_text(path: Path, *args: Any, **kwargs: Any) -> str:
        content = original_read_text(path, *args, **kwargs)
        if path == hosts_path:
            try:
                barrier.wait(timeout=2)
            except threading.BrokenBarrierError:
                pass
        return content

    with (
        patch.object(web_blocker, "default_hoster", hosts_path_string),
        patch.object(Path, "read_text", new=read_text),
    ):
        web_blocker.block(domains_path_string)


def _verification_domain(url: str) -> str | None:
    value = url.strip().lower().split("://", 1)[-1]
    domain = value.split("/", 1)[0].split(":", 1)[0]
    return domain or None


def _run_automatic(url: str) -> int:
    domain = _verification_domain(url)
    if domain is None:
        print("Invalid verification URL", file=sys.stderr)
        return 2
    result = 0
    added_domains: set[str] = set()
    try:
        print(f"Block: applying {len(web_blocker.DEFAULT_BLOCK_LIST_PATHS)} default lists")
        added_domains = _block_default_lists()
        blocked = domain in _blocked_domains(Path(web_blocker.default_hoster))
        print(f"Block: {domain} is {'present' if blocked else 'missing'} in hosts")
        resolved_ips = _resolved_ips(domain)
        dns_blocked = web_blocker.redirect in resolved_ips
        print(f"DNS: {domain} -> {sorted(resolved_ips)} | blocked={dns_blocked}")
        result = 0 if blocked and dns_blocked else 1
    except Exception as error:
        print(f"Action failed: {error}", file=sys.stderr)
        traceback.print_exc()
        result = 1
    finally:
        print("Cleanup: removing automatic domains")
        try:
            _unblock_domains(added_domains)
            print("Cleanup: complete")
        except Exception as error:
            print(f"Cleanup failed: {error}", file=sys.stderr)
            traceback.print_exc()
            result = 1
    return result


def run_real(arguments: Sequence[str]) -> int:
    """Chạy thao tác hosts thật chỉ khi caller chọn mode real rõ ràng."""

    command = _parse_real_arguments(arguments)
    if command is None:
        print("Invalid real command", file=sys.stderr)
        return 2
    if command.command == "automatic":
        return _run_automatic(command.url)
    try:
        if command.command == "block":
            print(f"Block: applying {len(web_blocker.DEFAULT_BLOCK_LIST_PATHS)} default lists")
            _block_default_lists()
            print("Block: changes kept; run real unblock to remove them")
        else:
            print("Cleanup: removing default lists")
            _unblock_default_lists()
            print("Cleanup: complete")
    except Exception as error:
        print(f"Action failed: {error}", file=sys.stderr)
        traceback.print_exc()
        return 1
    return 0


class WebBlockerTests(unittest.TestCase):
    """Web blocker chỉ ghi hosts thật trong mode real rõ ràng."""

    @test_modes("fake", "smoke")
    def test_block_and_unblock_use_temporary_hosts(self) -> None:
        with TemporaryDirectory() as directory:
            directory_path = Path(directory)
            hosts_path = directory_path / "hosts"
            domains_path = directory_path / "domains.txt"
            hosts_path.write_text("127.0.0.1 localhost\n", encoding="utf-8")
            domains_path.write_text(
                "Example.com\nhttps://second.example/path\nexample.com\n",
                encoding="utf-8",
            )
            with patch.object(web_blocker, "default_hoster", str(hosts_path)):
                web_blocker.block(domains_path)
                self.assertEqual(
                    _blocked_domains(hosts_path),
                    {"example.com", "second.example"},
                )
                web_blocker.unblock(domains_path)

            self.assertEqual(_blocked_domains(hosts_path), set())
            self.assertIn("127.0.0.1 localhost", hosts_path.read_text(encoding="utf-8"))

    @test_modes("fake")
    def test_parse_real_automatic_accepts_default_and_configured_url(self) -> None:
        default_command = _parse_real_arguments(("automatic",))
        configured_command = _parse_real_arguments(
            ("automatic", "https://example.com/path"),
        )

        self.assertIsNotNone(default_command)
        self.assertIsNotNone(configured_command)
        assert default_command is not None
        assert configured_command is not None
        self.assertEqual(default_command.url, "pornhub.com")
        self.assertEqual(configured_command.url, "https://example.com/path")

    @test_modes("fake")
    def test_parse_real_block_requires_keep_changes(self) -> None:
        blocked_command = _parse_real_arguments(("block", "--keep-changes"))

        self.assertIsNone(_parse_real_arguments(("block",)))
        self.assertIsNotNone(blocked_command)
        assert blocked_command is not None
        self.assertTrue(blocked_command.keep_changes)
        unblock_command = _parse_real_arguments(("unblock",))
        self.assertIsNotNone(unblock_command)
        assert unblock_command is not None
        self.assertEqual(unblock_command.command, "unblock")

    @test_modes("fake", "smoke")
    def test_automatic_preserves_existing_persistent_block(self) -> None:
        with TemporaryDirectory() as directory:
            output = StringIO()
            directory_path = Path(directory)
            hosts_path = directory_path / "hosts"
            persistent_path = directory_path / "persistent.txt"
            automatic_path = directory_path / "automatic.txt"
            hosts_path.write_text("127.0.0.1 localhost\n", encoding="utf-8")
            persistent_path.write_text("persistent.example\n", encoding="utf-8")
            automatic_path.write_text(
                "persistent.example\nautomatic.example\n",
                encoding="utf-8",
            )
            with (
                patch.object(web_blocker, "default_hoster", str(hosts_path)),
                patch.object(web_blocker, "DEFAULT_BLOCK_LIST_PATHS", (automatic_path,)),
                patch(__name__ + "._resolved_ips", return_value={web_blocker.redirect}),
                redirect_stdout(output),
            ):
                web_blocker.block(persistent_path)
                result = _run_automatic("automatic.example")

            self.assertEqual(result, 0)
            self.assertEqual(_blocked_domains(hosts_path), {"persistent.example"})

    @test_modes("fake", "smoke")
    def test_automatic_cleanup_keeps_concurrent_sag_domain(self) -> None:
        with TemporaryDirectory() as directory:
            output = StringIO()
            directory_path = Path(directory)
            hosts_path = directory_path / "hosts"
            automatic_path = directory_path / "automatic.txt"
            concurrent_path = directory_path / "concurrent.txt"
            hosts_path.write_text("127.0.0.1 localhost\n", encoding="utf-8")
            automatic_path.write_text("automatic.example\n", encoding="utf-8")
            concurrent_path.write_text("concurrent.example\n", encoding="utf-8")

            def resolve_after_concurrent_block(domain: str) -> set[str]:
                web_blocker.block(concurrent_path)
                return {web_blocker.redirect}

            with (
                patch.object(web_blocker, "default_hoster", str(hosts_path)),
                patch.object(web_blocker, "DEFAULT_BLOCK_LIST_PATHS", (automatic_path,)),
                patch(__name__ + "._resolved_ips", resolve_after_concurrent_block),
                redirect_stdout(output),
            ):
                result = _run_automatic("automatic.example")

            self.assertEqual(result, 0)
            self.assertEqual(_blocked_domains(hosts_path), {"concurrent.example"})

    @test_modes("fake", "smoke")
    def test_concurrent_processes_preserve_each_domains(self) -> None:
        with TemporaryDirectory() as directory:
            directory_path = Path(directory)
            hosts_path = directory_path / "hosts"
            first_domains_path = directory_path / "first-domains.txt"
            second_domains_path = directory_path / "second-domains.txt"
            hosts_path.write_text("127.0.0.1 localhost\n", encoding="utf-8")
            first_domains_path.write_text("first.example\n", encoding="utf-8")
            second_domains_path.write_text("second.example\n", encoding="utf-8")
            context = multiprocessing.get_context("spawn")
            barrier = context.Barrier(2)
            processes = [
                context.Process(
                    target=_concurrent_block_worker,
                    args=(str(hosts_path), str(domains_path), barrier),
                )
                for domains_path in (first_domains_path, second_domains_path)
            ]
            try:
                for process in processes:
                    process.start()
                for process in processes:
                    process.join(timeout=10)
                self.assertTrue(all(not process.is_alive() for process in processes))
                self.assertEqual([process.exitcode for process in processes], [0, 0])
            finally:
                for process in processes:
                    if process.is_alive():
                        process.terminate()
                    process.join()

            self.assertEqual(
                _blocked_domains(hosts_path),
                {"first.example", "second.example"},
            )

    @test_modes("fake")
    def test_automatic_reports_and_cleans_up_after_block_failure(self) -> None:
        with TemporaryDirectory() as directory:
            directory_path = Path(directory)
            hosts_path = directory_path / "hosts"
            automatic_path = directory_path / "automatic.txt"
            hosts_path.write_text("127.0.0.1 localhost\n", encoding="utf-8")
            automatic_path.write_text("automatic.example\n", encoding="utf-8")
            output = StringIO()
            errors = StringIO()
            def block_then_fail(path: str | Path) -> set[str]:
                raise OSError("block failed")

            with (
                patch.object(web_blocker, "default_hoster", str(hosts_path)),
                patch.object(web_blocker, "DEFAULT_BLOCK_LIST_PATHS", (automatic_path,)),
                patch.object(web_blocker, "block", side_effect=block_then_fail),
                redirect_stdout(output),
                redirect_stderr(errors),
            ):
                result = _run_automatic("automatic.example")

            self.assertEqual(result, 1)
            self.assertEqual(_blocked_domains(hosts_path), set())
            self.assertIn("Action failed: block failed", errors.getvalue())
            self.assertIn("Cleanup: complete", output.getvalue())

    @test_modes("real")
    def test_blocker_edits_system_hosts_with_cleanup(self) -> None:
        domain = "pornhub.com"
        hosts_path = Path(web_blocker.default_hoster)
        blocked = False
        try:
            _block_default_lists()
            blocked = True
            self.assertIn(domain, _blocked_domains(hosts_path))
            self.assertIn(web_blocker.redirect, _resolved_ips(domain))
        finally:
            if blocked:
                _unblock_default_lists()

        self.assertNotIn(domain, _blocked_domains(hosts_path))


if __name__ == "__main__":
    raise SystemExit(run_module(sys.modules[__name__]))
