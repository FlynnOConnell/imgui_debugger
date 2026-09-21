"""A DebugTools set is an ordered, editable collection of panels."""

import pytest

from imgui_debugger import (
    AboutPanel,
    DebugTools,
    Debugger,
    DemoPanel,
    MetricsPanel,
    StyleEditor,
)


class Widget:
    def __init__(self):
        self.threshold = 0.4


def test_default_set_order():
    assert [p.title for p in DebugTools.default()] == [
        "Debugger",
        "Style Editor",
        "Metrics / Debugger",
        "Debug Log",
        "ID Stack Tool",
    ]


def test_default_set_excludes_the_demo():
    assert not any(isinstance(p, DemoPanel) for p in DebugTools.default())


def test_default_set_starts_closed():
    assert not any(p.visible for p in DebugTools.default())


def test_default_passes_config_to_the_inspector():
    tools = DebugTools.default(Widget(), private=True, show_runtime=False)
    dbg = tools.debugger()
    assert dbg.config.private
    assert isinstance(dbg.target, Widget)


def test_lookup_by_title():
    tools = DebugTools.default()
    assert isinstance(tools["Style Editor"], StyleEditor)
    with pytest.raises(KeyError):
        tools["nope"]


def test_add_replaces_a_title():
    tools = DebugTools([StyleEditor()])
    tools.add(StyleEditor())
    assert len(tools) == 1


def test_add_accepts_any_panel():
    tools = DebugTools([StyleEditor()])
    tools.add(AboutPanel())
    tools.add(DemoPanel())
    assert len(tools) == 3


def test_remove_is_forgiving():
    tools = DebugTools([StyleEditor()])
    tools.remove("not there")
    tools.remove("Style Editor")
    assert len(tools) == 0


def test_show_and_hide_all():
    tools = DebugTools.default()
    tools.show_all()
    assert all(tools.visible().values())
    tools.hide_all()
    assert not any(tools.visible().values())


def test_debugger_returns_none_without_one():
    assert DebugTools([MetricsPanel()]).debugger() is None


def test_debugger_finds_the_inspector():
    assert isinstance(DebugTools.default().debugger(), Debugger)


def test_menu_label_is_configurable():
    assert DebugTools.default(menu_label="Tools").menu_label == "Tools"
