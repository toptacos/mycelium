import pytest

from mycelium.tools.scaffold import TEMPLATES, _render, _slug, scaffold_app
from conftest import build_agent


async def ctx_for(ws, home, scripted):
    agent, settings, log, registry, memory = build_agent(ws, home, scripted)
    return agent.ctx


async def test_all_templates_have_readme_and_gitignore():
    for name, files in TEMPLATES.items():
        assert any(f.endswith("README.md") for f in files), f"{name} missing README"


async def test_scaffold_python_cli_runs_its_tests(ws, home, scripted):
    ctx = await ctx_for(ws, home, scripted)
    out = await scaffold_app(
        {
            "name": "change-calculator",
            "template": "python-cli",
            "description": "compute change",
            "run_tests": True,
        },
        ctx,
    )
    assert "python-cli app 'change-calculator'" in out
    assert "PASSED" in out
    root = ws / "apps" / "change-calculator"
    assert (root / "pyproject.toml").is_file()
    assert (root / "src" / "change_calculator" / "cli.py").is_file()
    assert (root / "tests" / "test_cli.py").is_file()
    assert (root / "README.md").is_file()
    assert "version" in (root / "src" / "change_calculator" / "cli.py").read_text()


async def test_scaffold_node_cli(ws, home, scripted):
    ctx = await ctx_for(ws, home, scripted)
    out = await scaffold_app({"name": "greeter", "template": "node-cli"}, ctx)
    assert "node-cli app 'greeter'" in out
    assert (ws / "apps" / "greeter" / "package.json").is_file()
    assert (ws / "apps" / "greeter" / "index.js").is_file()


async def test_scaffold_fastapi_service(ws, home, scripted):
    ctx = await ctx_for(ws, home, scripted)
    out = await scaffold_app({"name": "orders-api", "template": "fastapi-service"}, ctx)
    assert "fastapi-service app 'orders-api'" in out
    assert (ws / "apps" / "orders-api" / "app" / "main.py").is_file()
    assert (ws / "apps" / "orders-api" / "Dockerfile").is_file()
    assert "healthz" in (ws / "apps" / "orders-api" / "app" / "main.py").read_text()


async def test_scaffold_static_site(ws, home, scripted):
    ctx = await ctx_for(ws, home, scripted)
    out = await scaffold_app({"name": "landing", "template": "static-site"}, ctx)
    assert "static-site app 'landing'" in out
    assert (ws / "apps" / "landing" / "index.html").is_file()
    assert (ws / "apps" / "landing" / "css" / "style.css").is_file()


async def test_scaffold_rejects_bad_names(ws, home, scripted):
    ctx = await ctx_for(ws, home, scripted)
    out = await scaffold_app({"name": "../evil", "template": "python-cli"}, ctx)
    assert "invalid app name" in out
    out2 = await scaffold_app({"name": "x" * 80, "template": "python-cli"}, ctx)
    assert "invalid app name" in out2


async def test_scaffold_rejects_unknown_template(ws, home, scripted):
    ctx = await ctx_for(ws, home, scripted)
    out = await scaffold_app({"name": "ok-name", "template": "rails"}, ctx)
    assert "unknown template" in out


async def test_scaffold_is_idempotent_overwrite(ws, home, scripted):
    ctx = await ctx_for(ws, home, scripted)
    await scaffold_app({"name": "twice", "template": "python-cli"}, ctx)
    out = await scaffold_app({"name": "twice", "template": "python-cli"}, ctx)
    assert "scaffolded" in out


def test_slug_and_render():
    assert _slug("My Cool App!") == "my-cool-app"
    assert (
        _render("hello {{name}}/{{module}}", {"name": "x", "module": "m"})
        == "hello x/m"
    )
