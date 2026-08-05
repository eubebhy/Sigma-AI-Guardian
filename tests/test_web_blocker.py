"""Kiểm thử WebBlocker với hosts và state tạm, không ghi hosts thật.

File path: `tests/test_web_blocker.py`.
Input: category source list, custom domain và temporary paths.
Output: marker hosts cùng policy persisted đúng theo action manager.
Nguyên lý: test inject hosts/state/category source tạm để không dùng desktop hay hosts OS.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from test_support import add_source_path, run_module, test_modes


add_source_path()

from device_controller import web_blocker
from device_controller.web_blocker import WebBlocker


class WebBlockerTests(unittest.TestCase):
    """WebBlocker chỉ thao tác hosts tạm trong safe test."""

    def setUp(self) -> None:
        self._directory = TemporaryDirectory()
        self._path = Path(self._directory.name)
        self._hosts_path = self._path / "hosts"
        self._state_path = self._path / "policy.json"
        self._hosts_path.write_text("127.0.0.1 localhost\n", encoding="utf-8")
        self._state_path.write_text(
            "{\"blocked_categories\": [], \"custom_blocked_domains\": [], "
            "\"custom_allowed_domains\": []}",
            encoding="utf-8",
        )
        self._porn_path = self._path / "porn.txt"
        self._game_path = self._path / "game.txt"
        self._porn_path.write_text(
            "one.example\nshared.example\n",
            encoding="utf-8",
        )
        self._game_path.write_text(
            "game.example\nshared.example\n",
            encoding="utf-8",
        )
        self._categories = {"porn": self._porn_path, "game": self._game_path}

    def tearDown(self) -> None:
        self._directory.cleanup()

    def _create_manager(self) -> WebBlocker:
        return WebBlocker(
            hosts_path=self._hosts_path,
            state_path=self._state_path,
            category_paths=self._categories,
        )

    @test_modes("fake", "smoke")
    def test_category_uses_its_own_marker_and_persists_policy(self) -> None:
        manager = self._create_manager()

        result = manager.block_category("porn")

        self.assertTrue(result.changed)
        self.assertEqual(result.blocked_domains, 2)
        self.assertEqual(manager.get_status().blocked_categories, frozenset({"porn"}))
        hosts = self._hosts_path.read_text(encoding="utf-8")
        self.assertIn("# SAG webblock category:porn start", hosts)
        self.assertIn("127.0.0.1 one.example", hosts)
        self.assertNotIn("category:game", hosts)

        repeated = manager.block_category("porn")

        self.assertFalse(repeated.changed)

    @test_modes("fake")
    def test_allow_removes_domain_from_all_sag_markers_and_survives_restart(self) -> None:
        manager = self._create_manager()
        manager.block_category("porn")
        manager.block_category("game")

        result = manager.allow_domain("shared.example")

        self.assertTrue(result.changed)
        self.assertEqual(result.unblocked_domains, 2)
        self.assertNotIn("127.0.0.1 shared.example", self._hosts_path.read_text())
        self.assertEqual(
            self._create_manager().get_status().allowed_domains,
            frozenset({"shared.example"}),
        )

    @test_modes("fake")
    def test_custom_block_does_not_add_domain_in_allowlist(self) -> None:
        manager = self._create_manager()
        manager.allow_domain("allowed.example")

        result = manager.block_domain("allowed.example")

        self.assertFalse(result.changed)

        result = manager.block_domain("blocked.example")

        self.assertTrue(result.changed)
        self.assertEqual(result.blocked_domains, 1)
        hosts = self._hosts_path.read_text(encoding="utf-8")
        self.assertIn("127.0.0.1 blocked.example", hosts)
        self.assertNotIn("127.0.0.1 allowed.example", hosts)

    @test_modes("fake")
    def test_reset_reports_policy_change_without_blocked_domain(self) -> None:
        manager = self._create_manager()
        manager.allow_domain("allowed.example")

        result = manager.clear_all()

        self.assertTrue(result.changed)
        self.assertEqual(manager.get_status().allowed_domains, frozenset())

    @test_modes("fake")
    def test_reconcile_restores_category_marker_missing_after_restart(self) -> None:
        manager = self._create_manager()
        manager.block_category("porn")
        self._hosts_path.write_text("127.0.0.1 localhost\n", encoding="utf-8")

        result = self._create_manager().block_category("porn")

        self.assertTrue(result.changed)
        self.assertIn("127.0.0.1 one.example", self._hosts_path.read_text())

    @test_modes("fake")
    def test_invalid_domain_cannot_inject_another_hosts_record(self) -> None:
        manager = self._create_manager()

        result = manager.block_domain("safe.example\n0.0.0.0 victim.example")

        self.assertFalse(result.changed)
        self.assertNotIn("victim.example", self._hosts_path.read_text())

    @test_modes("fake")
    def test_broken_marker_does_not_persist_category_policy(self) -> None:
        self._hosts_path.write_text(
            "# SAG webblock category:porn start\n127.0.0.1 old.example\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "marker"):
            self._create_manager().block_category("porn")

        self.assertEqual(self._create_manager().get_status().blocked_categories, frozenset())

    @test_modes("fake")
    def test_state_write_failure_does_not_modify_hosts(self) -> None:
        manager = self._create_manager()

        with (
            patch.object(manager, "_save_policy", side_effect=OSError("state failed")),
            self.assertRaisesRegex(OSError, "state failed"),
        ):
            manager.block_category("porn")

        self.assertNotIn("category:porn", self._hosts_path.read_text())

    @test_modes("fake")
    def test_hosts_failure_restores_previous_policy(self) -> None:
        manager = self._create_manager()

        with (
            patch.object(web_blocker, "block_file", side_effect=OSError("hosts failed")),
            self.assertRaisesRegex(OSError, "hosts failed"),
        ):
            manager.block_category("porn")

        self.assertEqual(self._create_manager().get_status().blocked_categories, frozenset())

    @test_modes("fake")
    def test_invalid_marker_cannot_inject_hosts_record(self) -> None:
        with self.assertRaisesRegex(ValueError, "Invalid web blocker marker"):
            web_blocker.block(
                ["safe.example"],
                "custom:block\n0.0.0.0 victim.example",
                self._hosts_path,
            )

        self.assertNotIn("victim.example", self._hosts_path.read_text())

    @test_modes("fake")
    def test_replace_marker_rejects_injected_domain(self) -> None:
        web_blocker.replace_marker(
            self._hosts_path,
            "custom:block",
            ["safe.example\n0.0.0.0 victim.example"],
        )

        self.assertNotIn("victim.example", self._hosts_path.read_text())

    @test_modes("fake")
    def test_reconcile_removes_marker_not_in_persisted_policy(self) -> None:
        self._hosts_path.write_text(
            "# SAG webblock category:porn start\n"
            "127.0.0.1 old.example\n"
            "# SAG webblock category:porn end\n",
            encoding="utf-8",
        )

        result = self._create_manager().clear_all()

        self.assertTrue(result.changed)
        self.assertNotIn("old.example", self._hosts_path.read_text())

    @test_modes("fake")
    def test_reset_rejects_nested_marker(self) -> None:
        self._hosts_path.write_text(
            "# SAG webblock category:porn start\n"
            "# SAG webblock custom:block start\n"
            "# SAG webblock custom:block end\n"
            "# SAG webblock category:porn end\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "marker"):
            self._create_manager().clear_all()

    @test_modes("fake")
    def test_unblock_category_removes_only_its_marker(self) -> None:
        manager = self._create_manager()
        manager.block_category("porn")
        manager.block_category("game")

        result = manager.unblock_category("porn")

        self.assertTrue(result.changed)
        hosts = self._hosts_path.read_text(encoding="utf-8")
        self.assertNotIn("category:porn", hosts)
        self.assertIn("127.0.0.1 game.example", hosts)

    @test_modes("fake")
    def test_category_source_is_read_without_path_read_text(self) -> None:
        manager = self._create_manager()
        original_read_text = Path.read_text

        def read_text(
            path: Path,
            encoding: str | None = None,
            errors: str | None = None,
            newline: str | None = None,
        ) -> str:
            if path == self._porn_path:
                raise AssertionError("Category source must be streamed")
            return original_read_text(
                path,
                encoding=encoding,
                errors=errors,
                newline=newline,
            )

        with patch.object(Path, "read_text", new=read_text):
            manager.block_category("porn")

        self.assertIn("127.0.0.1 one.example", self._hosts_path.read_text())


if __name__ == "__main__":
    raise SystemExit(run_module(sys.modules[__name__]))
