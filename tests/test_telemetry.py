import json
from pathlib import Path

from mycelium.telemetry import EventLog, analyze_session


def make_log(tmp_path: Path) -> EventLog:
    return EventLog(tmp_path / "session.jsonl", session_id="s_test")


def test_emit_appends_jsonl(tmp_path: Path):
    log = make_log(tmp_path)
    log.emit("agent_start", task="hi")
    log.emit_llm(
        model="local:qwen",
        backend="local",
        prompt_tokens=100,
        completion_tokens=20,
        latency_ms=1200.5,
        tool_calls=1,
    )
    log.emit_tool(name="fs_list", ok=True, latency_ms=3.0, result_chars=42)
    lines = (tmp_path / "session.jsonl").read_text().strip().splitlines()
    assert len(lines) == 3
    records = [json.loads(line) for line in lines]
    assert records[0]["event"] == "agent_start"
    assert records[1]["prompt_tokens"] == 100
    assert records[1]["latency_ms"] == 1200.5
    assert records[2]["tool"] == "fs_list"


def test_verbose_prints_to_console(tmp_path: Path, capsys):
    log = EventLog(tmp_path / "session.jsonl", verbose=True)
    log.emit("agent_start", task="hello")
    captured = capsys.readouterr()
    assert "agent_start" in captured.out


def test_analysis_totals(tmp_path: Path):
    log = make_log(tmp_path)
    for i in range(3):
        log.emit_llm(
            model="local:m",
            backend="local",
            prompt_tokens=100,
            completion_tokens=10,
            latency_ms=100 * (i + 1),
        )
    log.emit_tool(name="fs_list", ok=True, latency_ms=1)
    log.emit_tool(name="fs_read", ok=False, latency_ms=1, error="boom")
    log.emit(
        "compaction",
        turns_dropped=5,
        tokens_before=1000,
        tokens_after=300,
        reclaimed=700,
    )
    log.emit("agent_step", step=1)

    analysis = analyze_session(tmp_path / "session.jsonl")
    assert analysis.events == 7
    assert analysis.llm_calls == 3
    assert analysis.prompt_tokens == 300
    assert analysis.completion_tokens == 30
    assert analysis.tool_calls == 2
    assert analysis.tool_errors == 1
    assert analysis.compactions == 1
    assert analysis.tokens_reclaimed == 700
    assert analysis.steps == 1
    assert analysis.errors == 1
    assert len(analysis.latencies_ms) == 3
    summary = "\n".join(analysis.summary_lines())
    assert "llm calls      : 3" in summary
    assert "compactions    : 1 (700 tokens reclaimed)" in summary
    assert "errors         : 1" in summary


def test_analysis_empty_file(tmp_path: Path):
    path = tmp_path / "empty.jsonl"
    path.write_text("")
    analysis = analyze_session(path)
    assert analysis.events == 0
    assert analysis.llm_calls == 0


def test_analysis_skips_corrupt_lines(tmp_path: Path):
    path = tmp_path / "corrupt.jsonl"
    path.write_text(
        '{"event": "agent_step", "step": 1}\nnot json\n{"event": "agent_step", "step": 2}\n'
    )
    analysis = analyze_session(path)
    assert analysis.events == 2
    assert analysis.steps == 2


def test_session_ids_unique(tmp_path: Path):
    a = EventLog(tmp_path / "a.jsonl")
    b = EventLog(tmp_path / "b.jsonl")
    assert a.session_id != b.session_id
    assert a.session_id.startswith("s_")
