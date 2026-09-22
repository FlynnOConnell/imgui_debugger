"""The config store: state file, named presets, panel state, layout ini."""

import os

from imgui_bundle import imgui

from imgui_debugger import (
    ConfigStore,
    DebugTools,
    StyleEditor,
    StyleEditorConfig,
    style_to_dict,
)


def test_missing_root_reads_as_empty(tmp_path):
    store = ConfigStore(tmp_path / "never-made")
    assert store.read_state() == {}
    assert store.style() is None
    assert store.presets() == []
    assert store.active_preset() is None
    assert store.panel_state("x") == {}


def test_construction_creates_nothing(tmp_path):
    root = tmp_path / "cfg"
    ConfigStore(root)
    assert not root.exists()


def test_state_round_trips(tmp_path):
    store = ConfigStore(tmp_path / "cfg")
    assert store.write_state({"a": 1})
    assert store.read_state() == {"a": 1}
    store.update_state(b=2)
    assert store.read_state() == {"a": 1, "b": 2}


def test_corrupt_state_reads_as_empty(tmp_path):
    store = ConfigStore(tmp_path / "cfg")
    store.write_state({"a": 1})
    store.state_path.write_text("{ not json")
    assert store.read_state() == {}


def test_style_round_trips(tmp_path):
    store = ConfigStore(tmp_path / "cfg")
    src = imgui.Style()
    src.frame_rounding = 7.0
    store.set_style(style_to_dict(src))

    dst = imgui.Style()
    assert store.apply_style(dst) > 0
    assert dst.frame_rounding == 7.0


def test_apply_style_with_nothing_saved(tmp_path):
    assert ConfigStore(tmp_path / "cfg").apply_style(imgui.Style()) == 0


def test_presets_are_listed_and_deleted(tmp_path):
    store = ConfigStore(tmp_path / "cfg")
    store.write_preset("night", {"sizes": {"frame_rounding": 8.0}})
    store.write_preset("day", {"sizes": {}})
    assert store.presets() == ["day", "night"]
    assert store.read_preset("night")["sizes"]["frame_rounding"] == 8.0
    assert store.delete_preset("night")
    assert store.presets() == ["day"]
    assert not store.delete_preset("night")


def test_preset_names_are_made_safe(tmp_path):
    store = ConfigStore(tmp_path / "cfg")
    path = store.write_preset("Night / high", {"sizes": {}})
    assert "/" not in path.name
    assert store.read_preset("Night / high") is not None


def test_active_preset_is_recorded(tmp_path):
    store = ConfigStore(tmp_path / "cfg")
    store.set_active_preset("night")
    assert store.active_preset() == "night"
    store.set_active_preset(None)
    assert store.active_preset() is None


def test_panel_state_is_per_key(tmp_path):
    store = ConfigStore(tmp_path / "cfg")
    store.set_panel_state("a", {"visible": True})
    store.set_panel_state("b", {"visible": False})
    assert store.panel_state("a") == {"visible": True}
    assert store.panel_state("b") == {"visible": False}


def test_layout_ini_is_absolute(tmp_path):
    ini = ConfigStore(tmp_path / "cfg").layout_ini
    assert ini.endswith("layout.ini")
    assert os.path.isabs(ini)


def test_editor_save_and_load_use_the_store(tmp_path, imgui_context):
    store = ConfigStore(tmp_path / "cfg")
    editor = StyleEditor(StyleEditorConfig(store=store))
    editor.save()
    assert "saved to" in editor.status
    assert store.style() is not None
    editor.load()
    assert "loaded" in editor.status


def test_editor_load_with_nothing_saved(tmp_path):
    editor = StyleEditor(StyleEditorConfig(store=ConfigStore(tmp_path / "cfg")))
    editor.load()
    assert editor.status == "nothing saved yet"


def test_hooks_still_win_over_the_store(tmp_path, imgui_context):
    seen = []
    editor = StyleEditor(
        StyleEditorConfig(store=ConfigStore(tmp_path / "cfg"), on_save=seen.append)
    )
    editor.save()
    assert len(seen) == 1
    assert not (tmp_path / "cfg").exists()


def test_editor_presets(tmp_path, imgui_context):
    store = ConfigStore(tmp_path / "cfg")
    editor = StyleEditor(StyleEditorConfig(store=store))
    editor.save_preset("night")
    assert editor.presets() == ["night"]
    assert store.active_preset() == "night"
    editor.load_preset("night")
    assert "loaded preset" in editor.status
    editor.load_preset("missing")
    assert editor.status == "no preset 'missing'"
    editor.delete_preset("night")
    assert editor.presets() == []
    assert store.active_preset() is None


def test_editor_without_a_store_has_no_presets():
    editor = StyleEditor()
    editor.save_preset("night")
    assert editor.presets() == []


def test_autosave_waits_for_quiet(tmp_path, imgui_context):
    store = ConfigStore(tmp_path / "cfg")
    editor = StyleEditor(StyleEditorConfig(store=store, autosave_delay=60.0))
    assert not editor.dirty
    editor.mark_dirty()
    assert editor.dirty
    assert editor.flush_autosave() is False
    assert store.style() is None
    assert editor.flush_autosave(force=True) is True
    assert store.style() is not None
    assert not editor.dirty


def test_autosave_off_writes_nothing(tmp_path, imgui_context):
    store = ConfigStore(tmp_path / "cfg")
    editor = StyleEditor(StyleEditorConfig(store=store, autosave=False))
    editor.mark_dirty()
    assert editor.flush_autosave(force=True) is False


def test_panel_state_round_trips():
    editor = StyleEditor(StyleEditorConfig(visible=False, show_sizes=False))
    state = editor.get_state()
    assert state == {
        "visible": False,
        "show_sizes": False,
        "show_colors": True,
        "show_rendering": True,
    }
    other = StyleEditor()
    other.set_state(state)
    assert other.visible is False
    assert other.config.show_sizes is False


def test_panel_set_state_ignores_unknown_keys():
    editor = StyleEditor()
    editor.set_state({"nonsense": 1})
    assert editor.visible


def test_tools_save_and_load_panel_state(tmp_path):
    store = ConfigStore(tmp_path / "cfg")
    tools = DebugTools.default(store=store)
    tools["Metrics / Debugger"].show()
    tools["Debugger"].config.private = True
    assert tools.save_state()

    fresh = DebugTools.default(store=store)
    assert fresh.load_state()
    assert fresh["Metrics / Debugger"].visible
    assert fresh["Debugger"].config.private


def test_tools_without_a_store_do_nothing():
    tools = DebugTools.default()
    assert tools.load_state() is False
    assert tools.save_state() is False
    assert tools.apply_style() == 0


def test_tools_load_state_with_nothing_saved(tmp_path):
    tools = DebugTools.default(store=ConfigStore(tmp_path / "cfg"))
    assert tools.load_state() is False


def test_tools_default_hands_the_store_to_the_editor(tmp_path):
    store = ConfigStore(tmp_path / "cfg")
    assert DebugTools.default(store=store)["Style Editor"].config.store is store
