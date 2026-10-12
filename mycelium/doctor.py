from __future__ import annotations

import sys
from dataclasses import dataclass

from mycelium.config import Settings

OK = "OK"
FAIL = "FAIL"
SKIP = "skip"


@dataclass
class Check:
    name: str
    status: str
    detail: str

    @property
    def ok(self) -> bool:
        return self.status == OK


async def run_checks(settings: Settings) -> list[Check]:
    checks: list[Check] = []

    checks.append(
        Check(
            "python",
            OK if sys.version_info >= (3, 11) else FAIL,
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        )
    )
    checks.append(
        Check("home dir", OK if settings.home.is_dir() else FAIL, str(settings.home))
    )
    checks.append(
        Check(
            "workspace",
            OK if settings.workspace.is_dir() else FAIL,
            str(settings.workspace),
        )
    )

    project_cfg = settings.workspace / "mycelium.toml"
    global_cfg = settings.home / "mycelium.toml"
    if project_cfg.exists():
        checks.append(Check("config", OK, f"project config: {project_cfg}"))
    elif global_cfg.exists():
        checks.append(Check("config", OK, f"global config: {global_cfg}"))
    else:
        checks.append(Check("config", OK, "no config file; using built-in defaults"))

    import httpx

    for name, cfg in settings.backends.items():
        active = name == settings.backend
        if cfg.kind == "scripted":
            checks.append(Check(f"backend:{name}", OK, "scripted test double"))
            continue
        label = f"{cfg.kind} @ {cfg.base_url}"
        if cfg.is_local:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(f"{cfg.base_url.rstrip('/')}/api/tags")
                    models = [m.get("name") for m in resp.json().get("models", [])]
                    running = ", ".join(models[:6]) or "(no models pulled)"
                    if resp.status_code == 200:
                        checks.append(
                            Check(
                                f"backend:{name}", OK, f"reachable; models: {running}"
                            )
                        )
                    else:
                        checks.append(
                            Check(
                                f"backend:{name}",
                                FAIL if active else SKIP,
                                f"HTTP {resp.status_code}",
                            )
                        )
            except Exception as exc:
                status = FAIL if active else SKIP
                checks.append(
                    Check(
                        f"backend:{name}",
                        status,
                        f"unreachable ({type(exc).__name__}); "
                        + (
                            "required: it is the active backend"
                            if active
                            else "not in use"
                        ),
                    )
                )
            continue
        if cfg.api_key:
            checks.append(Check(f"backend:{name}", OK, f"{label}, key set"))
        else:
            detail = f"not configured (set ${cfg.api_key_env} to enable)"
            if active:
                detail += " - ACTIVE backend"
            checks.append(Check(f"backend:{name}", FAIL if active else SKIP, detail))

    return checks
