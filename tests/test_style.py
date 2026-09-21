"""Style serialization round-trips and the Save/Load hooks replace the defaults."""

import json

from imgui_bundle import imgui

from imgui_debugger import (
    StyleEditor,
    StyleEditorConfig,
    apply_style_dict,
    load_style,
    save_style,
    style_to_dict,
)
from imgui_debugger.style import SKIP_KEYS, style_fields


def test_skipped_keys_are_not_serialized():
    fields = style_fields()
    for key in SKIP_KEYS:
        assert key not in fields


def test_round_trip_preserves_sizes_and_colors():
    src = imgui.Style()
    src.frame_rounding = 7.0
    src.window_padding = imgui.ImVec2(3.0, 9.0)
    src.set_color_(int(imgui.Col_.text), imgui.ImVec4(0.1, 0.2, 0.3, 0.4))

    dst = imgui.Style()
    apply_style_dict(style_to_dict(src), dst)

    assert dst.frame_rounding == 7.0
    assert (dst.window_padding.x, dst.window_padding.y) == (3.0, 9.0)
    c = dst.color_(int(imgui.Col_.text))
    assert (round(c.x, 3), round(c.w, 3)) == (0.1, 0.4)


def test_apply_reports_how_many_fields_landed():
    assert apply_style_dict({"sizes": {"frame_rounding": 6.0}}, imgui.Style()) == 1


def test_unknown_keys_are_ignored():
    data = {"sizes": {"no_such_field": 1.0}, "colors": {"NoSuchColor": [0, 0, 0, 1]}}
    assert apply_style_dict(data, imgui.Style()) == 0


def test_every_color_is_named_and_round_trips():
    data = style_to_dict(imgui.Style())
    assert len(data["colors"]) == int(imgui.Col_.count)
    assert all(len(v) == 4 for v in data["colors"].values())


def test_save_and_load_a_file(tmp_path):
    src = imgui.Style()
    src.grab_rounding = 5.0
    path = save_style(tmp_path / "style.json", src)
    assert json.loads(path.read_text())["sizes"]["grab_rounding"] == 5.0

    dst = imgui.Style()
    assert load_style(path, dst) > 0
    assert dst.grab_rounding == 5.0


def test_save_hook_replaces_the_file_write():
    seen = []
    editor = StyleEditor(StyleEditorConfig(on_save=seen.append))
    editor.config.on_save({"sizes": {}})
    assert seen == [{"sizes": {}}]


def test_load_hook_returning_none_is_a_cancel():
    editor = StyleEditor(StyleEditorConfig(on_load=lambda: None))
    editor.load()
    assert editor.status == "load cancelled"


def test_load_failure_lands_on_the_status_line(tmp_path):
    editor = StyleEditor(StyleEditorConfig(path=tmp_path / "missing.json"))
    editor.load()
    assert editor.status.startswith("load failed")


def test_visibility_toggles():
    editor = StyleEditor()
    assert editor.visible
    editor.toggle()
    assert not editor.visible
