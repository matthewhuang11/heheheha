"""The start menu (C4) builds the right command for every choice, without running anything."""
import sys
import pytest
from scoutbot import start

@pytest.fixture
def calls(monkeypatch):
    seen = []
    monkeypatch.setattr(start.subprocess, "call", lambda cmd, cwd=None: seen.append(cmd) or 0)
    return seen

@pytest.mark.parametrize("choice,expect", [
    ("sim", ["-m", "scoutbot", "--profile", "sim", "--set", "sim.world=demo"]),
    ("laptop", ["-m", "scoutbot", "--profile", "laptop"]),
    ("offline", ["-m", "scoutbot", "--profile", "laptop", "--set", "net.force_offline=true"]),
    ("robot", ["-m", "scoutbot", "--profile", "pi"]),
    ("doctor", ["-m", "scoutbot.tools.doctor"]),
    ("test", ["-m", "pytest", "-q", "tests"]),
])
def test_each_choice(calls, choice, expect):
    assert start.main([choice]) == 0
    assert calls == [[sys.executable, *expect]]

def test_share_and_numbers(calls):
    start.main(["1", "--share"]); start.main(["doctor", "--share"])
    assert calls[0][-1] == "--share" and "--share" not in calls[1]     # sharing only for things with a dashboard

def test_menu_default_and_share_question(calls, monkeypatch):
    answers = iter(["", "y"])
    monkeypatch.setattr("builtins.input", lambda _p="": next(answers))
    assert start.main([]) == 0
    assert calls[0][1:5] == ["-m", "scoutbot", "--profile", "sim"] and calls[0][-1] == "--share"

def test_unknown_choice(calls, capsys):
    assert start.main(["fly"]) == 2 and calls == []
    assert "sim" in capsys.readouterr().out

def test_lan_ips_are_not_loopback():
    assert all(not ip.startswith("127.") for ip in start.lan_ips())
