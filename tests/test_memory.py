import time

import pytest

from mycelium.memory import KIND_FACT, KIND_PREFERENCE, KIND_SUMMARY, MemoryStore


@pytest.fixture
def memory(tmp_path):
    return MemoryStore(tmp_path / "memory.jsonl")


def test_add_persists_and_counts(memory, tmp_path):
    entry = memory.add(
        "use uv for python projects", kind=KIND_FACT, tags=["python", "tooling"]
    )
    assert memory.count() == 1
    reloaded = MemoryStore(tmp_path / "memory.jsonl")
    assert reloaded.count() == 1
    assert reloaded.entries[0].text == "use uv for python projects"
    assert reloaded.entries[0].tags == ["python", "tooling"]


def test_recall_ranks_by_overlap(memory):
    memory.add("the project uses python 3.13 and uv", kind=KIND_FACT)
    memory.add("docker compose runs the database", kind=KIND_FACT)
    memory.add("python testing uses pytest with asyncio", kind=KIND_FACT)
    hits = memory.recall("python testing")
    assert hits
    assert any("pytest" in h.text for h in hits)


def test_recall_respects_kind_filter(memory):
    memory.add("prefers terse output", kind=KIND_PREFERENCE)
    memory.add("deploys on fridays", kind=KIND_FACT)
    hits = memory.recall("deploys on fridays", kinds=(KIND_FACT,))
    assert len(hits) == 1
    assert "fridays" in hits[0].text


def test_recall_tag_bonus(memory):
    memory.add("colour scheme is dark", kind=KIND_PREFERENCE, tags=["ui", "theme"])
    memory.add("no relevant text here", kind=KIND_FACT)
    hits = memory.recall("theme")
    assert hits[0].text == "colour scheme is dark"


def test_recall_empty_query(memory):
    memory.add("something", kind=KIND_FACT)
    assert memory.recall("the of a") == []


def test_invalid_kind_rejected(memory):
    with pytest.raises(ValueError):
        memory.add("x", kind="bogus")


def test_forget(memory, tmp_path):
    e1 = memory.add("keep me")
    e2 = memory.add("delete me")
    assert memory.forget(e2.id) is True
    assert memory.forget("nonexistent") is False
    assert [e.text for e in memory.entries] == ["keep me"]


def test_extra_paths_merged(tmp_path):
    global_store = tmp_path / "global.jsonl"
    project_store = tmp_path / "project.jsonl"
    g = MemoryStore(global_store)
    g.add("global fact about python", kind=KIND_FACT)
    p = MemoryStore(project_store, extra_paths=[global_store])
    hits = p.recall("python global")
    assert any(h.text == "global fact about python" for h in hits)
    assert p.count() == 1


def test_recall_text_format(memory):
    memory.add("model default is qwen2.5-coder", kind=KIND_FACT)
    text = memory.recall_text("model default", k=3)
    assert text.startswith("Recalled from memory:")
    assert "qwen2.5-coder" in text


def test_recent_ordering(memory):
    memory.add("first", kind=KIND_SUMMARY)
    time.sleep(0.01)
    memory.add("second", kind=KIND_SUMMARY)
    recent = memory.recent(1)
    assert recent[0].text == "second"
