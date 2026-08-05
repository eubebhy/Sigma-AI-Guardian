# pyright: reportPrivateUsage=false
"""Shell demo giao tiếp với backend qua fake network an toàn.

File path: `tests/test_agent_loop.py`.
Input: shell nhận text như `status`, `classify TEXT` và `keylogger on`; shell tự đổi
text thành command có cấu trúc trước khi gửi qua fake network.
Output: backend trả response text; `trace on` in các bước backend đang xử lý.
Nguyên lý: transport chỉ chuyển command/response. Backend validate, route và gọi
feature; feature tự giữ worker thread. Shutdown dừng backend rồi dừng feature.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from queue import Empty, Queue
import shlex
import sys
import threading
import time
import unittest

from test_support import add_source_path, run_module, test_modes


add_source_path()

from content_classifier.rule_based import rule_based_classifier
import system_monitor.keylogger as keylogger_module
from system_monitor.keylogger import KeyLogger
from utils.key_listener import KeyEvent


_HELP = """Commands:
  help                 Show this list.
  status               Show backend and feature state.
  classify TEXT        Run the synchronous rule classifier.
  keylogger on|off     Start or stop the fake threaded KeyLogger.
  inject TEXT          Queue fake keystrokes.
  keys                 Show the KeyLogger virtual buffer.
  trace                Show backend trace history.
  trace on|off         Enable or disable live backend trace output.
  quit                 Stop the backend cleanly."""


@dataclass(frozen=True)
class NetworkCommand:
    """Command có cấu trúc được shell gửi qua fake network."""

    request_id: int
    action: str
    args: dict[str, str]


@dataclass(frozen=True)
class NetworkResponse:
    """Response backend gửi lại qua fake network."""

    request_id: int
    ok: bool
    message: str


@dataclass(frozen=True)
class TraceEvent:
    """Một bước xử lý backend để shell quan sát."""

    request_id: int
    action: str
    phase: str

    def format(self) -> str:
        return f"backend [{self.request_id}] {self.phase}: {self.action}"


class FakeNetwork:
    """Cặp queue mô phỏng transport hai chiều giữa shell và backend."""

    def __init__(self) -> None:
        self._commands: Queue[NetworkCommand | None] = Queue()
        self._responses: Queue[NetworkResponse] = Queue()

    def send_command(self, command: NetworkCommand) -> None:
        self._commands.put(command)

    def receive_command(self, timeout: float) -> NetworkCommand | None:
        try:
            return self._commands.get(timeout=timeout)
        except Empty:
            return None

    def send_response(self, response: NetworkResponse) -> None:
        self._responses.put(response)

    def receive_response(self, timeout: float) -> NetworkResponse | None:
        try:
            return self._responses.get(timeout=timeout)
        except Empty:
            return None

    def stop(self) -> None:
        self._commands.put(None)


class AgentBackend:
    """Backend nhận command từ transport, route tới feature và ghi trace."""

    def __init__(self) -> None:
        self.network = FakeNetwork()
        self._keylogger = _KeyLoggerFeature()
        self._trace_events: Queue[TraceEvent] = Queue()
        self._trace_history: deque[TraceEvent] = deque(maxlen=50)
        self._trace_lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stopping = threading.Event()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.is_running:
            return
        self._stopping.clear()
        self._thread = threading.Thread(target=self._serve, name="agent-backend")
        self._thread.start()

    def shutdown(self) -> None:
        self._stopping.set()
        self.network.stop()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        self._keylogger.stop()

    def wait_response(
        self,
        request_id: int,
        timeout: float,
        on_trace: Callable[[TraceEvent], None] | None = None,
    ) -> NetworkResponse:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self._send_trace_to(on_trace)
            response = self.network.receive_response(timeout=0.02)
            if response is not None and response.request_id == request_id:
                self._send_trace_to(on_trace)
                return response
        raise TimeoutError(f"backend did not respond to request {request_id}")

    def get_trace_history(self) -> list[TraceEvent]:
        with self._trace_lock:
            return list(self._trace_history)

    def clear_live_trace(self) -> None:
        while True:
            try:
                self._trace_events.get_nowait()
            except Empty:
                return

    def _serve(self) -> None:
        while not self._stopping.is_set():
            command = self.network.receive_command(timeout=0.1)
            if command is None:
                continue
            response = self._handle(command)
            self.network.send_response(response)
            if command.action == "agent.shutdown":
                self._stopping.set()

    def _handle(self, command: NetworkCommand) -> NetworkResponse:
        self._trace(command, "received")
        if not self._is_valid(command):
            self._trace(command, "rejected")
            return NetworkResponse(command.request_id, False, "error: invalid command")
        self._trace(command, "validated")
        try:
            message = self._dispatch(command)
        except Exception as error:
            self._trace(command, "failed")
            return NetworkResponse(command.request_id, False, f"error: {error}")
        self._trace(command, "completed")
        return NetworkResponse(command.request_id, True, message)

    def _is_valid(self, command: NetworkCommand) -> bool:
        return command.action in {
            "agent.help",
            "agent.status",
            "agent.shutdown",
            "classifier.rule_based",
            "keylogger.start",
            "keylogger.stop",
            "keylogger.inject",
            "keylogger.buffer",
        }

    def _dispatch(self, command: NetworkCommand) -> str:
        self._trace(command, "dispatched")
        if command.action == "agent.help":
            return _HELP
        if command.action == "agent.status":
            return f"agent: running; keylogger: {self._keylogger.running}"
        if command.action == "agent.shutdown":
            return "agent: stopping"
        if command.action == "classifier.rule_based":
            return self._classify(command)
        if command.action == "keylogger.start":
            return "keylogger: started" if self._keylogger.start() else "keylogger: running"
        if command.action == "keylogger.stop":
            self._keylogger.stop()
            return "keylogger: stopped"
        if command.action == "keylogger.inject":
            return self._inject(command)
        return f"keys: {self._keylogger.get_buffer()}"

    def _classify(self, command: NetworkCommand) -> str:
        text = command.args.get("text", "")
        if not text:
            return "error: classify requires TEXT"
        category = rule_based_classifier(text, moderation_level="strict")
        return f"category: {category.name}"

    def _inject(self, command: NetworkCommand) -> str:
        text = command.args.get("text", "")
        if not text:
            return "error: inject requires TEXT"
        if not self._keylogger.queue_text(text):
            return "error: keylogger is off or text is unsupported"
        return f"keylogger: queued {text}"

    def _trace(self, command: NetworkCommand, phase: str) -> None:
        event = TraceEvent(command.request_id, command.action, phase)
        with self._trace_lock:
            self._trace_history.append(event)
        self._trace_events.put(event)

    def _send_trace_to(self, callback: Callable[[TraceEvent], None] | None) -> None:
        if callback is None:
            return
        while True:
            try:
                callback(self._trace_events.get_nowait())
            except Empty:
                return


class ShellConsole:
    """Teacher shell text, fake network client và live trace viewer."""

    def __init__(self) -> None:
        self.backend = AgentBackend()
        self.backend.start()
        self._next_request_id = 1
        self._trace_enabled = False
        self.stopped = False

    def execute(self, text: str, on_trace: Callable[[TraceEvent], None] | None = None) -> str:
        words = self._split(text)
        if isinstance(words, str):
            return words
        if words == ["trace"]:
            return self._format_trace()
        if words == ["trace", "on"]:
            self.backend.clear_live_trace()
            self._trace_enabled = True
            return "trace: on"
        if words == ["trace", "off"]:
            self._trace_enabled = False
            return "trace: off"
        command = self._to_command(words, text)
        if isinstance(command, str):
            return command
        self.backend.network.send_command(command)
        callback = on_trace if self._trace_enabled else None
        response = self.backend.wait_response(command.request_id, 1.0, callback)
        if command.action == "agent.shutdown" and response.ok:
            self.stopped = True
        return response.message

    def shutdown(self) -> None:
        self.backend.shutdown()

    def _split(self, text: str) -> list[str] | str:
        try:
            return shlex.split(text)
        except ValueError as error:
            return f"error: {error}"

    def _to_command(self, words: list[str], text: str) -> NetworkCommand | str:
        action = ""
        args: dict[str, str] = {}
        if words == ["help"]:
            action = "agent.help"
        elif words == ["status"]:
            action = "agent.status"
        elif words == ["quit"]:
            action = "agent.shutdown"
        elif words == ["keylogger", "on"]:
            action = "keylogger.start"
        elif words == ["keylogger", "off"]:
            action = "keylogger.stop"
        elif words == ["keys"]:
            action = "keylogger.buffer"
        elif words and words[0] == "classify":
            action = "classifier.rule_based"
            args["text"] = text.removeprefix("classify").strip()
        elif words and words[0] == "inject":
            action = "keylogger.inject"
            args["text"] = text.removeprefix("inject").strip()
        else:
            name = words[0] if words else ""
            return f"error: unknown command: {name}"
        command = NetworkCommand(self._next_request_id, action, args)
        self._next_request_id += 1
        return command

    def _format_trace(self) -> str:
        events = self.backend.get_trace_history()
        if not events:
            return "trace: empty"
        return "\n".join(event.format() for event in events)


class _KeyLoggerFeature:
    """KeyLogger thật với fake event source để demo không đọc input OS."""

    def __init__(self) -> None:
        self._events: Queue[KeyEvent] = Queue()
        self._processed = threading.Event()
        self._original_listener = keylogger_module.listen_keys
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    def start(self) -> bool:
        if self._running:
            return False
        self._reset_keylogger()
        keylogger_module.listen_keys = self._listen_keys
        self._running = True
        KeyLogger.start()
        return True

    def stop(self) -> bool:
        was_running = self._running
        KeyLogger.stop()
        keylogger_module.listen_keys = self._original_listener
        self._running = False
        return was_running

    def queue_text(self, text: str) -> bool:
        if not self._running:
            return False
        for character in text:
            event = self._event_for_character(character)
            if event is None:
                return False
            self._events.put(event)
        return True

    def get_buffer(self) -> str:
        return KeyLogger.get_current_buffer()

    def wait_for_buffer(self, expected: str, timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        while self.get_buffer() != expected:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not self._processed.wait(remaining):
                return False
            self._processed.clear()
        return True

    def _listen_keys(
        self,
        *,
        timeout: float | None,
        stop_event: threading.Event | None,
    ) -> Iterator[KeyEvent]:
        wait_timeout = 0.1 if timeout is None else timeout
        while stop_event is None or not stop_event.is_set():
            try:
                event = self._events.get(timeout=wait_timeout)
            except Empty:
                continue
            yield event
            self._processed.set()

    def _reset_keylogger(self) -> None:
        KeyLogger.stop()
        KeyLogger._buffer.clear()
        KeyLogger._cursor = 0
        KeyLogger._modifiers.clear()
        KeyLogger._caps_lock = False

    def _event_for_character(self, character: str) -> KeyEvent | None:
        if character.isalpha() or character.isdigit():
            return f"KEY_{character.upper()}", "down"
        if character == " ":
            return "KEY_SPACE", "down"
        return None


def _read_shell_commands(commands: Queue[str], stopped: threading.Event) -> None:
    while not stopped.is_set():
        try:
            command = input("server > ").strip()
        except (EOFError, StopIteration):
            commands.put("quit")
            return
        if command:
            commands.put(command)


def run_real(arguments: Sequence[str]) -> int:
    if tuple(arguments) != ("shell",):
        print("Usage: real shell", file=sys.stderr)
        return 2
    shell = ShellConsole()
    commands: Queue[str] = Queue()
    stopped = threading.Event()
    reader = threading.Thread(target=_read_shell_commands, args=(commands, stopped), daemon=True)
    reader.start()
    print("Fake network shell. Type help; trace on prints backend steps.")
    try:
        while not shell.stopped:
            try:
                command = commands.get(timeout=0.1)
            except Empty:
                continue
            result = shell.execute(command, lambda event: print(event.format()))
            print(result)
    except KeyboardInterrupt:
        print()
    finally:
        stopped.set()
        shell.shutdown()
    print("Agent stopped.")
    return 0


class AgentLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.shell = ShellConsole()

    def tearDown(self) -> None:
        self.shell.shutdown()

    @test_modes("fake")
    def test_shell_sends_text_command_through_fake_network(self) -> None:
        result = self.shell.execute("status")

        self.assertEqual(result, "agent: running; keylogger: False")
        self.assertIn("backend [1] completed: agent.status", self.shell.execute("trace"))

    @test_modes("fake")
    def test_help_and_live_trace_are_shell_commands(self) -> None:
        events: list[str] = []

        self.assertIn("trace on|off", self.shell.execute("help"))
        self.assertEqual(self.shell.execute("trace on"), "trace: on")
        self.assertIn("agent: running", self.shell.execute("status", lambda event: events.append(event.format())))

        self.assertTrue(any("received: agent.status" in event for event in events))
        self.assertTrue(any("completed: agent.status" in event for event in events))

    @test_modes("fake")
    def test_backend_calls_threaded_feature_and_shutdown_cleans_up(self) -> None:
        self.assertEqual(self.shell.execute("keylogger on"), "keylogger: started")
        self.assertEqual(self.shell.execute("inject hello"), "keylogger: queued hello")
        self.assertTrue(self.shell.backend._keylogger.wait_for_buffer("hello", timeout=1.0))

        self.assertEqual(self.shell.execute("quit"), "agent: stopping")
        self.shell.shutdown()

        self.assertFalse(self.shell.backend.is_running)
        self.assertFalse(self.shell.backend._keylogger.running)

    @test_modes("mock")
    def test_shell_rejects_unknown_text_without_sending_it(self) -> None:
        self.assertEqual(self.shell.execute("unknown"), "error: unknown command: unknown")


if __name__ == "__main__":
    raise SystemExit(run_module(sys.modules[__name__]))
