from __future__ import annotations

import shutil
from pathlib import Path

ALIASES = {
    "kraken-compose": "04-kraken-compose",
}

SKIP_DIR_NAMES = {"logs"}


def examples_root() -> Path | None:
    checkout = Path(__file__).resolve().parent.parent / "examples"
    if checkout.is_dir() and any(checkout.iterdir()):
        return checkout
    bundled = Path(__file__).resolve().parent / "data" / "examples"
    if bundled.is_dir():
        return bundled
    return None


def canonical_id(name: str) -> str:
    return ALIASES.get(name, name)


def list_examples() -> list[dict[str, str]]:
    root = examples_root()
    if root is None:
        return []
    items: list[dict[str, str]] = []
    for child in sorted(p for p in root.iterdir() if p.is_dir()):
        if child.name in SKIP_DIR_NAMES or child.name.startswith("."):
            continue
        if not (child / "run.sh").exists() and not (child / "README.md").exists():
            continue
        items.append({"id": child.name, "path": str(child)})
    return items


def example_dir(name: str) -> Path | None:
    root = examples_root()
    if root is None:
        return None
    path = root / canonical_id(name)
    return path if path.is_dir() else None


def copy_example(name: str, dest: Path) -> Path:
    src = example_dir(name)
    if src is None:
        raise FileNotFoundError(name)
    dest = dest.expanduser().resolve()
    if dest.exists():
        if dest.is_file() or any(dest.iterdir()):
            raise FileExistsError(str(dest))
    ignore = shutil.ignore_patterns(
        "example-home",
        "reef-home",
        ".mycelium",
        ".mycelium-home",
        "ENVIRONMENT.md",
        "BRIEF.md",
    )
    shutil.copytree(src, dest, dirs_exist_ok=dest.exists(), ignore=ignore)
    return dest
