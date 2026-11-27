from pathlib import Path

from mycelium.cli import main
from mycelium.examples_lib import canonical_id, example_dir, list_examples

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "04-kraken-compose"


def test_example_list_includes_kraken_compose(capsys):
    rc = main(["example", "list"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "04-kraken-compose" in out
    assert "01-explore" in out
    ids = {item["id"] for item in list_examples()}
    assert "04-kraken-compose" in ids


def test_example_show(capsys):
    rc = main(["example", "show", "kraken-compose"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "plan-only" in out.lower() or "Kraken" in out
    assert "dry-run" in out


def test_example_copy_alias(tmp_path, capsys):
    dest = tmp_path / "reef"
    rc = main(["example", "copy", "kraken-compose", str(dest)])
    assert rc == 0
    out = capsys.readouterr().out
    assert str(dest) in out
    assert (dest / "run.sh").exists()
    assert (dest / "compose.yaml").exists()
    assert (dest / "workflows" / "shift.yaml").exists()
    rc2 = main(["example", "copy", "04-kraken-compose", str(dest)])
    assert rc2 == 2


def test_example_unknown(capsys):
    rc = main(["example", "show", "nope"])
    assert rc == 2


def test_canonical_alias():
    assert canonical_id("kraken-compose") == "04-kraken-compose"
    assert example_dir("kraken-compose") == EXAMPLE


def test_shift_does_not_start_docker():
    shift = (EXAMPLE / "workflows" / "shift.yaml").read_text(encoding="utf-8")
    compose = (EXAMPLE / "compose.yaml").read_text(encoding="utf-8")
    config = (EXAMPLE / ".kraken" / "config.yaml").read_text(encoding="utf-8")
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert 'command: "kraken up --file compose.yaml"' in shift
    assert 'command: "kraken up --file compose.yaml --start"' not in shift
    assert "docker compose up" not in shift
    assert "127.0.0.1:" in compose
    assert "public: false" in config
    assert "examples/04-kraken-compose/run.sh dry-run" in agents
    assert "docker compose up" in agents


def test_shift_dry_run(ws, home, capsys):
    for name in ("shift.yaml", "kraken-stack.yaml"):
        src = EXAMPLE / "workflows" / name
        dest = ws / "workflows" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(src.read_text(encoding="utf-8"))
    rc = main(
        [
            "--workspace",
            str(ws),
            "--home",
            str(home),
            "workflow",
            "run",
            "shift",
            "--dry-run",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "workflow shift: ok" in out
    assert "compose-plan" in out
    assert not (ws / "ENVIRONMENT.md").exists()
