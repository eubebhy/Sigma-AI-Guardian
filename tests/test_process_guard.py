# pyright: reportPrivateUsage=false
"""Kiểm tra ProcessKiller bằng process operations fake và fixture opt-in.

File path: ``tests/test_process_guard.py``.
Input: safe mode ``fake`` hoặc ``smoke``; real nhận ``fixture`` hoặc
``kill PROCESS_NAME --confirm``.
Output: pass im lặng, fail in lỗi ngắn.
Nguyên lý: safe test không kill process thật. Lệnh real chính xác là
``./.pyvenv/bin/python tests/test_process_guard.py real fixture``. Lệnh này tạo một
child riêng, adapter chỉ liệt kê và kill PID child đó với tên fixture cố định; không
liệt kê hoặc kill process hệ thống khác, rồi luôn cleanup child trong ``finally``.

Lệnh real trực tiếp là
``./.pyvenv/bin/python tests/test_process_guard.py real kill PROCESS_NAME --confirm``.
Lệnh này chỉ kill PID đã có trong snapshot exact-name sau lowercase/strip, từ chối
khi không có PID hoặc snapshot chứa PID của runner; kiểm tra kỹ tên trước khi chạy.

Lệnh safe: ``./.pyvenv/bin/python tests/test_process_guard.py fake smoke``.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import threading
import unittest
from collections.abc import Sequence
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from typing import Callable, NoReturn, Protocol
from unittest.mock import patch

from test_support import add_source_path, run_module, test_modes


add_source_path()

from agent.contracts import ProcessOperations
from agent.platform.linux.processes import LinuxProcessOperations
from agent.platform.windows.processes import WindowsProcessOperations
from device_controler.process_killer import ProcessKiller


_FIXTURE_PROCESS_NAME = "sag-process-guard-fixture"
_FIXTURE_TIMEOUT_SECONDS = 5.0
_PROCESS_KILLER_CLASS = ProcessKiller


class _FakeProcessOperations:
    def __init__(self, processes: list[tuple[int, str]]) -> None:
        self.processes = processes
        self.killed_processes: list[int] = []
        self.list_calls = 0

    def list_processes(self) -> list[tuple[int, str]]:
        self.list_calls += 1
        return self.processes

    def kill_process(self, pid: int) -> None:
        self.killed_processes.append(pid)
        self.processes = [process for process in self.processes if process[0] != pid]


class _ExitingProcessOperations(_FakeProcessOperations):
    def kill_process(self, pid: int) -> None:
        if pid == 101:
            raise ProcessLookupError(pid)
        super().kill_process(pid)


class _FailingProcessOperations(_FakeProcessOperations):
    def kill_process(self, pid: int) -> None:
        raise RuntimeError(f"cannot kill {pid}")


class _PermissionDeniedProcessOperations(_FakeProcessOperations):
    def kill_process(self, pid: int) -> None:
        raise PermissionError(f"cannot kill {pid}")


class _TransientLookupProcessOperations(_FakeProcessOperations):
    def list_processes(self) -> list[tuple[int, str]]:
        self.list_calls += 1
        if self.list_calls == 1:
            raise ProcessLookupError(101)
        return self.processes


class _SpawningProcessOperations(_FakeProcessOperations):
    def kill_process(self, pid: int) -> None:
        super().kill_process(pid)
        self.processes.append((102, "game.exe"))


class _PidReuseProcessOperations(_FakeProcessOperations):
    def __init__(self) -> None:
        super().__init__([(101, "game.exe")])

    def list_processes(self) -> list[tuple[int, str]]:
        self.list_calls += 1
        if self.list_calls == 1:
            return self.processes
        return [(101, "other.exe")]


class _MissingPidProcessOperations(_FakeProcessOperations):
    def __init__(self) -> None:
        super().__init__([(101, "game.exe")])

    def list_processes(self) -> list[tuple[int, str]]:
        self.list_calls += 1
        if self.list_calls == 1:
            return self.processes
        return []


class _FakeStopEvent(threading.Event):
    def __init__(self) -> None:
        super().__init__()
        self.was_set = False

    def is_set(self) -> bool:
        return self.was_set

    def set(self) -> None:
        self.was_set = True

    def wait(self, timeout: float | None = None) -> bool:
        del timeout
        return self.was_set


class _ScanStopEvent(_FakeStopEvent):
    def __init__(self, stop_after_waits: int) -> None:
        super().__init__()
        self._stop_after_waits = stop_after_waits
        self.wait_calls = 0

    def wait(self, timeout: float | None = None) -> bool:
        del timeout
        self.wait_calls += 1
        if self.wait_calls == self._stop_after_waits:
            self.set()
        return self.was_set


class _FakeDaemonThread:
    def __init__(
        self,
        *,
        target: Callable[..., None],
        args: tuple[_FakeStopEvent],
        daemon: bool,
    ) -> None:
        self.target = target
        self.args = args
        self.daemon = daemon
        self.alive = False
        self.join_calls = 0

    def is_alive(self) -> bool:
        return self.alive

    def start(self) -> None:
        self.alive = True

    def join(self) -> None:
        self.join_calls += 1
        self.alive = False


class _FixtureChild(Protocol):
    @property
    def pid(self) -> int:
        """Trả PID child fixture."""

        ...

    def poll(self) -> int | None:
        """Trả exit code hoặc ``None`` khi child còn chạy."""

    def kill(self) -> None:
        """Kết thúc child fixture."""


class _FixtureProcessOperations:
    """Adapter chỉ cấp ProcessKiller quyền trên đúng child fixture đã tạo."""

    def __init__(self, child: _FixtureChild) -> None:
        self._child = child

    def list_processes(self) -> list[tuple[int, str]]:
        if self._child.poll() is None:
            return [(self._child.pid, _FIXTURE_PROCESS_NAME)]
        return []

    def kill_process(self, pid: int) -> None:
        if pid != self._child.pid:
            raise ProcessLookupError(pid)
        self._child.kill()


class _SnapshotProcessOperations:
    """Chỉ cho ProcessKiller scan và kill các PID đã được preflight chọn."""

    def __init__(
        self,
        process_operations: ProcessOperations,
        matches: list[tuple[int, str]],
    ) -> None:
        self._process_operations = process_operations
        self._matches = matches
        self._selected_processes = {
            (pid, name.strip().lower()) for pid, name in matches
        }

    def list_processes(self) -> list[tuple[int, str]]:
        return list(self._matches)

    def kill_process(self, pid: int) -> None:
        selected_names = {
            name for selected_pid, name in self._selected_processes if selected_pid == pid
        }
        current_names = {
            name.strip().lower()
            for current_pid, name in self._process_operations.list_processes()
            if current_pid == pid
        }
        if not selected_names.intersection(current_names):
            raise ProcessLookupError(pid)
        self._process_operations.kill_process(pid)

    def remaining_processes(self) -> list[tuple[int, str]]:
        return [
            (pid, name)
            for pid, name in self._process_operations.list_processes()
            if any(selected_pid == pid for selected_pid, _ in self._selected_processes)
        ]


class _FakeFixtureChild:
    def __init__(self, pid: int) -> None:
        self._pid = pid
        self.was_killed = False
        self.was_terminated = False

    @property
    def pid(self) -> int:
        return self._pid

    def poll(self) -> int | None:
        if self.was_killed:
            return -9
        return None

    def kill(self) -> None:
        self.was_killed = True

    def terminate(self) -> None:
        self.was_terminated = True
        self.was_killed = True

    def wait(self, timeout: float) -> int:
        del timeout
        if self.was_killed:
            return -9
        raise subprocess.TimeoutExpired("fixture", _FIXTURE_TIMEOUT_SECONDS)


class _RealArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ValueError(message)


def _parse_real_arguments(arguments: Sequence[str]) -> argparse.Namespace | None:
    parser = _RealArgumentParser(add_help=False)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("fixture", add_help=False)
    kill_parser = commands.add_parser("kill", add_help=False)
    kill_parser.add_argument("process_name")
    kill_parser.add_argument("--confirm", action="store_true", required=True)
    try:
        return parser.parse_args(arguments)
    except (argparse.ArgumentError, ValueError):
        return None


def _start_fixture() -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _cleanup_fixture(child: subprocess.Popen[bytes]) -> None:
    if child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=_FIXTURE_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=_FIXTURE_TIMEOUT_SECONDS)
        print("Cleanup: child terminated")
        return
    print("Cleanup: child already exited")


def run_real(arguments: Sequence[str]) -> int:
    """Chạy fixture riêng hoặc kill exact process name ngoài safe suite."""

    command = _parse_real_arguments(arguments)
    if command is None:
        print("Usage: real fixture | real kill PROCESS_NAME --confirm", file=sys.stderr)
        return 2
    if command.command == "kill":
        return _run_named_kill(command.process_name)
    child: subprocess.Popen[bytes] | None = None
    result = 1
    print(f"Start: fixture={_FIXTURE_PROCESS_NAME}")
    try:
        child = _start_fixture()
        print(f"Child PID: {child.pid}")
        killer = ProcessKiller(_FixtureProcessOperations(child))
        killer.set_blacklist([_FIXTURE_PROCESS_NAME])
        killer._scan_and_kill()
        exit_code = child.wait(timeout=_FIXTURE_TIMEOUT_SECONDS)
        print(f"Kill result: child exited code={exit_code}")
        result = 0
    except Exception as error:
        print(f"Fixture failed: {error}", file=sys.stderr)
    finally:
        if child is None:
            print("Cleanup: child was not started")
        else:
            try:
                _cleanup_fixture(child)
            except Exception as error:
                print(f"Cleanup failed: {error}", file=sys.stderr)
                result = 1
    return result


def _run_named_kill(supplied_name: str) -> int:
    process_name = supplied_name.strip().lower()
    if not process_name:
        print("Usage: real kill PROCESS_NAME --confirm", file=sys.stderr)
        return 2
    operations: _SnapshotProcessOperations | None = None
    try:
        default_killer = ProcessKiller()
        matches = _matching_processes(
            default_killer._process_operations,
            process_name,
        )
        _print_matches("Match list", matches)
        if not matches:
            print("Kill result: rejected; no exact matching PID")
            _print_matches("Remaining selected PIDs", [])
            return 1
        if os.getpid() in {pid for pid, _ in matches}:
            print("Kill result: rejected; runner PID is selected")
            _print_matches("Remaining selected PIDs", matches)
            return 1
        operations = _SnapshotProcessOperations(
            default_killer._process_operations,
            matches,
        )
        killer = ProcessKiller(operations)
        killer.set_blacklist([process_name])
        killer._scan_and_kill()
        print("Kill result: scan completed")
        remaining = operations.remaining_processes()
        _print_matches("Remaining selected PIDs", remaining)
    except Exception as error:
        print(f"Kill result: failed; {error}")
        if operations is not None:
            _print_matches(
                "Remaining selected PIDs",
                operations.remaining_processes(),
            )
        return 1
    return 0 if matches and not remaining else 1


def _matching_processes(
    process_operations: ProcessOperations,
    process_name: str,
) -> list[tuple[int, str]]:
    return [
        (pid, process_name)
        for pid, name in process_operations.list_processes()
        if name.strip().lower() == process_name
    ]


def _print_matches(label: str, matches: list[tuple[int, str]]) -> None:
    print(f"{label}:")
    for pid, name in matches:
        print(f"PID={pid} name={name}")


def _process_killer_factory(
    default_operations: ProcessOperations,
) -> Callable[[ProcessOperations | None], ProcessKiller]:
    def _create(process_operations: ProcessOperations | None = None) -> ProcessKiller:
        return _PROCESS_KILLER_CLASS(process_operations or default_operations)

    return _create


class ProcessGuardTests(unittest.TestCase):
    @test_modes("fake")
    def test_blacklist_matches_exact_name(self) -> None:
        killer = ProcessKiller(_FakeProcessOperations([]))
        killer.set_blacklist(["Game.exe"])

        self.assertTrue(killer._should_kill("game.exe"))
        self.assertFalse(killer._should_kill("game-helper.exe"))

    @test_modes("fake")
    def test_whitelist_wins_over_blacklist(self) -> None:
        killer = ProcessKiller(_FakeProcessOperations([]))
        killer.blocked = ["game.exe"]
        killer.set_whitelist(["Game.exe"])

        self.assertFalse(killer._should_kill("game.exe"))

    @test_modes("fake", "smoke")
    def test_scan_uses_injected_process_operations(self) -> None:
        operations = _FakeProcessOperations([(101, "game.exe"), (102, "teacher-tool.exe")])
        killer = ProcessKiller(operations)
        killer.set_blacklist(["game.exe"])

        killer._scan_and_kill()

        self.assertEqual(operations.killed_processes, [101])
        self.assertEqual(operations.list_calls, 2)

    @test_modes("fake")
    def test_scan_skips_pid_when_its_name_changes_before_kill(self) -> None:
        operations = _PidReuseProcessOperations()
        killer = ProcessKiller(operations)
        killer.set_blacklist(["game.exe"])

        killer._scan_and_kill()

        self.assertEqual(operations.killed_processes, [])

    @test_modes("fake")
    def test_scan_skips_pid_when_it_disappears_before_kill(self) -> None:
        operations = _MissingPidProcessOperations()
        killer = ProcessKiller(operations)
        killer.set_blacklist(["game.exe"])

        killer._scan_and_kill()

        self.assertEqual(operations.killed_processes, [])

    @test_modes("fake")
    def test_scan_continues_when_a_process_exits_before_kill(self) -> None:
        operations = _ExitingProcessOperations([(101, "game.exe"), (102, "game.exe")])
        killer = ProcessKiller(operations)
        killer.set_blacklist(["game.exe"])

        killer._scan_and_kill()

        self.assertEqual(operations.killed_processes, [102])

    @test_modes("fake")
    def test_daemon_continues_after_process_lookup_error(self) -> None:
        operations = _TransientLookupProcessOperations([(101, "game.exe")])
        killer = ProcessKiller(operations)
        killer.set_blacklist(["game.exe"])
        stop_event = _ScanStopEvent(stop_after_waits=2)

        killer._run(stop_event)

        self.assertEqual(operations.killed_processes, [101])
        self.assertEqual(stop_event.wait_calls, 2)
        killer.raise_if_failed()

    @test_modes("fake")
    def test_daemon_records_kill_failure_for_agent_caller(self) -> None:
        killer = ProcessKiller(_FailingProcessOperations([(101, "game.exe")]))
        killer.set_blacklist(["game.exe"])

        killer._run(_FakeStopEvent())

        with self.assertRaisesRegex(RuntimeError, "cannot kill 101"):
            killer.raise_if_failed()

    @test_modes("fake")
    def test_daemon_records_permission_error(self) -> None:
        killer = ProcessKiller(
            _PermissionDeniedProcessOperations([(101, "game.exe")])
        )
        killer.set_blacklist(["game.exe"])
        stop_event = _ScanStopEvent(stop_after_waits=1)

        killer._run(stop_event)

        with self.assertRaisesRegex(PermissionError, "cannot kill 101"):
            killer.raise_if_failed()

    @test_modes("fake")
    def test_linux_list_processes_propagates_command_failure(self) -> None:
        error = subprocess.CalledProcessError(1, ["ps"])

        with patch(
            "agent.platform.linux.processes.subprocess.check_output",
            side_effect=error,
        ):
            with self.assertRaises(subprocess.CalledProcessError):
                LinuxProcessOperations().list_processes()

    @test_modes("fake")
    def test_windows_list_processes_propagates_command_failure(self) -> None:
        with patch(
            "agent.platform.windows.processes.subprocess.check_output",
            side_effect=OSError("tasklist unavailable"),
        ):
            with self.assertRaisesRegex(OSError, "tasklist unavailable"):
                WindowsProcessOperations().list_processes()

    @test_modes("fake")
    def test_windows_kill_process_propagates_nonzero_exit(self) -> None:
        error = subprocess.CalledProcessError(1, ["taskkill"])

        with patch(
            "agent.platform.windows.processes.subprocess.run",
            side_effect=error,
        ) as run:
            with self.assertRaises(subprocess.CalledProcessError):
                WindowsProcessOperations().kill_process(101)

        run.assert_called_once_with(["taskkill", "/PID", "101", "/F"], check=True)

    @test_modes("fake")
    def test_stop_then_start_signals_and_replaces_alive_daemon(self) -> None:
        events = [_FakeStopEvent(), _FakeStopEvent()]
        threads: list[_FakeDaemonThread] = []

        def create_thread(
            *,
            target: Callable[..., None],
            args: tuple[_FakeStopEvent],
            daemon: bool,
        ) -> _FakeDaemonThread:
            thread = _FakeDaemonThread(target=target, args=args, daemon=daemon)
            threads.append(thread)
            return thread

        with (
            patch("device_controler.process_killer.threading.Event", side_effect=events),
            patch("device_controler.process_killer.threading.Thread", side_effect=create_thread),
        ):
            killer = ProcessKiller(_FakeProcessOperations([]))
            killer.start()
            killer.stop()
            killer.start()

        self.assertTrue(events[0].was_set)
        self.assertEqual(threads[0].join_calls, 1)
        self.assertFalse(threads[0].is_alive())
        self.assertEqual(len(threads), 2)
        self.assertTrue(threads[1].is_alive())
        self.assertIs(killer._thread, threads[1])

    @test_modes("fake")
    def test_stop_joins_daemon_before_returning(self) -> None:
        event = _FakeStopEvent()
        threads: list[_FakeDaemonThread] = []

        def create_thread(
            *,
            target: Callable[..., None],
            args: tuple[_FakeStopEvent],
            daemon: bool,
        ) -> _FakeDaemonThread:
            thread = _FakeDaemonThread(target=target, args=args, daemon=daemon)
            threads.append(thread)
            return thread

        with (
            patch("device_controler.process_killer.threading.Event", return_value=event),
            patch("device_controler.process_killer.threading.Thread", side_effect=create_thread),
        ):
            killer = ProcessKiller(_FakeProcessOperations([]))
            killer.start()
            killer.stop()

        self.assertTrue(event.was_set)
        self.assertEqual(threads[0].join_calls, 1)
        self.assertFalse(threads[0].is_alive())
        self.assertIsNone(killer._thread)
        self.assertIsNone(killer._stop_event)

class RealProcessGuardCommandTests(unittest.TestCase):
    def test_parse_real_fixture_command(self) -> None:
        command = _parse_real_arguments(("fixture",))

        self.assertIsNotNone(command)
        assert command is not None
        self.assertEqual(command.command, "fixture")

    def test_parse_real_rejects_extra_arguments(self) -> None:
        self.assertIsNone(_parse_real_arguments(("fixture", "extra")))

    def test_parse_real_kill_command(self) -> None:
        command = _parse_real_arguments(("kill", " Game.EXE ", "--confirm"))

        self.assertIsNotNone(command)
        assert command is not None
        self.assertEqual(command.command, "kill")
        self.assertEqual(command.process_name, " Game.EXE ")
        self.assertTrue(command.confirm)

    def test_run_real_kill_requires_confirmation(self) -> None:
        operations = _FakeProcessOperations([(101, "game.exe")])
        output = StringIO()

        with (
            patch(__name__ + ".ProcessKiller", return_value=ProcessKiller(operations)),
            redirect_stderr(output),
        ):
            result = run_real(("kill", "game.exe"))

        self.assertEqual(result, 2)
        self.assertEqual(operations.killed_processes, [])
        self.assertIn("--confirm", output.getvalue())

    def test_run_real_kill_normalizes_and_kills_only_selected_pids(self) -> None:
        operations = _FakeProcessOperations(
            [(101, "game.exe"), (102, "game-helper.exe"), (103, "Game.exe")]
        )
        output = StringIO()

        with (
            patch(
                __name__ + ".ProcessKiller",
                side_effect=_process_killer_factory(operations),
            ),
            redirect_stdout(output),
        ):
            result = run_real(("kill", " Game.EXE ", "--confirm"))

        self.assertEqual(result, 0)
        self.assertEqual(operations.killed_processes, [101, 103])
        self.assertEqual(
            output.getvalue(),
            "Match list:\nPID=101 name=game.exe\nPID=103 name=game.exe\n"
            "Kill result: scan completed\nRemaining selected PIDs:\n",
        )

    def test_run_real_kill_returns_one_when_no_exact_match_exists(self) -> None:
        operations = _FakeProcessOperations([(101, "game-helper.exe")])

        with (
            patch(__name__ + ".ProcessKiller", return_value=ProcessKiller(operations)),
            redirect_stdout(StringIO()),
        ):
            result = run_real(("kill", "game.exe", "--confirm"))

        self.assertEqual(result, 1)
        self.assertEqual(operations.killed_processes, [])

    def test_run_real_kill_rejects_current_runner_pid(self) -> None:
        operations = _FakeProcessOperations([(101, "game.exe")])

        with (
            patch(__name__ + ".ProcessKiller", return_value=ProcessKiller(operations)),
            patch(__name__ + ".os.getpid", return_value=101),
            redirect_stdout(StringIO()),
        ):
            result = run_real(("kill", "game.exe", "--confirm"))

        self.assertEqual(result, 1)
        self.assertEqual(operations.killed_processes, [])

    def test_run_real_kill_ignores_same_name_process_added_after_preflight(self) -> None:
        operations = _SpawningProcessOperations([(101, "game.exe")])

        with (
            patch(
                __name__ + ".ProcessKiller",
                side_effect=_process_killer_factory(operations),
            ),
            redirect_stdout(StringIO()),
        ):
            result = run_real(("kill", "game.exe", "--confirm"))

        self.assertEqual(result, 0)
        self.assertEqual(operations.killed_processes, [101])
        self.assertEqual(operations.processes, [(102, "game.exe")])

    def test_run_real_kill_rejects_pid_reused_with_another_name(self) -> None:
        operations = _PidReuseProcessOperations()

        with (
            patch(
                __name__ + ".ProcessKiller",
                side_effect=_process_killer_factory(operations),
            ),
            redirect_stdout(StringIO()),
        ):
            result = run_real(("kill", "game.exe", "--confirm"))

        self.assertEqual(result, 1)
        self.assertEqual(operations.killed_processes, [])

    def test_run_real_kill_returns_one_when_kill_errors(self) -> None:
        operations = _FailingProcessOperations([(101, "game.exe")])

        with (
            patch(
                __name__ + ".ProcessKiller",
                side_effect=_process_killer_factory(operations),
            ),
            redirect_stderr(StringIO()),
            redirect_stdout(StringIO()),
        ):
            result = run_real(("kill", "game.exe", "--confirm"))

        self.assertEqual(result, 1)

    def test_run_real_kill_rejects_blank_name(self) -> None:
        with redirect_stderr(StringIO()):
            result = run_real(("kill", "  ", "--confirm"))

        self.assertEqual(result, 2)

    def test_fixture_adapter_exposes_and_kills_only_its_child(self) -> None:
        child = _FakeFixtureChild(pid=707)
        operations = _FixtureProcessOperations(child)

        self.assertEqual(operations.list_processes(), [(707, _FIXTURE_PROCESS_NAME)])
        with self.assertRaises(ProcessLookupError):
            operations.kill_process(708)

        operations.kill_process(707)

        self.assertTrue(child.was_killed)
        self.assertEqual(operations.list_processes(), [])

    def test_run_real_fixture_prints_result_and_cleanup(self) -> None:
        child = _FakeFixtureChild(pid=707)
        output = StringIO()

        with (
            patch(__name__ + "._start_fixture", return_value=child),
            redirect_stdout(output),
        ):
            result = run_real(("fixture",))

        self.assertEqual(result, 0)
        self.assertEqual(
            output.getvalue(),
            "Start: fixture=sag-process-guard-fixture\nChild PID: 707\n"
            "Kill result: child exited code=-9\nCleanup: child already exited\n",
        )

    def test_run_real_fixture_cleans_up_after_scan_failure(self) -> None:
        child = _FakeFixtureChild(pid=707)
        failing_killer = ProcessKiller(
            _FailingProcessOperations([(707, _FIXTURE_PROCESS_NAME)])
        )

        with (
            patch(__name__ + "._start_fixture", return_value=child),
            patch(__name__ + ".ProcessKiller", return_value=failing_killer),
            redirect_stderr(StringIO()),
            redirect_stdout(StringIO()),
        ):
            result = run_real(("fixture",))

        self.assertEqual(result, 1)
        self.assertTrue(child.was_terminated)

    def test_run_real_invalid_command_returns_two(self) -> None:
        with redirect_stderr(StringIO()):
            result = run_real(("unknown",))

        self.assertEqual(result, 2)

    def test_run_real_fixture_error_returns_one(self) -> None:
        with (
            patch(__name__ + "._start_fixture", side_effect=OSError("unavailable")),
            redirect_stderr(StringIO()),
            redirect_stdout(StringIO()),
        ):
            result = run_real(("fixture",))

        self.assertEqual(result, 1)


if __name__ == "__main__":
    raise SystemExit(run_module(sys.modules[__name__]))
