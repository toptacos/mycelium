#!/usr/bin/env python3
"""Validate conventional-commit formatting for a commit range.

Usage: python scripts/check-commits.py <base>..<head>   (or a list of SHAs)
Exits 1 with a readable message on the first invalid subject line.
"""

from __future__ import annotations

import re
import subprocess
import sys

TYPES = {
    "feat",
    "fix",
    "perf",
    "refactor",
    "docs",
    "test",
    "build",
    "ci",
    "chore",
    "revert",
    "style",
}
SUBJECT_RE = re.compile(
    r"^(?P<type>[a-z]+)(?P<scope>\([a-z0-9_.,-]+\))?(?P<bang>!)?: .{1,72}$"
)


def commits(spec: str) -> list[str]:
    out = subprocess.run(
        ["git", "log", "--format=%s", spec], capture_output=True, text=True
    )
    if out.returncode != 0:
        if not spec:
            return []
        print(out.stderr.strip())
        sys.exit(2)
    return [line.strip() for line in out.stdout.splitlines() if line.strip()]


def main() -> int:
    spec = sys.argv[1] if len(sys.argv) > 1 else "HEAD~10..HEAD"
    subjects = commits(spec)
    if not subjects:
        print(f"check-commits: no commits in {spec!r}")
        return 0
    bad = []
    for subject in subjects:
        if subject.startswith("Merge ") or subject.startswith('Revert "'):
            continue
        m = SUBJECT_RE.match(subject)
        if not m or m.group("type") not in TYPES:
            bad.append(subject)
    if bad:
        print("check-commits: these subjects are not conventional commits:")
        for b in bad:
            print(f"  - {b}")
        print("\nexpected: <type>(<scope>): <subject>  where type is one of:")
        print("  " + ", ".join(sorted(TYPES)))
        return 1
    print(f"check-commits: {len(subjects)} commits ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
