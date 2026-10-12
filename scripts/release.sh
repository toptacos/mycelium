#!/usr/bin/env bash
# Release helper: check | tag <version> | notes
set -euo pipefail
cd "$(dirname "$0")/.."

cmd="${1:-check}"

case "$cmd" in
  check)
    echo "== tests =="
    uv run pytest -q
    echo "== changelog =="
    grep -q "## \[Unreleased\]" CHANGELOG.md && echo "unreleased section present"
    last_tag=$(git describe --tags --abbrev=0 2>/dev/null || echo "none")
    echo "last tag: $last_tag"
    if [ "$last_tag" != "none" ]; then
      python scripts/check-commits.py "$last_tag..HEAD"
    fi
    ;;
  tag)
    version="${2:?usage: scripts/release.sh tag 0.2.0}"
    echo "== tests =="
    uv run pytest -q
    python - "$version" <<'EOF'
import re, sys
from pathlib import Path
version = sys.argv[1]
if not re.fullmatch(r"\d+\.\d+\.\d+", version):
    sys.exit(f"invalid version {version!r}; expected X.Y.Z")
p = Path("mycelium/__init__.py")
s = p.read_text()
s2 = re.sub(r'__version__ = "[^"]+"', f'__version__ = "{version}"', s)
if s == s2:
    sys.exit("version string not found in mycelium/__init__.py")
p.write_text(s2)
print(f"version set to {version}")
EOF
    if ! grep -q "## \[$version\]" CHANGELOG.md; then
      date=$(date +%Y-%m-%d)
      python - "$version" "$date" <<'EOF'
import sys
from pathlib import Path
version, date = sys.argv[1], sys.argv[2]
p = Path("CHANGELOG.md")
s = p.read_text()
s = s.replace("## [Unreleased]", f"## [Unreleased]\n\n## [{version}] - {date}", 1)
if "[Unreleased]: " in s:
    s = s.replace("[Unreleased]: https://github.com/toptacos/mycelium/compare/v0.1.0...HEAD",
                  f"[Unreleased]: https://github.com/toptacos/mycelium/compare/v{version}...HEAD\n[{version}]: https://github.com/toptacos/mycelium/releases/tag/v{version}")
p.write_text(s)
print(f"changelog section added for {version}")
EOF
    fi
    git add -A
    git commit -m "chore(release): $version"
    git tag -a "v$version" -m "mycelium v$version"
    echo "tagged v$version - push with: git push origin main v$version"
    ;;
  notes)
    last_tag=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
    if [ -z "$last_tag" ]; then echo "no tags yet"; exit 1; fi
    git log --format="* %s (%h)" "$last_tag..HEAD"
    ;;
  *)
    echo "usage: scripts/release.sh [check|tag <version>|notes]"
    exit 2
    ;;
esac
