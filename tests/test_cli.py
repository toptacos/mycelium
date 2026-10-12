import json
from pathlib import Path

import pytest

from mycelium.cli import main


def test_prompts_list(capsys):
    rc = main(["prompts", "list"])
    assert rc == 0
    out = capsys.readouterr().out
    for name in ("scaffold-app", "research", "content", "integration", "workflow"):
        assert name in out


def test_prompts_show(capsys):
    rc = main(["prompts", "show", "scaffold-app"])
    assert rc == 0
    assert "scaffold_app" in capsys.readouterr().out


def test_prompts_show_unknown(capsys):
    rc = main(["prompts", "show", "nope"])
    assert rc == 2


def test_doctor_reports_table(ws, home, capsys):
    rc = main(["--workspace", str(ws), "--home", str(home), "doctor"])
    assert rc in (0, 1)
    out = capsys.readouterr().out
    assert "python" in out
    assert "workspace" in out
    assert "backend:local" in out


def test_doctor_cloud_backends_skip_without_keys(ws, home, capsys, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    rc = main(["--workspace", str(ws), "--home", str(home), "doctor"])
    out = capsys.readouterr().out
    assert "not configured" in out
    assert "backend:local" in out


def test_learn_and_recall_roundtrip(ws, home, capsys):
    rc = main(
        [
            "--workspace",
            str(ws),
            "--home",
            str(home),
            "learn",
            "the deploy target is aws us-east-1",
            "--kind",
            "fact",
            "--tags",
            "deploy,aws",
        ]
    )
    assert rc == 0
    rc2 = main(
        [
            "--workspace",
            str(ws),
            "--home",
            str(home),
            "memory",
            "recall",
            "deploy target aws",
        ]
    )
    assert rc2 == 0
    out = capsys.readouterr().out
    assert "aws us-east-1" in out
    assert (ws / ".mycelium" / "memory.jsonl").exists()


def test_memory_show_empty(ws, home, capsys):
    rc = main(["--workspace", str(ws), "--home", str(home), "memory", "recent"])
    assert rc == 0
    assert "(empty)" in capsys.readouterr().out


def test_models_lists_backends(ws, home, capsys):
    rc = main(["--workspace", str(ws), "--home", str(home), "models"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "openrouter" in out
    assert "OPENROUTER_API_KEY" in out


def test_run_with_scripted_backend(ws, home, tmp_path, capsys):
    script = tmp_path / "script.json"
    script.write_text(
        json.dumps(
            [
                {"content": "done: listed workspace", "model": "test"},
            ]
        )
    )
    rc = main(
        [
            "--workspace",
            str(ws),
            "--home",
            str(home),
            "run",
            "list the workspace",
            "--scripted",
            str(script),
            "--json",
        ]
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert "done: listed workspace" in payload["content"]
    assert payload["ok"] is True
    assert payload["session"].startswith("s_")


def test_run_from_prompt_file(ws, home, tmp_path, capsys):
    prompt = tmp_path / "prompt.md"
    prompt.write_text("Say hello.")
    script = tmp_path / "s.json"
    script.write_text(json.dumps([{"content": "hello there"}]))
    rc = main(
        [
            "--workspace",
            str(ws),
            "--home",
            str(home),
            "run",
            f"@{prompt}",
            "--scripted",
            str(script),
        ]
    )
    assert rc == 0
    assert "hello there" in capsys.readouterr().out


def test_report_analyzes_session(ws, home, tmp_path, capsys):
    log = ws / ".mycelium" / "logs" / "session.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(
        "\n".join(
            [
                json.dumps({"event": "agent_step", "step": 1, "session": "s_x"}),
                json.dumps(
                    {
                        "event": "llm_call",
                        "model": "local:m",
                        "prompt_tokens": 10,
                        "completion_tokens": 4,
                        "latency_ms": 99.0,
                        "tool_calls": 1,
                        "session": "s_x",
                    }
                ),
                json.dumps(
                    {
                        "event": "tool_call",
                        "tool": "fs_list",
                        "ok": True,
                        "latency_ms": 1.0,
                        "session": "s_x",
                    }
                ),
                json.dumps(
                    {
                        "event": "compaction",
                        "turns_dropped": 2,
                        "tokens_before": 100,
                        "tokens_after": 40,
                        "reclaimed": 60,
                        "session": "s_x",
                    }
                ),
            ]
        )
        + "\n"
    )
    rc = main(["--workspace", str(ws), "--home", str(home), "report", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["llm_calls"] == 1
    assert payload["prompt_tokens"] == 10
    assert payload["tokens_reclaimed"] == 60
    assert payload["tools_by_name"] == {"fs_list": 1}


def test_workflow_list_and_run(ws, home, capsys):
    wf_dir = ws / "workflows"
    wf_dir.mkdir(exist_ok=True)
    (wf_dir / "demo.yaml").write_text(
        'name: demo\ndescription: list workspace\nsteps:\n  - id: list\n    tool: fs_list\n    args:\n      path: "."\n'
    )
    rc = main(["--workspace", str(ws), "--home", str(home), "workflow", "list"])
    assert rc == 0
    assert "demo" in capsys.readouterr().out
    rc2 = main(["--workspace", str(ws), "--home", str(home), "workflow", "run", "demo"])
    assert rc2 == 0
    rc3 = main(
        ["--workspace", str(ws), "--home", str(home), "workflow", "validate", "demo"]
    )
    assert rc3 == 0


def test_workflow_run_failing_exit_code(ws, home, capsys):
    wf_dir = ws / "workflows"
    wf_dir.mkdir(exist_ok=True)
    (wf_dir / "bad.yaml").write_text(
        'name: bad\nsteps:\n  - id: r\n    tool: definite_nonexistent_tool\n    args:\n      path: "missing.txt"\n'
    )
    rc = main(["--workspace", str(ws), "--home", str(home), "workflow", "run", "bad"])
    assert rc == 3


def test_workflow_bad_input_format(ws, home, capsys):
    wf_dir = ws / "workflows"
    wf_dir.mkdir(exist_ok=True)
    (wf_dir / "d.yaml").write_text("name: d\nsteps:\n  - id: s\n    tool: fs_list\n")
    rc = main(
        [
            "--workspace",
            str(ws),
            "--home",
            str(home),
            "workflow",
            "run",
            "d",
            "--input",
            "noequals",
        ]
    )
    assert rc == 2
