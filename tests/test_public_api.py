"""Smoke the package's public exports used by external importers."""

from __future__ import annotations

import mycelium


def test_version_and_all_exports():
    assert isinstance(mycelium.__version__, str)
    assert mycelium.__version__
    for name in mycelium.__all__:
        assert hasattr(mycelium, name), f"missing public export: {name}"


def test_settings_and_registry_assemble():
    settings = mycelium.load_settings()
    assert settings is not None
    registry = mycelium.ToolRegistry()
    assert isinstance(registry, mycelium.ToolRegistry)
    ctx = mycelium.ContextManager(window_tokens=4096, reserve_tokens=256)
    assert ctx.budget_tokens == 4096 - 256


def test_workflow_loader_finds_bundled_release_notes(tmp_path):
    from pathlib import Path

    src = Path(__file__).resolve().parents[1] / "workflows" / "release-notes.yaml"
    assert src.is_file()
    wf = mycelium.load_workflow(src)
    assert wf.name == "release-notes"
    assert len(wf.steps) >= 1
