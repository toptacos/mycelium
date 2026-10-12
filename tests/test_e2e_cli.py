import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.e2e

REPO_ROOT = Path(__file__).resolve().parents[1]


def run_cli(
    ws: Path,
    home: Path,
    *args: str,
    timeout: float = 120,
    env_extra: dict | None = None,
) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["MYCELIUM_HOME"] = str(home)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-m", "mycelium.cli", "--workspace", str(ws), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(REPO_ROOT),
        env=env,
    )


@pytest.fixture
def ws_workflows(ws: Path) -> Path:
    wf = ws / "workflows"
    wf.mkdir(exist_ok=True)
    (wf / "demo.yaml").write_text(
        'name: demo\ndescription: list the workspace\nsteps:\n  - id: list\n    tool: fs_list\n    args:\n      path: "."\n'
    )
    return ws


def test_doctor_exit_codes(ws: Path, home: Path):
    result = run_cli(ws, home, "doctor")
    assert result.returncode in (0, 1)
    assert "python" in result.stdout
    assert "backend:local" in result.stdout


def test_models_and_prompts(ws: Path, home: Path):
    models = run_cli(ws, home, "models")
    assert models.returncode == 0
    assert "openrouter" in models.stdout
    prompts = run_cli(ws, home, "prompts", "list")
    assert prompts.returncode == 0
    assert "scaffold-app" in prompts.stdout
    shown = run_cli(ws, home, "prompts", "show", "workflow")
    assert shown.returncode == 0
    assert "run_workflow" in shown.stdout


def test_run_json_end_to_end(ws: Path, home: Path, tmp_path: Path):
    script = tmp_path / "script.json"
    script.write_text(
        json.dumps(
            [
                {
                    "content": "",
                    "tool_calls": [
                        {"id": "c1", "name": "fs_list", "arguments": {"path": "."}}
                    ],
                },
                {"content": "the workspace is empty"},
            ]
        )
    )
    result = run_cli(
        ws, home, "run", "what is in here?", "--scripted", str(script), "--json"
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["tools_used"] == ["fs_list"]
    assert payload["ok"] is True
    session_log = ws / ".mycelium" / "logs" / "session.jsonl"
    assert session_log.exists()
    events = [json.loads(line) for line in session_log.read_text().splitlines()]
    assert any(e["event"] == "agent_finish" for e in events)
    assert any(e["event"] == "tool_call" and e["tool"] == "fs_list" for e in events)


def test_report_after_run(ws: Path, home: Path, tmp_path: Path):
    script = tmp_path / "s.json"
    script.write_text(json.dumps([{"content": "done"}]))
    run_cli(ws, home, "run", "say done", "--scripted", str(script))
    report = run_cli(ws, home, "report")
    assert report.returncode == 0
    assert "llm calls" in report.stdout
    assert "errors" in report.stdout
    report_json = run_cli(ws, home, "report", "--json")
    payload = json.loads(report_json.stdout)
    assert payload["llm_calls"] >= 1


def test_learn_then_recall_then_forget(ws: Path, home: Path):
    learned = run_cli(
        ws,
        home,
        "learn",
        "the build server is called forge",
        "--kind",
        "fact",
        "--tags",
        "ci",
    )
    assert learned.returncode == 0
    assert "learned" in learned.stdout
    recall = run_cli(ws, home, "memory", "recall", "what is the build server")
    assert "forge" in recall.stdout
    show = run_cli(ws, home, "memory", "recent")
    assert show.returncode == 0


def test_workflow_lifecycle_e2e(ws_workflows: Path, home: Path):
    ws = ws_workflows
    listed = run_cli(ws, home, "workflow", "list")
    assert "demo" in listed.stdout
    validated = run_cli(ws, home, "workflow", "validate", "demo")
    assert validated.returncode == 0
    dry = run_cli(ws, home, "workflow", "run", "demo", "--dry-run")
    assert dry.returncode == 0
    assert not (ws / "listed.txt").exists()
    real = run_cli(ws, home, "workflow", "run", "demo")
    assert real.returncode == 0
    assert "[ok] list" in real.stdout


def test_workflow_resume_e2e(ws: Path, home: Path):
    wf = ws / "workflows"
    wf.mkdir(exist_ok=True)
    (wf / "resumable.yaml").write_text(
        "name: resumable\nsteps:\n  - id: a\n    tool: fs_write\n    args:\n      path: a.txt\n      content: A\n  - id: b\n    tool: definitely_not_a_tool\n"
    )
    first = run_cli(ws, home, "workflow", "run", "resumable")
    assert first.returncode == 3
    assert "checkpoint" in first.stdout
    (wf / "resumable.yaml").write_text(
        "name: resumable\nsteps:\n  - id: a\n    tool: fs_write\n    args:\n      path: a.txt\n      content: A\n  - id: b\n    tool: fs_read\n    args:\n      path: a.txt\n"
    )
    second = run_cli(ws, home, "workflow", "run", "resumable", "--resume")
    assert second.returncode == 0
    assert (ws / "a.txt").read_text() == "A"


def test_read_only_run_blocks_mutation(ws: Path, home: Path, tmp_path: Path):
    script = tmp_path / "s.json"
    script.write_text(
        json.dumps(
            [
                {
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "c1",
                            "name": "fs_write",
                            "arguments": {"path": "x.txt", "content": "nope"},
                        }
                    ],
                },
                {"content": "cannot write in read-only mode"},
            ]
        )
    )
    env_extra = {"MYCELIUM_READ_ONLY": "1"}
    result = run_cli(
        ws, home, "run", "write x.txt", "--scripted", str(script), env_extra=env_extra
    )
    assert not (ws / "x.txt").exists()
    assert result.returncode in (0, 2)
