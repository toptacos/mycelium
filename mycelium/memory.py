from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

KIND_FACT = "fact"
KIND_PREFERENCE = "preference"
KIND_SUMMARY = "summary"
KIND_NOTE = "note"
VALID_KINDS = (KIND_FACT, KIND_PREFERENCE, KIND_SUMMARY, KIND_NOTE)


@dataclass
class MemoryEntry:
    id: str
    ts: float
    kind: str
    text: str
    tags: list[str] = field(default_factory=list)
    source: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "MemoryEntry":
        return MemoryEntry(
            id=d.get("id", ""),
            ts=float(d.get("ts", 0.0)),
            kind=d.get("kind", KIND_NOTE),
            text=d.get("text", ""),
            tags=list(d.get("tags", [])),
            source=d.get("source", ""),
        )


def _tokenize(text: str) -> set[str]:
    return {
        w
        for w in "".join(c.lower() if c.isalnum() else " " for c in text).split()
        if len(w) > 2
    }


class MemoryStore:
    """Append-only JSONL memory with keyword-overlap recall. Project scope + optional global scope."""

    def __init__(self, path: str | Path, extra_paths: list[Path] | None = None) -> None:
        self.path = Path(path)
        self.extra_paths = [Path(p) for p in (extra_paths or [])]
        self.entries: list[MemoryEntry] = []
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._load(self.path)
        for p in self.extra_paths:
            self._load(p)

    def _load(self, path: Path) -> None:
        if not path.exists():
            return
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    self.entries.append(MemoryEntry.from_dict(json.loads(line)))
                except json.JSONDecodeError:
                    continue

    def add(
        self,
        text: str,
        *,
        kind: str = KIND_NOTE,
        tags: list[str] | None = None,
        source: str = "",
    ) -> MemoryEntry:
        if kind not in VALID_KINDS:
            raise ValueError(f"kind must be one of {VALID_KINDS}")
        entry = MemoryEntry(
            id=uuid.uuid4().hex[:12],
            ts=time.time(),
            kind=kind,
            text=text.strip(),
            tags=sorted(set(tags or [])),
            source=source,
        )
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry.to_dict()) + "\n")
        self.entries.append(entry)
        return entry

    def learn_fact(
        self, text: str, *, tags: list[str] | None = None, source: str = ""
    ) -> MemoryEntry:
        return self.add(text, kind=KIND_FACT, tags=tags, source=source)

    def learn_preference(
        self, text: str, *, tags: list[str] | None = None, source: str = ""
    ) -> MemoryEntry:
        return self.add(text, kind=KIND_PREFERENCE, tags=tags, source=source)

    def recall(
        self, query: str, k: int = 5, kinds: tuple[str, ...] | None = None
    ) -> list[MemoryEntry]:
        q_tokens = _tokenize(query)
        if not q_tokens:
            return []
        scored: list[tuple[float, MemoryEntry]] = []
        now = time.time()
        for e in self.entries:
            if kinds and e.kind not in kinds:
                continue
            text_tokens = _tokenize(e.text)
            tag_tokens = _tokenize(" ".join(e.tags))
            overlap = len(q_tokens & text_tokens) / len(q_tokens)
            tag_overlap = len(q_tokens & tag_tokens) / len(q_tokens)
            score = overlap + 0.5 * tag_overlap
            if score <= 0:
                continue
            age_days = max(0.0, (now - e.ts) / 86400.0)
            score += max(0.0, 0.1 - age_days * 0.001)
            scored.append((score, e))
        scored.sort(key=lambda pair: (-pair[0], -pair[1].ts))
        return [e for _, e in scored[:k]]

    def recall_text(self, query: str, k: int = 5) -> str:
        hits = self.recall(query, k=k)
        if not hits:
            return ""
        lines = ["Recalled from memory:"]
        lines += [f"- ({e.kind}) {e.text}" for e in hits]
        return "\n".join(lines)

    def count(self) -> int:
        return len(self.entries)

    def recent(self, n: int = 10) -> list[MemoryEntry]:
        return sorted(self.entries, key=lambda e: -e.ts)[:n]

    def forget(self, entry_id: str) -> bool:
        before = len(self.entries)
        self.entries = [e for e in self.entries if e.id != entry_id]
        if len(self.entries) == before:
            return False
        with self.path.open("w", encoding="utf-8") as fh:
            for e in self.entries:
                fh.write(json.dumps(e.to_dict()) + "\n")
        return True
