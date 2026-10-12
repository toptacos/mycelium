from __future__ import annotations

import re
from typing import Any

from mycelium.tools import Tool, ToolContext, resolve_in_workspace


def _slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "app"


def _render(template: str, values: dict[str, str]) -> str:
    out = template
    for k, v in values.items():
        out = out.replace("{{" + k + "}}", v)
    return out


TEMPLATES: dict[str, dict[str, str]] = {
    "python-cli": {
        "pyproject.toml": """[project]
name = "{{name}}"
version = "0.1.0"
description = "{{description}}"
requires-python = ">=3.11"

[project.scripts]
{{name}} = "{{module}}.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
""",
        "src/{{module}}/__init__.py": """__version__ = "0.1.0"
""",
        "src/{{module}}/cli.py": """import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="{{name}}", description="{{description}}")
    parser.add_argument("--version", action="store_true", help="print version and exit")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.version:
        from {{module}} import __version__

        print(f"{{name}} {__version__}")
        return 0
    print("hello from {{name}}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
""",
        "tests/conftest.py": """import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
""",
        "tests/test_cli.py": """from {{module}}.cli import build_parser


def test_parser_version_flag():
    parser = build_parser()
    args = parser.parse_args(["--version"])
    assert args.version is True
""",
        "README.md": """# {{name}}

{{description}}

## Usage

```bash
python -m {{module}}.cli --version
```

## Tests

```bash
python -m pytest tests/ -v
```
""",
        ".gitignore": """__pycache__/
*.pyc
.venv/
dist/
""",
    },
    "fastapi-service": {
        "requirements.txt": "fastapi>=0.115\nuvicorn[standard]>=0.30\nhttpx>=0.28\n",
        "app/__init__.py": "",
        "app/main.py": """from fastapi import FastAPI

app = FastAPI(title="{{name}}")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/items/{item_id}")
def read_item(item_id: int) -> dict[str, int]:
    return {"item_id": item_id}
""",
        "tests/test_api.py": """from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthz():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_read_item():
    resp = client.get("/items/42")
    assert resp.status_code == 200
    assert resp.json() == {"item_id": 42}
""",
        "Dockerfile": """FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
""",
        "README.md": """# {{name}}

{{description}}

## Run

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Test

```bash
python -m pytest tests/ -v
```
""",
    },
    "node-cli": {
        "package.json": """{
  "name": "{{name}}",
  "version": "0.1.0",
  "description": "{{description}}",
  "main": "index.js",
  "bin": {"{{name}}": "./index.js"},
  "scripts": {"test": "node test.js"}
}
""",
        "index.js": """#!/usr/bin/env node
const args = process.argv.slice(2);

function main() {
  if (args.includes("--version")) {
    console.log("{{name}} 0.1.0");
    return 0;
  }
  console.log("hello from {{name}}");
  return 0;
}

process.exit(main());
""",
        "test.js": """const assert = require("node:assert");

assert.strictEqual(1 + 1, 2);
console.log("ok - {{name}} smoke test passed");
""",
        "README.md": """# {{name}}

{{description}}

## Usage

```bash
node index.js
npm test
```
""",
    },
    "static-site": {
        "index.html": """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{{name}}</title>
  <link rel="stylesheet" href="css/style.css" />
</head>
<body>
  <main>
    <h1>{{name}}</h1>
    <p>{{description}}</p>
    <button id="cta">Click me</button>
    <p id="count">clicks: 0</p>
  </main>
  <script src="js/app.js"></script>
</body>
</html>
""",
        "css/style.css": """:root { color-scheme: light dark; }
body { font-family: system-ui, sans-serif; margin: 4rem auto; max-width: 32rem; }
button { font-size: 1rem; padding: 0.5rem 1rem; }
""",
        "js/app.js": """let clicks = 0;
document.getElementById("cta").addEventListener("click", () => {
  clicks += 1;
  document.getElementById("count").textContent = `clicks: ${clicks}`;
});
""",
        "README.md": """# {{name}}

{{description}}

Open `index.html` in a browser, or serve with `python -m http.server`.
""",
    },
}


async def scaffold_app(args: dict[str, Any], ctx: ToolContext) -> str:
    name: str = args["name"].strip()
    template = args.get("template", "python-cli").strip()
    description = args.get(
        "description", f"A {template} scaffolded by mycelium"
    ).strip()
    run_tests = bool(args.get("run_tests", False))

    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", name):
        return f"error: invalid app name {name!r}; use letters, digits, dot, dash, underscore (max 64 chars)"
    if template not in TEMPLATES:
        return f"error: unknown template {template!r}; available: {', '.join(sorted(TEMPLATES))}"

    module = _slug(name).replace("-", "_")
    values = {"name": name, "description": description, "module": module}
    app_root = resolve_in_workspace(ctx.workspace, f"apps/{name}")

    created: list[str] = []
    for rel_tmpl, content_tmpl in TEMPLATES[template].items():
        rel = _render(rel_tmpl, values)
        target = app_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_render(content_tmpl, values), encoding="utf-8")
        created.append(target.relative_to(ctx.workspace.resolve()).as_posix())

    lines = [
        f"scaffolded {template} app {name!r} at apps/{name}",
        f"files ({len(created)}):",
    ]
    lines += [f"  {c}" for c in sorted(created)]

    if run_tests:
        result = await _run_tests(app_root, template)
        lines.append("")
        lines.append(result)

    return "\n".join(lines)


async def _run_tests(app_root, template: str) -> str:
    import asyncio

    if template == "node-cli":
        cmd, cwd = ["node", "test.js"], app_root
    elif template == "fastapi-service":
        return "test run skipped: fastapi-service tests need `pip install -r requirements.txt` first (deps not vendored)"
    else:
        import sys

        cmd, cwd = [sys.executable, "-m", "pytest", "tests/", "-q"], app_root
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=180)
        tail = stdout.decode(errors="replace").strip().splitlines()[-15:]
        status = (
            "PASSED" if proc.returncode == 0 else f"FAILED (exit {proc.returncode})"
        )
        return f"tests {status}:\n" + "\n".join("  " + line for line in tail)
    except asyncio.TimeoutError:
        return "tests FAILED: timeout after 180s"
    except FileNotFoundError:
        return f"tests skipped: {cmd[0]} not found on PATH"


def scaffold_tool() -> Tool:
    return Tool(
        name="scaffold_app",
        description=(
            "Scaffold a new application from a built-in template into workspace apps/<name>/. "
            "Templates: python-cli, fastapi-service, node-cli, static-site. "
            "Set run_tests=true to execute the scaffold's own test suite."
        ),
        parameters={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Application name (becomes directory apps/<name>)",
                },
                "template": {
                    "type": "string",
                    "enum": [
                        "python-cli",
                        "fastapi-service",
                        "node-cli",
                        "static-site",
                    ],
                    "default": "python-cli",
                },
                "description": {"type": "string"},
                "run_tests": {"type": "boolean", "default": False},
            },
            "required": ["name", "template"],
        },
        handler=scaffold_app,
        mutating=True,
    )
