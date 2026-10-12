import json

import pytest

from mycelium.backends import ChatResponse
from mycelium.workflows import WorkflowError, load_workflow
from mycelium.tools import ToolContext
from mycelium.runtime import build_registry, make_event_log, make_memory
from mycelium.config import load_settings
from mycelium.workflows import WorkflowRunner


async def runner_for(ws, home, scripted, **overrides):
    settings = load_settings(workspace=ws, home=home, **overrides)
    log = make_event_log(settings)
    memory = make_memory(settings)
    registry = build_registry()
    ctx = ToolContext(
        workspace=settings.workspace,
        settings=settings,
        memory=memory,
        log=log,
        backend=scripted,
    )
    return WorkflowRunner(registry, ctx)


async def write_wf(ws, text: str, name: str = "wf.yaml"):
    d = ws / "workflows"
    d.mkdir(exist_ok=True)
    p = d / name
    p.write_text(text)
    return p


MATRIX_WF = """
name: matrix-demo
description: matrix over python versions
matrix:
  python: ["a", "b"]
steps:
  - id: mark
    tool: fs_write
    args:
      path: "matrix-{{matrix.python}}.txt"
      content: "ran with {{matrix.python}}"
"""

WHEN_WF = """
name: when-demo
inputs:
  live:
    default: ""
steps:
  - id: gated
    tool: fs_write
    args:
      path: "gated.txt"
      content: "gated ran"
    when: "{{inputs.live}}"
  - id: always
    tool: fs_write
    args:
      path: "always.txt"
      content: "always ran"
"""


async def test_matrix_iterates_all_combos(ws, home, scripted):
    runner = await runner_for(ws, home, scripted, command_allow=["python3"])
    path = await write_wf(ws, MATRIX_WF)
    result = await runner.run(path)
    assert result.ok
    assert [s.id for s in result.steps] == ["mark[a]", "mark[b]"]
    assert (ws / "matrix-a.txt").read_text() == "ran with a"
    assert (ws / "matrix-b.txt").read_text() == "ran with b"


async def test_matrix_multi_axis(ws, home, scripted):
    runner = await runner_for(ws, home, scripted, command_allow=["python3"])
    wf = """
name: two-axis
matrix:
  py: ["3.11", "3.12"]
  os: ["linux", "mac"]
steps:
  - id: t
    tool: fs_write
    args:
      path: "t-{{matrix.py}}-{{matrix.os}}.txt"
      content: "{{matrix.py}}/{{matrix.os}}"
"""
    path = await write_wf(ws, wf)
    result = await runner.run(path)
    assert result.ok
    assert len(result.steps) == 4
    assert (ws / "t-3.11-linux.txt").is_file()
    assert (ws / "t-3.12-mac.txt").is_file()


async def test_matrix_dry_run_substitutes(ws, home, scripted):
    runner = await runner_for(ws, home, scripted, command_allow=["python3"])
    path = await write_wf(ws, MATRIX_WF)
    result = await runner.run(path, dry_run=True)
    assert result.ok
    assert len(result.steps) == 2
    assert "matrix-a.txt" in result.outputs["mark[a]"]
    assert not (ws / "matrix-a.txt").exists()


async def test_matrix_rejects_empty_axis(ws, home, scripted):
    path = await write_wf(
        ws,
        """
name: bad
matrix:
  py: []
steps:
  - id: t
    tool: fs_list
""",
    )
    with pytest.raises(WorkflowError, match="non-empty list"):
        load_workflow(path)


async def test_when_true_runs_step(ws, home, scripted):
    runner = await runner_for(ws, home, scripted, command_allow=["python3"])
    path = await write_wf(ws, WHEN_WF)
    result = await runner.run(path, {"live": "1"})
    assert result.ok
    assert (ws / "gated.txt").read_text() == "gated ran"
    assert [s.id for s in result.steps] == ["gated", "always"]


async def test_when_false_skips_step(ws, home, scripted):
    runner = await runner_for(ws, home, scripted, command_allow=["python3"])
    path = await write_wf(ws, WHEN_WF)
    result = await runner.run(path)
    assert result.ok
    assert not (ws / "gated.txt").exists()
    assert (ws / "always.txt").read_text() == "always ran"
    assert result.steps[0].output == "(skipped)"


async def test_when_dry_run_marks_skip(ws, home, scripted):
    runner = await runner_for(ws, home, scripted, command_allow=["python3"])
    path = await write_wf(ws, WHEN_WF)
    result = await runner.run(path, dry_run=True)
    assert result.steps[0].output == "(skipped)"
    assert result.steps[1].output == "(dry-run)"


async def test_run_command_end_to_end_via_workflow(ws, home, scripted):
    runner = await runner_for(ws, home, scripted, command_allow=["python3"])
    path = await write_wf(
        ws,
        """
name: cmd-wf
steps:
  - id: run
    tool: run_command
    args:
      command: "python3 -c \\"print(6 * 7)\\""
""",
    )
    result = await runner.run(path)
    assert result.ok
    assert "42" in result.outputs["run"]


async def test_run_command_denied_fails_workflow(ws, home, scripted):
    runner = await runner_for(ws, home, scripted)
    path = await write_wf(
        ws,
        """
name: denied-wf
steps:
  - id: run
    tool: run_command
    args:
      command: "sh -c 'echo pwned'"
""",
    )
    result = await runner.run(path)
    assert result.ok is False
    assert "not in the command allowlist" in result.failed_step.error


async def test_matrix_failure_aggregates(ws, home, scripted):
    runner = await runner_for(ws, home, scripted, command_allow=["python3"])
    path = await write_wf(
        ws,
        """
name: matrix-fail
matrix:
  v: ["ok", "bad"]
steps:
  - id: maybe-fail
    tool: run_command
    args:
      command: "python3 -c \\"import sys; sys.exit(0 if '{{matrix.v}}' == 'ok' else 1)\\""
""",
    )
    result = await runner.run(path)
    assert result.ok is False
    assert [s.ok for s in result.steps] == [True, False]
