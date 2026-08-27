"""Kiểm tra registry, manager và command boundary của SAG Agent Runtime.

File path: `tests/test_agent_runtime.py`.
Input: registry và component fake, không gọi desktop thật.
Output: lifecycle được quản lý đúng và command chỉ đi qua allowlist.
Nguyên lý: inject registry nhỏ để kiểm tra Runtime độc lập với feature thật.
"""

import sys
import unittest
from dataclasses import dataclass
from typing import cast
from uuid import uuid4

from test_support import add_source_path, run_module, test_modes


add_source_path()

from agent.platform import PlatformServices
from agent.runtime import AgentRuntime
from agent.runtime.feature_manager import FeatureManager
from agent.runtime.feature_registry import FeatureDefinition, FeatureRegistry
from agent.runtime.request_types import Request, RequestFailed, RequestSuccessful
from config import AgentConfig


class _Service:
    def __init__(self) -> None:
        self.starts = 0
        self.stops = 0

    def start(self) -> None:
        self.starts += 1

    def stop(self) -> None:
        self.stops += 1


class _Resource:
    def __init__(self) -> None:
        self.closes = 0

    def close(self) -> None:
        self.closes += 1


@dataclass
class _Locker:
    locks: int = 0
    closes: int = 0

    def lock(self) -> None:
        self.locks += 1

    def close(self) -> None:
        self.closes += 1


class FeatureManagerTests(unittest.TestCase):
    @test_modes("fake")
    def test_starts_services_and_closes_in_reverse_order_once(self) -> None:
        service = _Service()
        resource = _Resource()
        registry = FeatureRegistry(
            (
                FeatureDefinition("worker", "service", lambda _s, _c: service),
                FeatureDefinition("model", "resource", lambda _s, _c: resource),
            )
        )
        manager = FeatureManager(
            registry,
            cast(PlatformServices, object()),
            AgentConfig(),
        )

        manager.start_enabled()
        manager.shutdown()
        manager.shutdown()

        self.assertEqual(service.starts, 1)
        self.assertEqual(service.stops, 1)
        self.assertEqual(resource.closes, 1)

    @test_modes("fake")
    def test_rejects_factory_result_with_wrong_contract(self) -> None:
        registry = FeatureRegistry(
            (FeatureDefinition("broken", "service", lambda _s, _c: object()),)
        )
        manager = FeatureManager(
            registry,
            cast(PlatformServices, object()),
            AgentConfig(),
        )

        with self.assertRaisesRegex(TypeError, "broken.*Service"):
            manager.start_enabled()


class AgentRuntimeTests(unittest.TestCase):
    @test_modes("fake")
    def test_status_and_lock_screen_use_allowlisted_commands(self) -> None:
        locker = _Locker()
        registry = FeatureRegistry(
            (FeatureDefinition("screen_locker", "resource", lambda _s, _c: locker),)
        )
        runtime = AgentRuntime(
            services=cast(PlatformServices, object()),
            config=AgentConfig(),
            registry=registry,
        )
        runtime.start()

        status = runtime.execute(Request(uuid4(), "get_agent_status"))
        locked = runtime.execute(Request(uuid4(), "lock_screen"))
        unknown = runtime.execute(Request(uuid4(), "unknown"))
        runtime.shutdown()

        self.assertIsInstance(status.status, RequestSuccessful)
        self.assertEqual(
            status.data,
            {"state": "running", "active_features": ("screen_locker",)},
        )
        self.assertIsInstance(locked.status, RequestSuccessful)
        self.assertEqual(locker.locks, 1)
        self.assertIsInstance(unknown.status, RequestFailed)
        self.assertEqual(locker.closes, 1)


if __name__ == "__main__":
    raise SystemExit(run_module(sys.modules[__name__]))
