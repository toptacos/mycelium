import os
from pathlib import Path

import pytest

from mycelium.config import Settings, load_settings
from mycelium.paths import ENV_BACKEND, ENV_MODEL


def test_defaults_when_no_config(ws: Path, home: Path):
    settings = load_settings(workspace=ws, home=home)
    assert settings.backend == "local"
    assert "local" in settings.backends
    assert settings.backend_config("local").kind == "ollama"
    assert settings.context_window == 32768


def test_project_config_overrides_global(ws: Path, home: Path):
    (home / "mycelium.toml").write_text('backend = "local"\ncontext_window = 4096\n')
    (ws / "mycelium.toml").write_text("context_window = 16384\n")
    settings = load_settings(workspace=ws, home=home)
    assert settings.context_window == 16384
    assert settings.backend == "local"


def test_global_config_used_when_no_project_config(ws: Path, home: Path):
    (home / "mycelium.toml").write_text(
        'backend = "openrouter"\nmodel = "openrouter:qwen/qwen3-coder:free"\n'
    )
    settings = load_settings(workspace=ws, home=home)
    assert settings.backend == "openrouter"
    assert settings.model == "openrouter:qwen/qwen3-coder:free"


def test_env_overrides(ws: Path, home: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(ENV_BACKEND, "deepseek")
    monkeypatch.setenv(ENV_MODEL, "deepseek:deepseek-chat")
    settings = load_settings(workspace=ws, home=home)
    assert settings.backend == "deepseek"


def test_cli_flags_beat_env(ws: Path, home: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(ENV_BACKEND, "deepseek")
    settings = load_settings(workspace=ws, home=home, backend="gemini")
    assert settings.backend == "gemini"


def test_resolve_model_parsing(ws: Path, home: Path):
    settings = load_settings(workspace=ws, home=home)
    assert settings.resolve_model("local:qwen3:0.6b") == ("local", "qwen3:0.6b")
    assert settings.resolve_model("qwen3:0.6b") == ("local", "qwen3:0.6b")
    assert settings.resolve_model("openrouter:deepseek/deepseek-chat:free") == (
        "openrouter",
        "deepseek/deepseek-chat:free",
    )
    # unknown prefixes are treated as part of the model name (ollama tags
    # contain colons), so only explicit backend resolution can fail
    assert settings.resolve_model("ghostbackend:m") == ("local", "ghostbackend:m")
    with pytest.raises(KeyError):
        settings.backend_config("ghostbackend")


def test_user_backend_override_merges(ws: Path, home: Path):
    (ws / "mycelium.toml").write_text(
        '[backends.custom]\nkind = "openai"\nbase_url = "http://127.0.0.1:9999/v1"\n'
    )
    settings = load_settings(workspace=ws, home=home)
    assert settings.backend_config("custom").kind == "openai"
    assert settings.backends["custom"].api_key is None


def test_connections_parsed(ws: Path, home: Path):
    (ws / "mycelium.toml").write_text(
        '[connections.example]\nbase_url = "http://127.0.0.1:9799"\nmethods = ["GET"]\n\n'
        '[connections.gh]\nbase_url = "https://api.github.com"\nauth_env = "GITHUB_TOKEN"\n'
    )
    settings = load_settings(workspace=ws, home=home)
    assert settings.connections["example"]["base_url"] == "http://127.0.0.1:9799"
    assert settings.connections["gh"]["auth_env"] == "GITHUB_TOKEN"


def test_read_only_env(ws: Path, home: Path, monkeypatch: pytest.MonkeyPatch):
    from mycelium.paths import ENV_READ_ONLY

    monkeypatch.setenv(ENV_READ_ONLY, "1")
    settings = load_settings(workspace=ws, home=home)
    assert settings.read_only is True
