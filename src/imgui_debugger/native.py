"""imgui's own debug windows as standalone panels, reachable without the demo.

Normally these are opened from the demo window's Tools menu. Each one here is a
:class:`~imgui_debugger.panel.Panel`, so it mounts on your menu and toggles like
any other tool. imgui owns the window and its title, so the config's title is
the menu label; everything else about the body is imgui's.

Examples
--------
>>> from imgui_debugger import MetricsPanel
>>> panel = MetricsPanel()
>>> panel.title
'Metrics / Debugger'
>>> panel.hide()
>>> panel.render_window()
False
"""

from __future__ import annotations

from dataclasses import dataclass

from imgui_bundle import imgui

from .panel import Panel, PanelConfig


@dataclass
class NativePanelConfig(PanelConfig):
    """A :class:`~imgui_debugger.panel.PanelConfig` for an imgui-owned window.

    ``window_size``, ``window_pos``, ``window_flags`` and ``closable`` are
    ignored: imgui begins and ends the window itself.

    Examples
    --------
    >>> from imgui_debugger import NativePanelConfig
    >>> NativePanelConfig(title="Metrics", visible=False).visible
    False
    """

    visible: bool = False


class NativeWindowPanel(Panel):
    """Base for a panel whose body is an imgui window we only toggle.

    Window-only by design: :meth:`render` raises, because imgui's own
    ``show_*_window`` calls cannot be drawn inside someone else's window.

    Examples
    --------
    >>> from imgui_debugger import DebugLogPanel
    >>> panel = DebugLogPanel()
    >>> panel.show()
    >>> panel.render_window()          # doctest: +SKIP
    True
    """

    config_class = NativePanelConfig
    show_window = None

    def render_window(self, flags: int = 0) -> bool:
        """Call imgui's ``show_*_window`` and keep :attr:`visible` in sync.

        Parameters
        ----------
        flags : int
            Ignored; imgui owns the window.

        Returns
        -------
        bool
            Whether the window was asked to draw this frame.

        Examples
        --------
        >>> from imgui_debugger import AboutPanel
        >>> AboutPanel().render_window()
        False
        """
        self.poll_hotkey()
        if not self.visible:
            return False
        opened = type(self).show_window(True)
        if opened is not None:
            self.visible = bool(opened)
        return True


class MetricsPanel(NativeWindowPanel):
    """imgui's Metrics / Debugger: windows, draw lists, viewports, internal state.

    Examples
    --------
    >>> from imgui_debugger import MetricsPanel, NativePanelConfig
    >>> MetricsPanel(NativePanelConfig(title="Metrics", visible=True)).visible
    True
    """

    config_class = NativePanelConfig
    show_window = staticmethod(imgui.show_metrics_window)

    def __init__(self, config=None):
        super().__init__(config or NativePanelConfig(title="Metrics / Debugger"))


class DebugLogPanel(NativeWindowPanel):
    """imgui's Debug Log: focus, nav, docking and IO events as they happen.

    Examples
    --------
    >>> from imgui_debugger import DebugLogPanel
    >>> DebugLogPanel().title
    'Debug Log'
    """

    config_class = NativePanelConfig
    show_window = staticmethod(imgui.show_debug_log_window)

    def __init__(self, config=None):
        super().__init__(config or NativePanelConfig(title="Debug Log"))


class IdStackPanel(NativeWindowPanel):
    """imgui's ID Stack Tool: what an item's id is built from, for id collisions.

    Examples
    --------
    >>> from imgui_debugger import IdStackPanel
    >>> IdStackPanel().title
    'ID Stack Tool'
    """

    config_class = NativePanelConfig
    show_window = staticmethod(imgui.show_id_stack_tool_window)

    def __init__(self, config=None):
        super().__init__(config or NativePanelConfig(title="ID Stack Tool"))


class AboutPanel(NativeWindowPanel):
    """imgui's About window: version and the build's enabled features.

    Examples
    --------
    >>> from imgui_debugger import AboutPanel
    >>> AboutPanel().title
    'About Dear ImGui'
    """

    config_class = NativePanelConfig
    show_window = staticmethod(imgui.show_about_window)

    def __init__(self, config=None):
        super().__init__(config or NativePanelConfig(title="About Dear ImGui"))


class DemoPanel(NativeWindowPanel):
    """imgui's demo window, for looking up a widget; not in the default tool set.

    Examples
    --------
    >>> from imgui_debugger import DemoPanel
    >>> DemoPanel().title
    'Dear ImGui Demo'
    """

    config_class = NativePanelConfig
    show_window = staticmethod(imgui.show_demo_window)

    def __init__(self, config=None):
        super().__init__(config or NativePanelConfig(title="Dear ImGui Demo"))


class UserGuidePanel(Panel):
    """imgui's built-in control reference, drawable inline or in its own window.

    Examples
    --------
    >>> from imgui_debugger import UserGuidePanel
    >>> UserGuidePanel().title
    'Controls'
    >>> UserGuidePanel().render()      # doctest: +SKIP
    """

    config_class = NativePanelConfig

    def __init__(self, config=None):
        super().__init__(config or NativePanelConfig(title="Controls"))

    def render(self) -> None:
        """Draw imgui's user guide at the current cursor.

        Examples
        --------
        >>> from imgui_debugger import UserGuidePanel
        >>> UserGuidePanel().render()  # doctest: +SKIP
        """
        imgui.show_user_guide()
