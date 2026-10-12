import json

import pytest

from mycelium.backends import ChatResponse
from mycelium.workflows import WorkflowError, WorkflowRunner, load_workflow, substitute
from mycelium.tools import ToolContext
from mycelium.runtime import build_registry, make_event_log, make_memory
from mycelium.config import load_settings


async def runner_for(ws, home, scripted, checkpoint_dir=None):
    settings = load_settings(workspace=ws, home=home)
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
    return WorkflowRunner(registry, ctx, checkpoint_dir=checkpoint_dir)


async def write_wf(ws, name: str, text: str):
    p = ws / "workflows"
    p.mkdir(exist_ok=True)
    path = p / f"{name}.yaml"
    path.write_text(text)
    return path


TOOL_ONLY_WF = """
name: pure-tools
description: tools only, no llm
inputs:
  target:
    default: "notes/out.txt"
steps:
  - id: write
    tool: fs_write
    args:
      path: "{{inputs.target}}"
      content: "written by workflow"
  - id: read
    tool: fs_read
    args:
      path: "{{inputs.target}}"
"""

MIXED_WF = """
name: mixed
description: tool then llm then tool
steps:
  - id: seed
    tool: fs_write
    args:
      path: "seed.txt"
      content: "hello workflow world"
  - id: read
    tool: fs_read
    args:
      path: "seed.txt"
  - id: draft
    llm: "Summarize: {{steps.read.output}}"
  - id: final
    tool: fs_write
    args:
      path: "final.txt"
      content: "{{steps.draft.output}}"
"""

FAILING_WF = """
name: failing
description: step one fails
steps:
  - id: boom
    tool: fs_read
    args:
      path: "../outside.md"
  - id: after
    tool: fs_list
    args:
      path: "."
"""


async def test_pure_tool_workflow(ws, home, scripted):
    runner = await runner_for(ws, home, scripted)
    path = await write_wf(ws, "pure-tools", TOOL_ONLY_WF)
    result = await runner.run(path)
    assert result.ok
    assert [s.id for s in result.steps] == ["write", "read"]
    assert (ws / "notes" / "out.txt").read_text() == "written by workflow"
    assert "written by workflow" in result.outputs["read"]


async def test_mixed_llm_workflow(ws, home, scripted):
    scripted.push(
        ChatResponse(
            content="A summary of hello workflow world.",
            prompt_tokens=20,
            completion_tokens=8,
        )
    )
    runner = await runner_for(ws, home, scripted)
    path = await write_wf(ws, "mixed", MIXED_WF)
    result = await runner.run(path)
    assert result.ok
    assert result.outputs["draft"] == "A summary of hello workflow world."
    assert (ws / "final.txt").read_text() == "A summary of hello workflow world."


async def test_workflow_failure_checkpoint_and_resume(ws, home, scripted):
    runner = await runner_for(ws, home, scripted)
    path = await write_wf(ws, "failing", FAILING_WF)
    result = await runner.run(path)
    assert result.ok is False
    assert result.failed_step.id == "boom"
    assert result.checkpoint is not None and result.checkpoint.exists()

    resume_wf = FAILING_WF.replace("../outside.md", "seed.txt")
    path2 = await write_wf(ws, "failing", resume_wf)
    (ws / "seed.txt").write_text("now it exists")
    result2 = await runner.run(path2, resume=True)
    assert result2.resumed is True
    assert result2.ok is True


async def test_workflow_dry_run(ws, home, scripted):
    runner = await runner_for(ws, home, scripted)
    path = await write_wf(ws, "pure-tools", TOOL_ONLY_WF)
    result = await runner.run(path, {"target": "dry.txt"}, dry_run=True)
    assert result.ok and result.dry_run
    assert not (ws / "dry.txt").exists()
    assert "dry.txt" in result.outputs["write"]


async def test_workflow_missing_required_input(ws, home, scripted):
    runner = await runner_for(ws, home, scripted)
    path = await write_wf(
        ws,
        "req",
        """
name: req
inputs:
  must:
steps:
  - id: s
    tool: fs_list
""",
    )
    with pytest.raises(WorkflowError, match="must"):
        await runner.run(path)


async def test_workflow_step_on_error_continue(ws, home, scripted):
    runner = await runner_for(ws, home, scripted)
    path = await write_wf(
        ws,
        "cont",
        """
name: cont
steps:
  - id: bad
    tool: fs_read
    args:
      path: "../outside2.md"
    on_error: continue
  - id: good
    tool: fs_write
    args:
      path: "after.txt"
      content: "still ran"
""",
    )
    result = await runner.run(path)
    assert result.ok
    assert result.steps[0].ok is False
    assert (ws / "after.txt").read_text() == "still ran"


def test_substitute_dotpaths():
    scope = {
        "inputs.name": "world",
        "steps.gen.output": "GENERATED",
        "env": {"HOME": "/home/x"},
    }
    assert substitute("hi {{inputs.name}}", scope) == "hi world"
    assert substitute("{{steps.gen.output}}", scope) == "GENERATED"
    assert substitute("home={{env.HOME}}", scope) == "home=/home/x"
    assert substitute("{{unknown.ref}}", scope) == "{{unknown.ref}}"
    assert substitute({"a": ["{{inputs.name}}", 1]}, scope) == {"a": ["world", 1]}


def test_load_workflow_validates(ws):
    path = ws / "dupes.yaml"
    path.write_text(
        "name: d\nsteps:\n  - id: a\n    tool: fs_list\n  - id: a\n    tool: fs_read\n"
    )
    with pytest.raises(WorkflowError, match="duplicate"):
        load_workflow(path)
    empty = ws / "empty.yaml"
    empty.write_text("name: e\nsteps: []\n")
    with pytest.raises(WorkflowError, match="no steps"):
        load_workflow(empty)
    missing = ws / "nope.yaml"
    with pytest.raises(WorkflowError, match="not found"):
        load_workflow(missing)
