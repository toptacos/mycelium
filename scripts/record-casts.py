#!/usr/bin/env python3
"""Record terminal sessions as asciinema v2 casts (.cast files).

Feeds a script of shell commands into a real pty, captures output with
timestamps, and writes an asciicast v2 file that any player can replay.

Completion detection uses a unique PS1 marker: bash prints the marker when it
is ready for the next command, so recordings capture full command output even
when a command thinks for minutes (a local LLM, for example).

Usage:
  python scripts/record-casts.py --name 01-doctor --title "mcy doctor" \
      --cmd "uv run mcy doctor" --cmd "uv run mcy models"
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import select
import struct
import subprocess
import sys
import termios
import time
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "site" / "casts"
MARKER = "__MCY_PROMPT_READY__"


def set_winsize(fd: int, width: int, height: int) -> None:
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", height, width, 0, 0))


def record_commands(
    commands: list[str],
    out_path: Path,
    *,
    title: str,
    width: int = 100,
    height: int = 28,
    max_wait: float = 900.0,
    cwd: Path | None = None,
) -> int:
    import pty

    master, slave = pty.openpty()
    set_winsize(slave, width, height)

    env = dict(os.environ)
    env.update(
        {
            "TERM": "xterm-256color",
            "PS1": MARKER,
            "PROMPT_COMMAND": "",
            "MYCELIUM_HOME": str(Path.home() / ".cast-mycelium-home"),
        }
    )
    proc = subprocess.Popen(
        ["bash", "--noprofile", "--norc", "-i"],
        stdin=slave,
        stdout=slave,
        stderr=slave,
        cwd=str(cwd or Path.cwd()),
        env=env,
        preexec_fn=lambda: os.setsid(),
    )
    os.close(slave)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    start = time.time()

    def read_until(done_predicate, timeout: float) -> bytes:
        data = b""
        deadline = time.time() + timeout
        while time.time() < deadline:
            ready, _, _ = select.select([master], [], [], 0.2)
            if not ready:
                if done_predicate(data.decode("utf-8", "replace")):
                    break
                continue
            try:
                chunk = os.read(master, 65536)
            except OSError:
                break
            if not chunk:
                break
            data += chunk
            if done_predicate(data.decode("utf-8", "replace")):
                break
        return data

    header = {
        "version": 2,
        "width": width,
        "height": height,
        "timestamp": int(start),
        "title": title,
        "env": {"TERM": "xterm-256color", "SHELL": "/bin/bash"},
    }

    def clean(text: str) -> str:
        return text.replace(MARKER, "$ ")

    with out_path.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps(header) + "\n")
        initial = read_until(lambda s: MARKER in s, 30.0)
        if initial:
            fh.write(
                json.dumps(
                    [
                        round(time.time() - start, 3),
                        "o",
                        clean(initial.decode("utf-8", "replace")),
                    ]
                )
                + "\n"
            )
        for command in commands:
            os.write(master, command.encode() + b"\n")
            # backgrounded commands return the prompt immediately; everything
            # else waits for the marker to reappear
            data = read_until(lambda s: MARKER in s, max_wait)
            if data:
                text = clean(data.decode("utf-8", "replace"))
                fh.write(json.dumps([round(time.time() - start, 3), "o", text]) + "\n")
                fh.flush()
        os.write(master, b"exit\n")
        tail = read_until(lambda s: False, 5.0)
        if tail:
            fh.write(
                json.dumps(
                    [
                        round(time.time() - start, 3),
                        "o",
                        clean(tail.decode("utf-8", "replace")),
                    ]
                )
                + "\n"
            )

    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
    duration = round(time.time() - start, 2)
    print(f"recorded {out_path} ({duration}s, {len(commands)} commands)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--title", default="mycelium")
    parser.add_argument("--cmd", action="append", default=[])
    parser.add_argument("--width", type=int, default=100)
    parser.add_argument("--height", type=int, default=28)
    parser.add_argument("--max-wait", type=float, default=900.0)
    parser.add_argument("--cwd", default=None)
    args = parser.parse_args()
    if not args.cmd:
        parser.error("at least one --cmd is required")
    out = OUT_DIR / f"{args.name}.cast"
    return record_commands(
        args.cmd,
        out,
        title=args.title,
        width=args.width,
        height=args.height,
        max_wait=args.max_wait,
        cwd=Path(args.cwd) if args.cwd else None,
    )


if __name__ == "__main__":
    raise SystemExit(main())
