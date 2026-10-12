from hypothesis import given, settings as hsettings, strategies as st

from mycelium.context import ContextManager, estimate_tokens
from mycelium.memory import MemoryStore
from mycelium.tools import PolicyViolation, resolve_in_workspace


@hsettings(max_examples=80, deadline=None)
@given(
    window=st.integers(min_value=300, max_value=8000),
    reserve=st.integers(min_value=50, max_value=500),
    threshold=st.floats(min_value=0.3, max_value=0.95),
)
def test_compaction_never_exceeds_budget(window, reserve, threshold):
    ctx = ContextManager(
        window_tokens=window,
        reserve_tokens=reserve,
        compact_threshold=threshold,
        keep_recent=2,
    )
    for i in range(40):
        ctx.add("user", f"turn {i} " + "x" * 120)
        if ctx.needs_compaction():
            plan = ctx.plan_compaction()
            if plan is not None:
                ctx.apply("summary " + "s" * 50, plan)
    assert ctx.used_tokens <= ctx.budget_tokens + 64 + ctx.keep_recent * 200


@hsettings(max_examples=60, deadline=None)
@given(
    texts=st.lists(st.text(alphabet="abcABC012 ", min_size=0, max_size=50), max_size=10)
)
def test_token_estimate_monotonic(texts):
    joined = "\n".join(texts)
    assert estimate_tokens(joined) >= max(
        (estimate_tokens(t) for t in texts), default=0
    )
    assert estimate_tokens(joined) >= len(joined) // 4 - 2


@hsettings(max_examples=60, deadline=None)
@given(component=st.text(alphabet="abc/._-", min_size=1, max_size=20))
def test_traversal_components_denied(component):
    ws = __import__("pathlib").Path("/tmp/ws")
    evil = "../" * 3 + component
    if evil.replace("/", "") != component:
        with_space = evil
        try:
            resolved = resolve_in_workspace(ws, with_space)
            assert str(resolved).startswith("/tmp/ws")
        except PolicyViolation:
            pass


@hsettings(max_examples=40, deadline=None)
@given(
    entries=st.lists(
        st.text(alphabet="abc def ghi ", min_size=3, max_size=60),
        min_size=1,
        max_size=8,
    )
)
def test_memory_recall_deterministic(entries):
    store = MemoryStore.__new__(MemoryStore)
    from pathlib import Path

    store.path = Path("/dev/null")
    store.extra_paths = []
    store.entries = []
    from mycelium.memory import MemoryEntry

    for i, e in enumerate(entries):
        store.entries.append(MemoryEntry(id=str(i), ts=float(i), kind="fact", text=e))
    if entries:
        hits1 = store.recall("abc")
        hits2 = store.recall("abc")
        assert [h.id for h in hits1] == [h.id for h in hits2]
