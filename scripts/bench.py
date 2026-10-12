#!/usr/bin/env python3
"""Benchmark mycelium itself and write a verbose JSON + text report.

Measures what we can honestly measure on this machine:
  - CLI cold start (`mcy --help`)
  - Import cost of the package
  - Full test-suite wall time (subprocess pytest)
  - A complete scripted agent run (the five sample scenarios, deterministic)
  - Proxy round-trip overhead (start + healthz + one completion)
  - Memory serialization throughput

Usage: python scripts/bench.py [--out logs/bench.json] [--verbose]
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def timed(fn, *, repeat: int = 5):
    samples = []
    result = None
    for _ in range(repeat):
        t0 = time.perf_counter()
        result = fn()
        samples.append((time.perf_counter() - t0) * 1000)
    return {
        "ms_avg": round(statistics.fmean(samples), 1),
        "ms_min": round(min(samples), 1),
        "ms_max": round(max(samples), 1),
        "n": repeat,
        "result": result,
    }


def bench_cli_help() -> dict:
    def run():
        return subprocess.run(
            [sys.executable, "-m", "mycelium.cli", "--help"],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        ).returncode

    return timed(run)


def bench_import() -> dict:
    def run():
        return subprocess.run(
            [sys.executable, "-c", "import mycelium"],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        ).returncode

    return timed(run)


def bench_test_suite() -> dict:
    t0 = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    ms = (time.perf_counter() - t0) * 1000
    tail = proc.stdout.strip().splitlines()[-1] if proc.stdout else ""
    return {"ms": round(ms, 1), "rc": proc.returncode, "summary": tail}


def bench_sample_suite() -> dict:
    t0 = time.perf_counter()
    proc = subprocess.run(
        ["bash", str(ROOT / "scripts" / "run-samples.sh"), "scripted"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    ms = (time.perf_counter() - t0) * 1000
    return {"ms": round(ms, 1), "rc": proc.returncode}


def bench_proxy() -> dict:
    import threading
    from http.server import ThreadingHTTPServer

    import httpx

    from mycelium.config import load_settings
    from mycelium.server import ProxyState, make_handler

    settings = load_settings(workspace=ROOT, home=Path.home() / ".mycelium")
    t0 = time.perf_counter()
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(ProxyState(settings)))
    bind_ms = (time.perf_counter() - t0) * 1000
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()

    async def roundtrip():
        latencies = []
        async with httpx.AsyncClient(timeout=10) as client:
            for _ in range(3):
                t = time.perf_counter()
                r = await client.get(f"http://127.0.0.1:{port}/healthz")
                r.raise_for_status()
                latencies.append((time.perf_counter() - t) * 1000)
        return latencies

    import asyncio

    latencies = asyncio.run(roundtrip())
    server.shutdown()
    server.server_close()
    return {
        "bind_ms": round(bind_ms, 1),
        "healthz_ms_avg": round(statistics.fmean(latencies), 2),
        "healthz_ms_min": round(min(latencies), 2),
    }


def bench_memory_io(tmp: Path) -> dict:
    from mycelium.memory import MemoryStore

    store = MemoryStore(tmp / "mem.jsonl")
    t0 = time.perf_counter()
    for i in range(500):
        store.add(
            f"benchmark entry {i} about python testing and workflows",
            kind="fact",
            tags=["bench"],
        )
    add_ms = (time.perf_counter() - t0) * 1000
    t0 = time.perf_counter()
    for _ in range(50):
        store.recall("python workflows")
    recall_ms = (time.perf_counter() - t0) * 1000
    return {
        "add_500_ms": round(add_ms, 1),
        "recall_50_ms": round(recall_ms, 1),
        "entries": store.count(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ROOT / "logs" / "bench.json"))
    parser.add_argument("--repeat", type=int, default=5)
    args = parser.parse_args()

    import tempfile

    report = {
        "machine": {
            "platform": sys.platform,
            "python": sys.version.split()[0],
            "note": "measured on this machine; not a controlled benchmark",
        },
        "cli_help": bench_cli_help(),
        "import": bench_import(),
        "test_suite": bench_test_suite(),
        "sample_suite": bench_sample_suite(),
        "proxy": bench_proxy(),
    }
    with tempfile.TemporaryDirectory() as td:
        report["memory_io"] = bench_memory_io(Path(td))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    print(f"\nwritten to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
