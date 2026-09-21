"""Debugger assembles its scopes and honors its config, with no imgui context."""

import pytest

from imgui_debugger import Debugger, DebuggerConfig, Theme, attach, watch_all


class Tab:
    name = "Voltage"

    def __init__(self):
        self.selected = 2
        self.metadata = {"fs": 9.6}


def test_attach_builds_the_object_scopes():
    dbg = attach(Tab(), show_frame=False, show_runtime=False)
    assert [s.name for s in dbg.scopes()] == ["instance", "properties", "class"]


def test_attach_rejects_unknown_config_fields():
    with pytest.raises(TypeError):
        attach(Tab(), nonsense=1)


def test_kwargs_override_a_supplied_config():
    cfg = DebuggerConfig(title="old", theme=Theme.light())
    dbg = attach(Tab(), cfg, title="new")
    assert dbg.config.title == "new"
    assert dbg.theme == Theme.light()


def test_frame_and_runtime_scopes_are_appended_last():
    dbg = attach(Tab())
    assert [s.name for s in dbg.scopes()][-3:] == ["locals", "globals", "imgui"]


def test_watch_replaces_a_name():
    dbg = Debugger(DebuggerConfig(show_frame=False, show_runtime=False))
    dbg.watch("state", {"a": 1})
    dbg.watch("state", {"b": 2})
    assert [s.name for s in dbg.scopes()] == ["state"]
    assert [c.name for c in dbg.scopes()[0].children()] == ["b"]


def test_watch_all_promotes_attributes():
    tab = Tab()
    dbg = watch_all(tab, ["metadata"], show_frame=False, show_runtime=False)
    scope = next(s for s in dbg.scopes() if s.name == "metadata")
    tab.metadata["dz"] = 5
    assert [c.name for c in scope.children()] == ["fs", "dz"]


def test_set_target_swaps_the_object():
    dbg = attach({"a": 1}, show_frame=False, show_runtime=False)
    dbg.set_target({"b": 2})
    assert dbg.target == {"b": 2}


def test_visibility_toggles():
    dbg = Debugger()
    assert dbg.visible
    dbg.toggle()
    assert not dbg.visible
    dbg.show()
    assert dbg.visible


def test_style_mirrors_the_config():
    dbg = attach(Tab(), private=True, max_depth=3, value_col=200.0)
    dbg.set_filter("fs")
    style = dbg.style()
    assert (style.private, style.max_depth, style.value_col, style.filter) == (
        True,
        3,
        200.0,
        "fs",
    )


def test_force_open_is_one_shot_per_render():
    dbg = attach(Tab())
    dbg.expand_all()
    assert dbg.style().force_open is True
    dbg.collapse_all()
    assert dbg.style().force_open is False


def test_capture_follows_the_calling_frame():
    dbg = Debugger()
    local_marker = 3
    dbg.capture()
    locals_scope = next(s for s in dbg.scopes() if s.name == "locals")
    assert any(c.name == "local_marker" for c in locals_scope.children())
    assert local_marker == 3
