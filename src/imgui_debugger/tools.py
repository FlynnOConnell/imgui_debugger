"""A set of panels behind one menu, so a host app wires debugging in once.

Examples
--------
>>> from imgui_debugger import DebugTools
>>> tools = DebugTools.default()
>>> [p.title for p in tools]
['Debugger', 'Style Editor', 'Metrics / Debugger', 'Debug Log', 'ID Stack Tool']
>>> tools["Style Editor"].visible
False
"""

from __future__ import annotations

from typing import Dict, Iterator, List, Optional, Sequence

from imgui_bundle import imgui

from .debugger import Debugger, DebuggerConfig
from .native import DebugLogPanel, IdStackPanel, MetricsPanel
from .panel import Panel
from .store import ConfigStore
from .style import StyleEditor, StyleEditorConfig


class DebugTools:
    """An ordered set of panels with one menu and one per-frame call.

    Parameters
    ----------
    panels : Sequence[Panel] | None
        The panels, in menu order.
    menu_label : str
        Label for the menu :meth:`draw_menu` opens.

    Examples
    --------
    >>> from imgui_debugger import DebugTools, StyleEditor, MetricsPanel
    >>> tools = DebugTools([StyleEditor(), MetricsPanel()], menu_label="Debug")
    >>> [p.title for p in tools]
    ['Style Editor', 'Metrics / Debugger']
    >>> tools.hide_all()
    >>> any(p.visible for p in tools)
    False
    """

    def __init__(
        self,
        panels: Optional[Sequence[Panel]] = None,
        menu_label: str = "Debug",
        store: Optional[ConfigStore] = None,
    ):
        self.panels: List[Panel] = list(panels or ())
        self.menu_label = menu_label
        self.store = store

    @classmethod
    def default(
        cls,
        target=None,
        menu_label: str = "Debug",
        store: Optional[ConfigStore] = None,
        **kwargs,
    ) -> "DebugTools":
        """The usual set: variable inspector, style editor and imgui's own tools.

        The demo window is deliberately not included; add
        :class:`~imgui_debugger.native.DemoPanel` if you want it.

        Parameters
        ----------
        target : object | None
            The object the variable inspector starts on.
        menu_label : str
            Label for the menu.
        store : ConfigStore | None
            Where the style editor saves and where :meth:`load_state` and
            :meth:`save_state` read and write the panels.
        **kwargs
            Any :class:`~imgui_debugger.DebuggerConfig` field, for the inspector.

        Examples
        --------
        >>> from imgui_debugger import DebugTools
        >>> tools = DebugTools.default(menu_label="Tools")
        >>> tools.menu_label
        'Tools'
        >>> tools["Debugger"].visible
        False
        """
        debugger = Debugger(
            DebuggerConfig(target=target, visible=False, **kwargs), frame_depth=2
        )
        return cls(
            [
                debugger,
                StyleEditor(StyleEditorConfig(visible=False, store=store)),
                MetricsPanel(),
                DebugLogPanel(),
                IdStackPanel(),
            ],
            menu_label,
            store,
        )

    def __iter__(self) -> Iterator[Panel]:
        """Iterate the panels in menu order.

        Examples
        --------
        >>> from imgui_debugger import DebugTools, StyleEditor
        >>> list(DebugTools([StyleEditor()]))[0].title
        'Style Editor'
        """
        return iter(self.panels)

    def __len__(self) -> int:
        """How many panels are registered.

        Examples
        --------
        >>> from imgui_debugger import DebugTools, StyleEditor
        >>> len(DebugTools([StyleEditor()]))
        1
        """
        return len(self.panels)

    def __getitem__(self, title: str) -> Panel:
        """Look a panel up by its title.

        Parameters
        ----------
        title : str
            The panel's configured title.

        Examples
        --------
        >>> from imgui_debugger import DebugTools, StyleEditor
        >>> DebugTools([StyleEditor()])["Style Editor"].title
        'Style Editor'
        """
        for panel in self.panels:
            if panel.title == title:
                return panel
        raise KeyError(title)

    def add(self, panel: Panel) -> Panel:
        """Register a panel and return it, replacing one with the same title.

        Parameters
        ----------
        panel : Panel
            Any panel, including one of your own.

        Examples
        --------
        >>> from imgui_debugger import DebugTools, StyleEditor, AboutPanel
        >>> tools = DebugTools([StyleEditor()])
        >>> tools.add(AboutPanel()).title
        'About Dear ImGui'
        >>> len(tools)
        2
        """
        self.remove(panel.title)
        self.panels.append(panel)
        return panel

    def remove(self, title: str) -> None:
        """Drop a panel by title; a title that is not registered is fine.

        Parameters
        ----------
        title : str
            The panel's configured title.

        Examples
        --------
        >>> from imgui_debugger import DebugTools, StyleEditor
        >>> tools = DebugTools([StyleEditor()])
        >>> tools.remove("Style Editor")
        >>> len(tools)
        0
        """
        self.panels = [p for p in self.panels if p.title != title]

    def debugger(self) -> Optional[Debugger]:
        """The variable inspector in this set, if there is one.

        Examples
        --------
        >>> from imgui_debugger import DebugTools
        >>> DebugTools.default().debugger().title
        'Debugger'
        """
        for panel in self.panels:
            if isinstance(panel, Debugger):
                return panel
        return None

    def show_all(self) -> None:
        """Open every panel.

        Examples
        --------
        >>> from imgui_debugger import DebugTools
        >>> tools = DebugTools.default()
        >>> tools.show_all()
        >>> all(p.visible for p in tools)
        True
        """
        for panel in self.panels:
            panel.show()

    def hide_all(self) -> None:
        """Close every panel.

        Examples
        --------
        >>> from imgui_debugger import DebugTools
        >>> tools = DebugTools.default()
        >>> tools.hide_all()
        >>> any(p.visible for p in tools)
        False
        """
        for panel in self.panels:
            panel.hide()

    def visible(self) -> Dict[str, bool]:
        """Which panels are open right now, by title.

        Examples
        --------
        >>> from imgui_debugger import DebugTools, StyleEditor
        >>> DebugTools([StyleEditor()]).visible()
        {'Style Editor': True}
        """
        return {p.title: p.visible for p in self.panels}

    def draw_menu_items(self) -> None:
        """Draw one checked entry per panel, inside a menu you already opened.

        Examples
        --------
        >>> from imgui_debugger import DebugTools
        >>> DebugTools.default().draw_menu_items()    # doctest: +SKIP
        """
        for panel in self.panels:
            panel.menu_item()

    def draw_menu(self) -> None:
        """Open a menu named :attr:`menu_label` and draw every entry in it.

        Examples
        --------
        >>> from imgui_debugger import DebugTools
        >>> DebugTools.default().draw_menu()          # doctest: +SKIP
        """
        if imgui.begin_menu(self.menu_label):
            self.draw_menu_items()
            imgui.end_menu()

    def render(self) -> None:
        """Draw every open panel's window, and poll every panel's hotkey.

        Examples
        --------
        >>> from imgui_debugger import DebugTools
        >>> DebugTools.default().render()             # doctest: +SKIP
        """
        for panel in self.panels:
            panel.render_window()

    def load_state(self) -> bool:
        """Restore every panel's saved state from the store.

        Call it once at startup, after building the set.

        Returns
        -------
        bool
            True when a store was set and something was restored.

        Examples
        --------
        >>> from imgui_debugger import ConfigStore, DebugTools
        >>> DebugTools.default(store=ConfigStore("build/cfg")).load_state()
        False
        """
        if self.store is None:
            return False
        saved = self.store.read_state().get("panels", {})
        if not saved:
            return False
        for panel in self.panels:
            state = saved.get(panel.window_id)
            if state:
                panel.set_state(state)
        return True

    def save_state(self) -> bool:
        """Write every panel's state to the store.

        Call it when the app closes, or whenever a panel is toggled.

        Examples
        --------
        >>> from imgui_debugger import ConfigStore, DebugTools
        >>> DebugTools.default(store=ConfigStore("build/cfg")).save_state()  # doctest: +SKIP
        True
        """
        if self.store is None:
            return False
        panels = {p.window_id: p.get_state() for p in self.panels}
        return self.store.update_state(panels=panels)

    def apply_style(self) -> int:
        """Apply the store's saved style to the live imgui style, at startup.

        Returns
        -------
        int
            How many fields were applied; ``0`` without a store or a saved style.

        Examples
        --------
        >>> from imgui_debugger import ConfigStore, DebugTools
        >>> DebugTools.default(store=ConfigStore("build/nope")).apply_style()
        0
        """
        return self.store.apply_style() if self.store is not None else 0
