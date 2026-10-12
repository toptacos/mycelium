import pytest

from mycelium.context import (
    ContextManager,
    CompactionPlan,
    estimate_messages_tokens,
    estimate_tokens,
    extractive_fallback_summary,
)


def test_estimate_tokens():
    assert estimate_tokens("") == 0
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("a" * 400) == 100
    assert estimate_tokens("abcde") == 2


def test_estimate_messages_tokens():
    msgs = [
        {"role": "user", "content": "a" * 40},
        {"role": "assistant", "content": "b" * 20},
    ]
    assert estimate_messages_tokens(msgs) == 23


def test_usage_and_headroom():
    ctx = ContextManager(window_tokens=1000, reserve_tokens=200, compact_threshold=0.8)
    assert ctx.budget_tokens == 800
    ctx.set_system("x" * 400)
    assert ctx.system_tokens == 100
    ctx.add("user", "y" * 400)
    assert ctx.used_tokens == 204
    assert ctx.headroom == 596
    assert ctx.usage_ratio == pytest.approx(0.255)


def test_compaction_trigger_and_event():
    ctx = ContextManager(
        window_tokens=400, reserve_tokens=50, compact_threshold=0.5, keep_recent=2
    )
    ctx.add("user", "u" * 120, pinned=True)
    for i in range(8):
        ctx.add("user", f"message {i} " + "z" * 200)
    assert ctx.needs_compaction()
    plan = ctx.plan_compaction()
    assert isinstance(plan, CompactionPlan)
    assert len(plan.drop_turns) >= 1
    before = ctx.used_tokens
    event = ctx.apply("summary", plan)
    assert event.turns_dropped == len(plan.drop_turns)
    assert ctx.used_tokens < before
    assert event.reclaimed == before - ctx.used_tokens
    assert ctx.compaction_events[0].turns_dropped == len(plan.drop_turns)
    assert not ctx.needs_compaction()


def test_compaction_keeps_pinned_and_recent():
    ctx = ContextManager(window_tokens=2000, reserve_tokens=100, keep_recent=3)
    first = ctx.add("user", "original task", pinned=True)
    for i in range(10):
        ctx.add("user", f"filler {i} " + "z" * 300)
    plan = ctx.plan_compaction()
    dropped = {t.content for t in plan.drop_turns}
    assert "original task" not in dropped
    ctx.apply("summary here", plan)
    contents = [t.content for t in ctx.turns]
    assert any(c == "original task" for c in contents)
    assert any("summary here" in c for c in contents)
    assert contents[-1].startswith("filler 9")


def test_compaction_plan_none_when_few_turns():
    ctx = ContextManager(keep_recent=5)
    for i in range(3):
        ctx.add("user", f"m{i}")
    assert ctx.plan_compaction() is None


def test_extractive_fallback_summary():
    from mycelium.context import Turn

    turns = [
        Turn(role="user", content="Do the thing. Then more."),
        Turn(role="tool", content="", name="fs_list"),
        Turn(role="assistant", content="Done it all."),
    ]
    summary = extractive_fallback_summary(turns)
    assert "user: Do the thing" in summary
    assert "no content" in summary
    assert "assistant: Done it all" in summary


def test_invalid_threshold():
    with pytest.raises(ValueError):
        ContextManager(compact_threshold=1.5)


def test_messages_roundtrip():
    ctx = ContextManager()
    ctx.add("user", "hello")
    ctx.add(
        "assistant",
        "hi",
        tool_calls=[
            {
                "id": "1",
                "type": "function",
                "function": {"name": "fs_list", "arguments": "{}"},
            }
        ],
    )
    ctx.add("tool", "result", tool_call_id="1", name="fs_list")
    msgs = ctx.messages()
    assert msgs[0]["role"] == "user"
    assert msgs[1]["tool_calls"][0]["function"]["name"] == "fs_list"
    assert msgs[2]["tool_call_id"] == "1"
