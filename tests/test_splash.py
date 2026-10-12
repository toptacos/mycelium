import io
import sys

import pytest

from mycelium import splash


def test_frames_are_well_formed():
    frames = splash.frames()
    assert len(frames) > 10
    first, last = frames[0], frames[-1]
    assert all(len(row) <= 200 for row in first)
    assert any("mycelium" in row for row in last)
    assert all(len(f) == len(frames[0]) or len(f) == len(frames[0]) + 1 for f in frames)


def test_frames_grow_over_time():
    frames = splash.frames()
    painted = [sum(1 for row in f if row) for f in frames]
    assert painted[0] < painted[-1]
    assert painted[-1] >= 10


def test_cap_gradient_spectrum():
    top = splash._cap_gradient(0)
    bottom = splash._cap_gradient(5)
    assert top[0] > top[2]  # magenta end: red dominant
    assert bottom[2] > bottom[0]  # cyan end: blue dominant


def test_disabled_by_env(monkeypatch):
    monkeypatch.setenv("MYCELIUM_NO_SPLASH", "1")
    assert splash.enabled(None) is False


def test_disabled_by_flag(monkeypatch):
    monkeypatch.delenv("MYCELIUM_NO_SPLASH", raising=False)

    class Args:
        no_splash = True
        json = False

    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    assert splash.enabled(Args()) is False


def test_disabled_for_json(monkeypatch):
    monkeypatch.delenv("MYCELIUM_NO_SPLASH", raising=False)

    class Args:
        no_splash = False
        json = True

    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    assert splash.enabled(Args()) is False


def test_disabled_when_not_a_tty(monkeypatch):
    monkeypatch.delenv("MYCELIUM_NO_SPLASH", raising=False)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
    assert splash.enabled(None) is False


def test_enabled_on_tty(monkeypatch):
    monkeypatch.delenv("MYCELIUM_NO_SPLASH", raising=False)

    class Args:
        no_splash = False
        json = False

    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    assert splash.enabled(Args()) is True


def test_show_noops_without_tty(monkeypatch, capsys):
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
    splash.show()
    assert capsys.readouterr().out == ""


def test_show_renders_frames_on_tty(monkeypatch):
    buffer = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buffer)
    monkeypatch.setattr(splash.time, "sleep", lambda _s: None)

    class FakeTTY(io.StringIO):
        def isatty(self):
            return True

    fake = FakeTTY()
    monkeypatch.setattr(sys, "stdout", fake)
    splash.show()
    out = fake.getvalue()
    assert "\x1b[?25l" in out
    assert "\x1b[?25h" in out
    assert "mycelium" in out
    assert "\x1b[38;2;255;46;136m" in out  # magenta present
    assert "\x1b[38;2;163;230;53m" in out  # lime threads present
    assert "\x1b[38;2;34;211;238m" in out  # cyan accent present


def test_frames_contain_threads_and_spores():
    frames = splash.frames()
    joined = "\n".join("\n".join(f) for f in frames)
    assert "~" in joined
    assert "*" in joined
