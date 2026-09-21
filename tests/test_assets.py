"""Per-user paths follow IMGUI_DEBUGGER_HOME and nothing else."""

from pathlib import Path

from imgui_debugger._assets import (
    data_dir,
    default_ini_path,
    imgui_bundle_assets_dir,
    user_assets_dir,
)


def test_data_dir_follows_the_env_var(tmp_path, monkeypatch):
    monkeypatch.setenv("IMGUI_DEBUGGER_HOME", str(tmp_path / "home"))
    assert data_dir() == tmp_path / "home"
    assert data_dir().is_dir()


def test_default_dir_is_a_dotfolder(monkeypatch):
    monkeypatch.delenv("IMGUI_DEBUGGER_HOME", raising=False)
    assert data_dir() == Path.home() / ".imgui_debugger"


def test_ini_path_is_absolute_and_named(tmp_path, monkeypatch):
    monkeypatch.setenv("IMGUI_DEBUGGER_HOME", str(tmp_path))
    ini = Path(default_ini_path("panel"))
    assert ini.is_absolute()
    assert ini.name == "panel.ini"


def test_user_assets_dir_is_not_created(tmp_path, monkeypatch):
    monkeypatch.setenv("IMGUI_DEBUGGER_HOME", str(tmp_path))
    assert not user_assets_dir().exists()


def test_bundled_assets_resolve():
    folder = imgui_bundle_assets_dir()
    assert folder is None or Path(folder).is_dir()
