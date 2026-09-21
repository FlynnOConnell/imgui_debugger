"""Every tool shares one surface: visibility, a menu entry and its own window."""

import pytest
from imgui_bundle import imgui

from imgui_debugger import (
    AboutPanel,
    DebugLogPanel,
    Debugger,
    DemoPanel,
    Hotkey,
    IdStackPanel,
    MetricsPanel,
    Panel,
    PanelConfig,
    StyleEditor,
    UserGuidePanel,
)

PANELS = [Debugger, StyleEditor, MetricsPanel, DebugLogPanel, IdStackPanel, AboutPanel,
          DemoPanel, UserGuidePanel]


class Counter(Panel):
    config_class = PanelConfig

    def __init__(self, config=None):
        super().__init__(config)
        self.frames = 0

    def render(self):
        self.frames += 1


@pytest.mark.parametrize("cls", PANELS)
def test_every_panel_shares_the_surface(cls):
    panel = cls()
    assert isinstance(panel, Panel)
    assert isinstance(panel.title, str) and panel.title
    panel.show()
    assert panel.visible
    panel.toggle()
    assert not panel.visible


@pytest.mark.parametrize("cls", PANELS)
def test_window_id_is_stable_and_unique(cls):
    ident = cls().window_id
    assert ident == cls().window_id
    assert "##imgui_debugger_" in ident


def test_window_id_follows_the_config():
    panel = Counter(PanelConfig(title="Counter", window_id="counter"))
    assert panel.window_id == "Counter##imgui_debugger_counter"


def test_window_id_defaults_to_the_class_name():
    assert Counter().window_id.endswith("##imgui_debugger_Counter")


def test_visible_comes_from_the_config():
    assert not Counter(PanelConfig(visible=False)).visible
    assert Counter(PanelConfig(visible=True)).visible


def test_native_panels_start_closed():
    assert not MetricsPanel().visible
    assert not DebugLogPanel().visible


def test_hidden_panel_draws_nothing():
    panel = Counter(PanelConfig(visible=False))
    assert panel.render_window() is False
    assert panel.frames == 0


def test_native_panels_have_no_inline_body():
    with pytest.raises(NotImplementedError):
        MetricsPanel().render()


def test_user_guide_is_inline_capable():
    assert UserGuidePanel().render is not Panel.render


def test_hotkey_text_reads_like_a_menu_shortcut():
    assert Hotkey(imgui.Key.f12).text == "F12"
    assert Hotkey(imgui.Key.d, ctrl=True).text == "Ctrl+D"
    assert Hotkey(imgui.Key.d, ctrl=True, shift=True, alt=True).text == "Ctrl+Shift+Alt+D"


def test_a_panel_without_a_hotkey_never_toggles_on_poll():
    assert Counter().poll_hotkey() is False


def test_base_render_is_abstract():
    with pytest.raises(NotImplementedError):
        Panel(PanelConfig()).render()
