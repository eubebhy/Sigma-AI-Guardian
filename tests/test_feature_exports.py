"""Kiểm tra convention public export của feature SAG Agent.

File path: `tests/test_feature_exports.py`.
Input: public package của device controller và system monitor.
Output: service/resource export class; stateless API export raw function.
Nguyên lý: kiểm tra `__all__` để convention hiển thị ngay tại import boundary.
"""

import inspect
import sys
import unittest

from test_support import add_source_path, run_module, test_modes


add_source_path()

from content_classifier import Classifier, content_classifier
from device_controller.browser_tab import open_tab
from device_controller.input_controller import Input
from device_controller.process_guard import ProcessGuard
from device_controller.screen_capture import ScreenCapture
from device_controller.screen_locker import ScreenLocker
from device_controller.web_blocker import WebBlocker, block
from system_monitor.keylogger import KeyLogger
from system_monitor.mouse_tracker import MouseTracker
from system_monitor.window_tracker import get_active_window_name


class FeatureExportTests(unittest.TestCase):
    @test_modes("fake")
    def test_services_and_resources_export_classes(self) -> None:
        exports = (
            Classifier,
            Input,
            ProcessGuard,
            ScreenCapture,
            ScreenLocker,
            WebBlocker,
            KeyLogger,
            MouseTracker,
        )

        self.assertTrue(all(inspect.isclass(value) for value in exports))

    @test_modes("fake")
    def test_stateless_apis_export_functions(self) -> None:
        exports = (content_classifier, open_tab, block, get_active_window_name)

        self.assertTrue(all(inspect.isfunction(value) for value in exports))


if __name__ == "__main__":
    raise SystemExit(run_module(sys.modules[__name__]))
