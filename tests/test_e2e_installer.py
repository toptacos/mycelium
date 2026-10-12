import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def local_origin(tmp_path: Path) -> Path:
    origin = tmp_path / "origin.git"
    origin.mkdir()

    def git(*args: str) -> None:
        subprocess.run(["git", *args], check=True, capture_output=True, cwd=str(origin))

    git("init", "--bare", "--initial-branch=main")
    work = tmp_path / "seed"
    work.mkdir()
    subprocess.run(
        ["git", "init", "--initial-branch=main"],
        check=True,
        capture_output=True,
        cwd=str(work),
    )
    for rel in ("pyproject.toml", "README.md"):
        (work / rel).write_text(f"# {rel}\n")
    pkg = work / "mycelium"
    pkg.mkdir()
    (pkg / "__init__.py").write_text('__version__ = "0.1.0"\n')
    (pkg / "cli.py").write_text(
        "import sys\n\n\ndef main() -> int:\n    if '--version' in sys.argv:\n"
        "        from mycelium import __version__\n\n        print(__version__)\n"
        "        return 0\n    print('shim ok')\n    return 0\n\n\n"
        "if __name__ == '__main__':\n    raise SystemExit(main())\n"
    )
    (work / "pyproject.toml").write_text(
        '[project]\nname = "mycelium"\nversion = "0.1.0"\nrequires-python = ">=3.11"\n\n'
        '[project.scripts]\nmcy-test = "mycelium.cli:main"\n\n'
        '[build-system]\nrequires = ["hatchling"]\nbuild-backend = "hatchling.build"\n\n'
        '[tool.hatch.build.targets.wheel]\npackages = ["mycelium"]\n'
    )
    subprocess.run(["git", "add", "-A"], check=True, capture_output=True, cwd=str(work))
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=ci",
            "-c",
            "user.email=ci@example.com",
            "commit",
            "-m",
            "seed",
        ],
        check=True,
        capture_output=True,
        cwd=str(work),
    )
    subprocess.run(
        ["git", "remote", "add", "origin", str(origin)],
        check=True,
        capture_output=True,
        cwd=str(work),
    )
    subprocess.run(
        ["git", "push", "origin", "main"],
        check=True,
        capture_output=True,
        cwd=str(work),
    )
    return origin


def run_installer(
    origin: Path, tmp_path: Path, *args: str
) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.update(
        {
            "MCY_REPO": str(origin),
            "MCY_REF": "main",
            "MCY_DIR": str(tmp_path / "src"),
            "MCY_BIN": str(tmp_path / "bin"),
            "MCY_NO_DOCTOR": "1",
        }
    )
    return subprocess.run(
        ["bash", str(REPO_ROOT / "install.sh"), *args],
        capture_output=True,
        text=True,
        timeout=600,
        env=env,
    )


def test_installer_clones_syncs_and_installs_shim(local_origin: Path, tmp_path: Path):
    result = run_installer(local_origin, tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "installing uv" not in result.stdout  # uv already present on CI
    shim = tmp_path / "bin" / "mcy"
    assert shim.exists()
    assert os.access(shim, os.X_OK)
    shim_text = shim.read_text()
    assert str(tmp_path / "src") in shim_text
    assert (tmp_path / "src" / "pyproject.toml").exists()


def test_installer_shim_runs_the_tool(local_origin: Path, tmp_path: Path):
    run_installer(local_origin, tmp_path)
    shim = tmp_path / "bin" / "mcy"
    version = subprocess.run(
        [str(shim), "--version"],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=str(tmp_path),
    )
    assert version.returncode == 0, version.stderr
    assert "0.1.0" in version.stdout
    hello = subprocess.run(
        [str(shim)], capture_output=True, text=True, timeout=120, cwd=str(tmp_path)
    )
    assert "shim ok" in hello.stdout


def test_installer_updates_existing_checkout(local_origin: Path, tmp_path: Path):
    run_installer(local_origin, tmp_path)
    result = run_installer(local_origin, tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "updating" in result.stdout


def test_installer_rejects_unknown_flags(local_origin: Path, tmp_path: Path):
    result = run_installer(local_origin, tmp_path, "--frobnicate")
    assert result.returncode == 2
    assert "unknown flag" in result.stderr
