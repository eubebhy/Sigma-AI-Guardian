# pyright: reportPrivateUsage=false
"""Regression tests cho ProcessKiller khong can process that."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from device_controler.process_killer import ProcessKiller


class _FakeProcessOperations:
    def __init__(self) -> None:
        self.killed_processes: list[int] = []

    def list_processes(self) -> list[tuple[int, str]]:
        return [(101, "game.exe"), (102, "game.exe")]

    def kill_process(self, pid: int) -> None:
        if pid == 101:
            raise ProcessLookupError(pid)
        self.killed_processes.append(pid)


class ProcessKillerTests(unittest.TestCase):
    def test_scan_continues_when_a_process_exits_before_kill(self) -> None:
        operations = _FakeProcessOperations()
        killer = ProcessKiller(process_operations=operations)
        killer.set_blacklist(["game.exe"])

        killer._scan_and_kill()

        self.assertEqual(operations.killed_processes, [102])


if __name__ == "__main__":
    unittest.main()
