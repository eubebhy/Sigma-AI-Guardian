"""Kiểm tra schema hiện tại và cơ chế fallback config Agent.

File path: `tests/test_config.py`.
Input: primary, last-good và fallback TOML trong temporary directory.
Output: mỗi field hợp lệ được chọn theo thứ tự primary, last-good rồi fallback.
Nguyên lý: dùng config thật làm schema chuẩn và chỉ thay giá trị cần kiểm tra.
"""

from pathlib import Path
import sys
import tempfile
import unittest

from test_support import add_source_path, run_module, test_modes


add_source_path()

from config import AgentConfig, ConfigSchemaError


_CONFIG_PATH = (
    Path(__file__).resolve().parents[1] / "src" / "sag_agent_config.toml"
)


class ConfigTests(unittest.TestCase):
    @test_modes("fake")
    def test_loads_current_schema_from_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fallback_path = root / "fallback.toml"
            _copy_config(fallback_path)

            config = AgentConfig()
            config.load(
                root / "missing.toml",
                root / "missing-good.toml",
                fallback_path,
            )

            self.assertTrue(config.system_monitoring.block_games)
            self.assertEqual(config.process_guard.scan_interval_seconds, 1.6767)
            self.assertEqual(config.keylogger.max_bufferi_chars, 6767)
            self.assertEqual(config.mouse_tracker.interval, 0.067)

    @test_modes("fake")
    def test_uses_each_source_per_field(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            primary_path = root / "primary.toml"
            last_good_path = root / "last-good.toml"
            fallback_path = root / "fallback.toml"
            _copy_config(fallback_path)
            _write_changed(last_good_path, "timeout = 402", "timeout = 500")
            primary_text = _changed_config(
                "scan_interval_seconds = 1.6767",
                "scan_interval_seconds = 3.0",
            ).replace("timeout = 402", 'timeout = "invalid"')
            primary_path.write_text(primary_text)

            config = AgentConfig()
            config.load(primary_path, last_good_path, fallback_path)

            self.assertEqual(config.process_guard.scan_interval_seconds, 3.0)
            self.assertEqual(config.screen_lock.timeout, 500)
            self.assertEqual(config.mouse_tracker.max_positions, 1000)

    @test_modes("fake")
    def test_uses_fallback_when_other_sources_have_invalid_field(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            primary_path = root / "primary.toml"
            last_good_path = root / "last-good.toml"
            fallback_path = root / "fallback.toml"
            _copy_config(fallback_path)
            _write_changed(primary_path, "timeout = 402", 'timeout = "invalid"')
            _write_changed(last_good_path, "timeout = 402", 'timeout = "invalid"')

            config = AgentConfig()
            config.load(primary_path, last_good_path, fallback_path)

            self.assertEqual(config.screen_lock.timeout, 402)

    @test_modes("fake")
    def test_saves_only_complete_valid_primary_as_last_good(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            primary_path = root / "primary.toml"
            last_good_path = root / "last-good.toml"
            fallback_path = root / "fallback.toml"
            _copy_config(primary_path)
            _copy_config(fallback_path)

            config = AgentConfig()
            config.load(primary_path, last_good_path, fallback_path)

            self.assertEqual(last_good_path.read_text(), primary_path.read_text())

    @test_modes("fake")
    def test_does_not_replace_last_good_with_invalid_primary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            primary_path = root / "primary.toml"
            last_good_path = root / "last-good.toml"
            fallback_path = root / "fallback.toml"
            _write_changed(primary_path, "timeout = 402", 'timeout = "invalid"')
            _write_changed(last_good_path, "timeout = 402", "timeout = 500")
            _copy_config(fallback_path)

            config = AgentConfig()
            config.load(primary_path, last_good_path, fallback_path)

            self.assertIn("timeout = 500", last_good_path.read_text())

    @test_modes("fake")
    def test_rejects_invalid_fallback_schema(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fallback_path = root / "fallback.toml"
            fallback_path.write_text(_CONFIG_PATH.read_text() + "\nunknown = true\n")

            with self.assertRaises(ConfigSchemaError):
                AgentConfig().load(
                    root / "missing.toml",
                    root / "missing-good.toml",
                    fallback_path,
                )


def _copy_config(destination: Path) -> None:
    destination.write_text(_CONFIG_PATH.read_text())


def _changed_config(old: str, new: str) -> str:
    return _CONFIG_PATH.read_text().replace(old, new)


def _write_changed(destination: Path, old: str, new: str) -> None:
    destination.write_text(_changed_config(old, new))


if __name__ == "__main__":
    raise SystemExit(run_module(sys.modules[__name__]))
