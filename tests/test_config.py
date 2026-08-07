"""Kiểm tra load và fallback config Agent.

File path: `tests/test_config.py`.
Input: ba file TOML temporary: primary, last-good và fallback.
Output: config dùng field hợp lệ ưu tiên từ primary, rồi last-good, rồi fallback.
Nguyên lý: fallback phải khớp hoàn toàn schema; primary và last-good được cứu theo
từng field để giữ tối đa cấu hình hợp lệ.
"""

from pathlib import Path
import sys
import tempfile
import unittest

from test_support import add_source_path, run_module, test_modes


add_source_path()

from config import AgentConfig, ConfigSchemaError, ConfigTypeError


_CONFIG_PATH = (
    Path(__file__).resolve().parents[1] / "src" / "sag_agent_config.toml"
)


class ConfigTests(unittest.TestCase):
    @test_modes("fake")
    def test_loads_primary_and_saves_last_good(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            primary_path = Path(temporary_directory) / "primary.toml"
            last_good_path = Path(temporary_directory) / "last-good.toml"
            fallback_path = Path(temporary_directory) / "fallback.toml"
            _copy_config(primary_path)
            _copy_config(fallback_path)

            config = AgentConfig()
            config.load(primary_path, last_good_path, fallback_path)

            self.assertTrue(config.web_blocker.block_porn)
            self.assertTrue(last_good_path.exists())
            self.assertEqual(last_good_path.read_text(), primary_path.read_text())

    @test_modes("fake")
    def test_uses_last_good_only_for_invalid_primary_field(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            primary_path = Path(temporary_directory) / "primary.toml"
            last_good_path = Path(temporary_directory) / "last-good.toml"
            fallback_path = Path(temporary_directory) / "fallback.toml"
            _copy_config(last_good_path)
            _copy_config(fallback_path)
            primary_text = _CONFIG_PATH.read_text().replace(
                "enabled = false",
                'enabled = "invalid"',
            )
            primary_text = primary_text.replace(
                "scan_interval_seconds = 1.6767",
                "scan_interval_seconds = 2.0",
            )
            primary_path.write_text(primary_text)

            config = AgentConfig()
            config.load(primary_path, last_good_path, fallback_path)

            self.assertFalse(config.process_guard.enabled)
            self.assertEqual(config.process_guard.scan_interval_seconds, 2.0)

    @test_modes("fake")
    def test_uses_fallback_when_primary_and_last_good_field_are_invalid(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            primary_path = Path(temporary_directory) / "primary.toml"
            last_good_path = Path(temporary_directory) / "last-good.toml"
            fallback_path = Path(temporary_directory) / "fallback.toml"
            _copy_config(fallback_path)
            invalid_text = _CONFIG_PATH.read_text().replace(
                "block_game = true",
                'block_game = "invalid"',
            )
            primary_path.write_text(invalid_text)
            last_good_path.write_text(invalid_text)

            config = AgentConfig()
            config.load(primary_path, last_good_path, fallback_path)

            self.assertTrue(config.web_blocker.block_game)

    @test_modes("fake")
    def test_rejects_fallback_with_unmatched_field(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            primary_path = Path(temporary_directory) / "primary.toml"
            last_good_path = Path(temporary_directory) / "last-good.toml"
            fallback_path = Path(temporary_directory) / "fallback.toml"
            _copy_config(primary_path)
            fallback_path.write_text(
                _CONFIG_PATH.read_text() + "\nunknown = true\n"
            )

            config = AgentConfig()

            with self.assertRaises(ConfigSchemaError):
                config.load(primary_path, last_good_path, fallback_path)

    @test_modes("fake")
    def test_rejects_wrong_config_field_type(self) -> None:
        with self.assertRaises(ConfigTypeError):
            from config import ProcessGuardConfig

            ProcessGuardConfig("false", 1.0, [])  # type: ignore[arg-type]


def _copy_config(destination_path: Path) -> None:
    destination_path.write_text(_CONFIG_PATH.read_text())


if __name__ == "__main__":
    raise SystemExit(run_module(sys.modules[__name__]))
