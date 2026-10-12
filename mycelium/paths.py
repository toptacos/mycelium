from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "mycelium"
COMMAND = "mcy"
DEFAULT_PORT = 8787
CCR_COMPAT_PORT = 3456

ENV_HOME = "MYCELIUM_HOME"
ENV_BACKEND = "MYCELIUM_BACKEND"
ENV_MODEL = "MYCELIUM_MODEL"
ENV_VERBOSE = "MYCELIUM_VERBOSE"
ENV_WORKSPACE = "MYCELIUM_WORKSPACE"
ENV_READ_ONLY = "MYCELIUM_READ_ONLY"


def app_home() -> Path:
    override = os.environ.get(ENV_HOME)
    if override:
        return Path(override).expanduser().resolve()
    return Path.home() / f".{APP_NAME}"


def resolve_workspace(path: str | Path | None) -> Path:
    if path is None:
        path = os.environ.get(ENV_WORKSPACE) or Path.cwd()
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = (Path.cwd() / p).resolve()
    return p
