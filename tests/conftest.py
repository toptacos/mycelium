import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from mycelium.agent import Agent, AgentConfig
from mycelium.backends import ChatResponse, ScriptedBackend
from mycelium.config import load_settings
from mycelium.memory import MemoryStore
from mycelium.runtime import build_registry, make_event_log, make_memory
from mycelium.telemetry import EventLog
from mycelium.tools import ToolContext
from mycelium.workflows import WorkflowRunner


class FakeProvider:
    """In-process HTTP server that records requests and serves canned JSON."""

    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []
        self.routes: dict[tuple[str, str], tuple[int, Any]] = {}
        self.server: ThreadingHTTPServer | None = None
        self.port = 0

    def route(
        self, method: str, path: str, status: int = 200, payload: Any = None
    ) -> None:
        self.routes[(method, path)] = (status, payload)

    def route_raw(
        self,
        method: str,
        path: str,
        status: int = 200,
        text: str = "",
        content_type: str = "text/html",
    ) -> None:
        self.routes[(method, path)] = (status, ("__raw__", text, content_type))

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def __enter__(self) -> "FakeProvider":
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args: Any) -> None:
                pass

            def _handle(self, method: str) -> None:
                length = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(length) if length else b""
                try:
                    body = json.loads(raw) if raw else None
                except json.JSONDecodeError:
                    body = {"_raw": raw.decode(errors="replace")}
                outer.requests.append(
                    {
                        "method": method,
                        "path": self.path,
                        "headers": dict(self.headers),
                        "body": body,
                    }
                )
                key = (method, self.path.split("?")[0])
                if key not in outer.routes:
                    self.send_response(404)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                status, payload = outer.routes[key]
                if callable(payload):
                    status, payload = payload(outer.requests[-1])
                if (
                    isinstance(payload, tuple)
                    and len(payload) == 3
                    and payload[0] == "__raw__"
                ):
                    _, text, content_type = payload
                    data = text.encode()
                    self.send_response(status)
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                data = json.dumps(payload if payload is not None else {}).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self) -> None:
                self._handle("GET")

            def do_POST(self) -> None:
                self._handle("POST")

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc: Any) -> None:
        if self.server:
            self.server.shutdown()
            self.server.server_close()


@pytest.fixture
def ws(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    (workspace / ".mycelium").mkdir(parents=True)
    return workspace


@pytest.fixture
def home(tmp_path: Path) -> Path:
    h = tmp_path / "home"
    h.mkdir()
    return h


@pytest.fixture
def scripted() -> ScriptedBackend:
    return ScriptedBackend()


def build_agent(
    ws: Path,
    home: Path,
    backend: Any,
    *,
    settings_overrides: dict | None = None,
    config: AgentConfig | None = None,
):
    settings = load_settings(workspace=ws, home=home)
    for key, value in (settings_overrides or {}).items():
        setattr(settings, key, value)
    log = make_event_log(settings)
    memory = make_memory(settings)
    registry = build_registry()
    if settings.read_only:
        registry = registry.filter(include_mutating=False)
    ctx = ToolContext(
        workspace=settings.workspace,
        settings=settings,
        memory=memory,
        log=log,
        backend=backend,
        read_only=settings.read_only,
    )
    runner = WorkflowRunner(registry, ctx)
    agent = Agent(
        settings, backend, registry, memory, log, config=config, runner=runner
    )
    return agent, settings, log, registry, memory


@pytest.fixture
def make_agent(ws: Path, home: Path, scripted: ScriptedBackend):
    def factory(**kwargs: Any):
        return build_agent(ws, home, scripted, **kwargs)

    return factory


@pytest.fixture
def provider() -> FakeProvider:
    with FakeProvider() as fp:
        yield fp


def tool_call_response(name: str, arguments: dict, content: str = "") -> ChatResponse:
    from mycelium.backends import ToolCall

    return ChatResponse(
        content=content,
        tool_calls=[ToolCall(id=f"call_1", name=name, arguments=arguments)],
        prompt_tokens=10,
        completion_tokens=5,
    )


def final_response(text: str) -> ChatResponse:
    return ChatResponse(content=text, prompt_tokens=12, completion_tokens=8)
