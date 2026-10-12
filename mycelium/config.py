from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from mycelium.paths import (
    APP_NAME,
    ENV_BACKEND,
    ENV_MODEL,
    ENV_READ_ONLY,
    ENV_VERBOSE,
    app_home,
    resolve_workspace,
)

DEFAULT_CONFIG_NAME = f"{APP_NAME}.toml"

DEFAULT_BACKENDS: dict[str, dict] = {
    "local": {
        "kind": "ollama",
        "base_url": "http://127.0.0.1:11434",
        "default_model": "qwen3:0.6b",
        "models": ["qwen3:0.6b", "qwen2.5-coder:latest", "llama3:latest"],
    },
    "openrouter": {
        "kind": "openai",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "default_model": "qwen/qwen3-coder:free",
        "models": [
            "qwen/qwen3-coder:free",
            "deepseek/deepseek-chat-v3-0324:free",
            "google/gemini-2.0-flash-exp:free",
        ],
    },
    "gemini": {
        "kind": "gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "api_key_env": "GOOGLE_API_KEY",
        "default_model": "gemini-2.0-flash",
        "models": ["gemini-2.0-flash", "gemini-2.5-flash-lite"],
    },
    "deepseek": {
        "kind": "openai",
        "base_url": "https://api.deepseek.com/v1",
        "api_key_env": "DEEPSEEK_API_KEY",
        "default_model": "deepseek-chat",
        "models": ["deepseek-chat", "deepseek-reasoner"],
    },
    "anthropic": {
        "kind": "anthropic",
        "base_url": "https://api.anthropic.com",
        "api_key_env": "ANTHROPIC_API_KEY",
        "default_model": "claude-sonnet-4-5",
        "models": ["claude-sonnet-4-5", "claude-haiku-4-5"],
    },
}


@dataclass
class BackendConfig:
    name: str
    kind: str
    base_url: str
    api_key_env: str | None = None
    default_model: str | None = None
    models: list[str] = field(default_factory=list)

    @property
    def api_key(self) -> str | None:
        if not self.api_key_env:
            return None
        return os.environ.get(self.api_key_env)

    @property
    def needs_key(self) -> bool:
        return self.api_key_env is not None

    @property
    def is_local(self) -> bool:
        return self.kind == "ollama" or self.base_url.startswith(
            ("http://127.", "http://localhost")
        )


@dataclass
class Settings:
    home: Path
    workspace: Path
    backend: str = "local"
    model: str = ""
    strong_backend: str = "local"
    strong_model: str = ""
    context_window: int = 32768
    reserve_tokens: int = 1024
    compact_threshold: float = 0.8
    max_steps: int = 8
    verbose: bool = False
    read_only: bool = False
    port: int = 8787
    backends: dict[str, BackendConfig] = field(default_factory=dict)
    connections: dict[str, dict] = field(default_factory=dict)

    def resolve_model(self, model: str | None = None) -> tuple[str, str]:
        spec = (
            model
            or self.model
            or f"{self.backend}:{self.backends[self.backend].default_model}"
        )
        if ":" in spec and spec.split(":", 1)[0] in self.backends:
            backend_name, _, model_name = spec.partition(":")
        else:
            backend_name = self.backend
            model_name = spec
        backend = self.backends.get(backend_name)
        if backend is None:
            known = ", ".join(sorted(self.backends))
            raise KeyError(f"unknown backend {backend_name!r}; known: {known}")
        return backend_name, model_name or (backend.default_model or "")

    def backend_config(self, name: str) -> BackendConfig:
        if name not in self.backends:
            known = ", ".join(sorted(self.backends))
            raise KeyError(f"unknown backend {name!r}; known: {known}")
        return self.backends[name]


def _merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def _read_toml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("rb") as fh:
        return tomllib.load(fh)


def _backend_configs(raw: dict) -> dict[str, BackendConfig]:
    merged: dict[str, dict] = {
        name: dict(spec) for name, spec in DEFAULT_BACKENDS.items()
    }
    for name, spec in (raw.get("backends") or {}).items():
        merged[name] = _merge(merged.get(name, {}), spec)
    out: dict[str, BackendConfig] = {}
    for name, spec in merged.items():
        out[name] = BackendConfig(
            name=name,
            kind=spec.get("kind", "openai"),
            base_url=spec.get("base_url", ""),
            api_key_env=spec.get("api_key_env"),
            default_model=spec.get("default_model"),
            models=list(spec.get("models", [])),
        )
    return out


def load_settings(
    workspace: str | Path | None = None,
    *,
    backend: str | None = None,
    model: str | None = None,
    verbose: bool | None = None,
    read_only: bool | None = None,
    home: Path | None = None,
    config_path: Path | None = None,
) -> Settings:
    home = home or app_home()
    ws = resolve_workspace(workspace)

    raw: dict = {}
    raw = _merge(raw, _read_toml(home / DEFAULT_CONFIG_NAME))
    raw = _merge(raw, _read_toml(ws / DEFAULT_CONFIG_NAME))
    if config_path:
        raw = _merge(raw, _read_toml(Path(config_path)))

    settings = Settings(
        home=home,
        workspace=ws,
        backend=raw.get("backend", "local"),
        model=raw.get("model", ""),
        strong_backend=raw.get("strong_backend", raw.get("backend", "local")),
        strong_model=raw.get("strong_model", ""),
        context_window=int(raw.get("context_window", 32768)),
        reserve_tokens=int(raw.get("reserve_tokens", 1024)),
        compact_threshold=float(raw.get("compact_threshold", 0.8)),
        max_steps=int(raw.get("max_steps", 8)),
        verbose=bool(raw.get("verbose", False)),
        read_only=bool(raw.get("read_only", False)),
        port=int(raw.get("port", 8787)),
        backends=_backend_configs(raw),
        connections=dict(raw.get("connections", {})),
    )

    if backend:
        settings.backend = backend
    if model:
        settings.model = model
    env_backend = os.environ.get(ENV_BACKEND)
    if env_backend and not backend:
        settings.backend = env_backend
    env_model = os.environ.get(ENV_MODEL)
    if env_model and not model:
        settings.model = env_model
    if verbose is not None:
        settings.verbose = verbose
    elif os.environ.get(ENV_VERBOSE, "").lower() in ("1", "true", "yes"):
        settings.verbose = True
    if read_only is not None:
        settings.read_only = read_only
    elif os.environ.get(ENV_READ_ONLY, "").lower() in ("1", "true", "yes"):
        settings.read_only = True

    settings.home.mkdir(parents=True, exist_ok=True)
    return settings
