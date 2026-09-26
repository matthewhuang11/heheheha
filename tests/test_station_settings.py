"""Profiles and settings (C1): the mac alias, a helpful unknown-profile message, utf-8 files, a bad CAMERA_INDEX."""
import pytest
from scoutbot import settings

def test_mac_is_an_alias_for_laptop():
    a = settings.load("mac", load_env=False); b = settings.load("laptop", load_env=False)
    assert a["profile"] == "laptop" and a == b
    assert a["hw"]["distance"] == "sliders"


def test_sim_profile_needs_no_webcam():
    assert settings.load("sim", load_env=False)["hw"]["camera"] == "synthetic"


def test_unknown_profile_lists_the_choices():
    with pytest.raises(SystemExit) as e: settings.load("nope", load_env=False)
    msg = str(e.value)
    for name in ("laptop", "sim", "pi"): assert name in msg

def test_utf8_profile_loads(tmp_path, monkeypatch):
    (tmp_path / "base.yaml").write_text((settings.PROFILES / "base.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "utf.yaml").write_text("# café ± naïve 🤖\nserver: {port: 8123}\n", encoding="utf-8")
    monkeypatch.setattr(settings, "PROFILES", tmp_path)
    assert settings.load("utf", load_env=False)["server"]["port"] == 8123

def test_bad_camera_index_is_ignored(monkeypatch):
    monkeypatch.setenv("CAMERA_INDEX", "front")
    cfg = settings.load("laptop", load_env=False)
    assert isinstance(cfg["hw"]["camera_index"], int)
    monkeypatch.setenv("CAMERA_INDEX", "2")
    assert settings.load("laptop", load_env=False)["hw"]["camera_index"] == 2

def test_share_sets_host(monkeypatch):
    from scoutbot import __main__ as m
    urls = m.dashboard_urls("0.0.0.0", 8000, "")
    assert urls[0] == ("dashboard", "http://localhost:8000") and len(urls) >= 2
    assert m.dashboard_urls("127.0.0.1", 8001, "abc") == [("dashboard", "http://localhost:8001/?token=abc")]

def test_placeholder_env_values_are_ignored(monkeypatch):
    monkeypatch.setenv("SCOUTBOT_TOKEN", "replace_with_a_long_random_token")
    monkeypatch.setenv("MONGODB_URI", "mongodb://user:password@host/database")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-flash-lite-latest")
    assert set(settings.drop_placeholders()) == {"SCOUTBOT_TOKEN", "MONGODB_URI"}
    import os
    assert "SCOUTBOT_TOKEN" not in os.environ and os.environ["GEMINI_MODEL"] == "gemini-flash-lite-latest"

def test_setup_never_copies_placeholders(tmp_path, monkeypatch):
    import importlib.util
    spec = importlib.util.spec_from_file_location("setup_script", settings.ROOT / "scripts" / "setup.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    (tmp_path / ".env.example").write_text("# c\nGEMINI_API_KEY=your_key\nGEMINI_MODEL=gemini-flash-lite-latest\nSCOUTBOT_TOKEN=replace_with_x\n", encoding="utf-8")
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    mod.make_env()
    env = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "GEMINI_API_KEY=\n" in env and "SCOUTBOT_TOKEN=\n" in env and "GEMINI_MODEL=gemini-flash-lite-latest" in env
