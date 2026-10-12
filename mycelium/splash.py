from __future__ import annotations

import os
import sys
import time

MAGENTA = (255, 46, 136)
VIOLET = (139, 47, 201)
CYAN = (34, 211, 238)
LIME = (163, 230, 53)
AMBER = (251, 191, 36)
CREAM = (255, 243, 226)

WIDTH = 25
ROWS = 10
DURATION_S = 1.4
FRAME_S = 0.1

ENV_DISABLE = "MYCELIUM_NO_SPLASH"

_CAP_TOP = "      .-~~~~~~~-.       "
_CAP_ROWS = [
    "    .'   o o o   '.     ",
    "   /   o   *   o   \\    ",
    "  |    *   o*   o    |  ",
    "   \\     o    *    /    ",
]
_CAP_BOTTOM = "      '-._____.-'       "
_STEM_ROWS = ["       |     |         ", "      /       \\        "]
_THREADS = "~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~"
_THREADS_DEEP = "~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~"

_SPORES = [(6, 0.0, 1.0), (17, 0.45, 1.25), (12, 0.8, 0.9)]


def _paint(text: str, color: tuple[int, int, int]) -> str:
    r, g, b = color
    return f"\x1b[38;2;{r};{g};{b}m{text}\x1b[0m"


def _mix(
    a: tuple[int, int, int], b: tuple[int, int, int], t: float
) -> tuple[int, int, int]:
    return (
        int(round(a[0] + (b[0] - a[0]) * t)),
        int(round(a[1] + (b[1] - a[1]) * t)),
        int(round(a[2] + (b[2] - a[2]) * t)),
    )


def _cap_gradient(row: int) -> tuple[int, int, int]:
    t = row / 5
    if t < 0.6:
        return _mix(MAGENTA, VIOLET, t / 0.6)
    return _mix(VIOLET, CYAN, (t - 0.6) / 0.4)


def _rows_at(t: float) -> list[str]:
    grid: list[list[tuple[str, tuple[int, int, int] | None]]] = [
        [(" ", None)] * WIDTH for _ in range(ROWS)
    ]

    def stamp(
        text: str,
        row: int,
        color: tuple[int, int, int],
        accent: tuple[int, int, int] | None = None,
    ) -> None:
        if not (0 <= row < ROWS):
            return
        for x, ch in enumerate(text[:WIDTH]):
            if ch == " ":
                continue
            cell_color = accent if (accent and ch in "o*") else color
            grid[row][x] = (ch, cell_color)

    if t >= 0.10:
        stamp(_CAP_TOP, 0, _cap_gradient(0), CYAN)
    body_start = max(0.0, min(1.0, (t - 0.18) / 0.42))
    for i, row_text in enumerate(_CAP_ROWS):
        if body_start > i / len(_CAP_ROWS):
            stamp(row_text, 1 + i, _cap_gradient(i + 1), CYAN)
    if t >= 0.62:
        stamp(_CAP_BOTTOM, 5, _cap_gradient(5))
    stem_start = max(0.0, min(1.0, (t - 0.66) / 0.18))
    for i, row_text in enumerate(_STEM_ROWS):
        if stem_start > i / len(_STEM_ROWS):
            stamp(row_text, 6 + i, CREAM)
    if t >= 0.88:
        stamp(_THREADS, 8, LIME)
        stamp(_THREADS_DEEP, 9, _mix(LIME, VIOLET, 0.45))

    for x0, phase, speed in _SPORES:
        spore_t = (t - 0.25 - phase * 0.3) * speed
        if 0.0 <= spore_t <= 1.0:
            x = min(WIDTH - 1, max(0, x0 + int(spore_t * 4) - 1))
            y = int(6 - spore_t * 7)
            if 0 <= y < 7:
                grid[y][x] = ("*", AMBER)

    lines: list[str] = []
    for row in grid:
        out = ""
        run_color: tuple[int, int, int] | None = None
        run_text = ""
        for ch, color in row:
            if ch == " " and not run_text:
                out += " "
                continue
            if color != run_color:
                if run_text:
                    out += _paint(run_text, run_color or (255, 255, 255))
                run_color = color
                run_text = ch
            else:
                run_text += ch
        if run_text:
            out += _paint(run_text, run_color or (255, 255, 255))
        lines.append(out.rstrip() or "")
    return lines


def _wordmark() -> str:
    return (
        _paint("   mycelium", MAGENTA)
        + _paint("  ·  ", VIOLET)
        + _paint("plant it once, it grows", CYAN)
    )


def frames() -> list[list[str]]:
    count = int(DURATION_S / FRAME_S)
    out: list[list[str]] = []
    for i in range(count + 1):
        t = i / count
        rows = _rows_at(t)
        if t >= 0.95:
            rows = [r for r in rows] + [_wordmark()]
        out.append(rows)
    return out


def enabled(args: object = None) -> bool:
    if os.environ.get(ENV_DISABLE, "").lower() in ("1", "true", "yes"):
        return False
    if args is not None and getattr(args, "no_splash", False):
        return False
    if args is not None and getattr(args, "json", False):
        return False
    return sys.stdout.isatty()


def show() -> None:
    if not sys.stdout.isatty():
        return
    sys.stdout.write("\x1b[?25l\x1b[2J\x1b[H")
    sys.stdout.flush()
    try:
        for frame in frames():
            sys.stdout.write("\x1b[2J\x1b[H" + "\n".join(frame) + "\n")
            sys.stdout.flush()
            time.sleep(FRAME_S)
        sys.stdout.write("\x1b[2J\x1b[H" + "\n".join(frames()[-1]) + "\n")
        sys.stdout.flush()
    finally:
        sys.stdout.write("\x1b[?25h")
        sys.stdout.flush()
