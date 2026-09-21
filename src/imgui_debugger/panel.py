"""The one surface every tool in this package shares.

A panel owns its visibility, draws its body with :meth:`Panel.render`, mounts on
a menu with :meth:`Panel.menu_item`, and opens its own window with
:meth:`Panel.render_window`. Nothing needs the imgui demo window.

Examples
--------
>>> from imgui_debugger import PanelConfig, StyleEditor
>>> editor = StyleEditor(PanelConfig(title="Theme", visible=False))
>>> editor.visible, editor.title
(False, 'Theme')
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Tuple

from imgui_bundle import imgui

from .theme import Theme


@dataclass(frozen=True)
class Hotkey:
    """A key plus modifiers that toggles a panel, and its own menu text.

    Parameters
    ----------
    key : imgui.Key
        The key, e.g. ``imgui.Key.f12``.
    ctrl, shift, alt : bool
        Modifiers that must be held.

    Examples
    --------
    >>> from imgui_bundle import imgui
    >>> from imgui_debugger import Hotkey
    >>> Hotkey(imgui.Key.f12).text
    'F12'
    >>> Hotkey(imgui.Key.d, ctrl=True, shift=True).text
    'Ctrl+Shift+D'
    """

    key: object
    ctrl: bool = False
    shift: bool = False
    alt: bool = False

    @property
    def text(self) -> str:
        """The shortcut written the way a menu shows it.

        Examples
        --------
        >>> from imgui_bundle import imgui
        >>> from imgui_debugger import Hotkey
        >>> Hotkey(imgui.Key.f1, alt=True).text
        'Alt+F1'
        """
        parts = []
        if self.ctrl:
            parts.append("Ctrl")
        if self.shift:
            parts.append("Shift")
        if self.alt:
            parts.append("Alt")
        parts.append(imgui.get_key_name(self.key))
        return "+".join(parts)

    def pressed(self) -> bool:
        """True on the frame the combination is pressed, inside a live frame.

        Examples
        --------
        >>> from imgui_bundle import imgui
        >>> from imgui_debugger import Hotkey
        >>> Hotkey(imgui.Key.f12).pressed()      # doctest: +SKIP
        False
        """
        io = imgui.get_io()
        if io.key_ctrl != self.ctrl or io.key_shift != self.shift or io.key_alt != self.alt:
            return False
        return imgui.is_key_pressed(self.key)


@dataclass
class PanelConfig:
    """Window, menu and theme settings every panel understands.

    Parameters
    ----------
    title : str
        Window title and default menu label.
    visible : bool
        Whether the panel starts open.
    window_id : str
        Stable imgui id suffix, so a renamed title keeps its saved layout;
        the class name when empty.
    window_size : tuple[int, int]
        First-use size; ``(0, 0)`` lets imgui size it to the content.
    window_pos : tuple[int, int] | None
        First-use position; imgui decides when None.
    window_flags : int
        ``imgui.WindowFlags_`` bits for the panel's own window.
    closable : bool
        Draw the window's close button and clear ``visible`` when it is used.
    shortcut : str
        Menu shortcut text; the hotkey's own text when empty.
    hotkey : Hotkey | None
        Key combination that toggles the panel.
    theme : Theme
        Palette for whatever the panel draws itself.

    Examples
    --------
    >>> from imgui_bundle import imgui
    >>> from imgui_debugger import Hotkey, PanelConfig
    >>> cfg = PanelConfig(title="Metrics", hotkey=Hotkey(imgui.Key.f11))
    >>> cfg.title, cfg.hotkey.text
    ('Metrics', 'F11')
    """

    title: str = "Panel"
    visible: bool = True
    window_id: str = ""
    window_size: Tuple[int, int] = (0, 0)
    window_pos: Optional[Tuple[int, int]] = None
    window_flags: int = 0
    closable: bool = True
    shortcut: str = ""
    hotkey: Optional[Hotkey] = None
    theme: Theme = field(default_factory=Theme.dark)


class Panel:
    """Base for every tool here: visibility, a menu entry and its own window.

    Subclasses implement :meth:`render` and nothing else.

    Parameters
    ----------
    config : PanelConfig | None
        Window, menu and theme settings.

    Examples
    --------
    >>> from imgui_debugger import Panel, PanelConfig
    >>> class Counter(Panel):
    ...     config_class = PanelConfig
    ...     def render(self):
    ...         pass
    >>> panel = Counter(PanelConfig(title="Counter", visible=False))
    >>> panel.title, panel.visible
    ('Counter', False)
    >>> panel.toggle()
    >>> panel.visible
    True
    """

    config_class = PanelConfig

    def __init__(self, config: Optional[PanelConfig] = None):
        self.config = config or self.config_class()
        self.visible = self.config.visible

    @property
    def title(self) -> str:
        """The panel's window title and default menu label.

        Examples
        --------
        >>> from imgui_debugger import StyleEditor
        >>> StyleEditor().title
        'Style Editor'
        """
        return self.config.title

    @property
    def theme(self) -> Theme:
        """The palette the panel draws itself with.

        Examples
        --------
        >>> from imgui_debugger import StyleEditor
        >>> StyleEditor().theme.frame_rounding
        4.0
        """
        return self.config.theme

    @property
    def window_id(self) -> str:
        """The full imgui window label, title plus a stable id suffix.

        Examples
        --------
        >>> from imgui_debugger import StyleEditor, StyleEditorConfig
        >>> StyleEditor(StyleEditorConfig(window_id="style")).window_id
        'Style Editor##imgui_debugger_style'
        """
        ident = self.config.window_id or type(self).__name__
        return f"{self.config.title}##imgui_debugger_{ident}"

    def show(self) -> None:
        """Open the panel.

        Examples
        --------
        >>> from imgui_debugger import StyleEditor
        >>> p = StyleEditor()
        >>> p.hide()
        >>> p.show()
        >>> p.visible
        True
        """
        self.visible = True

    def hide(self) -> None:
        """Close the panel.

        Examples
        --------
        >>> from imgui_debugger import StyleEditor
        >>> p = StyleEditor()
        >>> p.hide()
        >>> p.visible
        False
        """
        self.visible = False

    def toggle(self) -> None:
        """Flip :attr:`visible`.

        Examples
        --------
        >>> from imgui_debugger import StyleEditor
        >>> p = StyleEditor()
        >>> p.toggle()
        >>> p.visible
        False
        """
        self.visible = not self.visible

    def menu_item(self, label: str = "", shortcut: str = "") -> bool:
        """Draw a checked menu entry bound to :attr:`visible`, inside your menu.

        Parameters
        ----------
        label : str
            Entry text; the config title when empty.
        shortcut : str
            Shortcut text; the config shortcut, else the hotkey's text.

        Returns
        -------
        bool
            True on the frame the entry was clicked.

        Examples
        --------
        >>> from imgui_debugger import StyleEditor
        >>> StyleEditor().menu_item("Style", "Ctrl+,")    # doctest: +SKIP
        False
        """
        text = shortcut or self.config.shortcut
        if not text and self.config.hotkey is not None:
            text = self.config.hotkey.text
        clicked, self.visible = imgui.menu_item(
            label or self.config.title, text, self.visible
        )
        return clicked

    def poll_hotkey(self) -> bool:
        """Toggle the panel when its hotkey is pressed, returning whether it was.

        Called by :meth:`render_window` every frame, open or not, so the hotkey
        reopens a closed panel.

        Examples
        --------
        >>> from imgui_debugger import StyleEditor
        >>> StyleEditor().poll_hotkey()                   # doctest: +SKIP
        False
        """
        if self.config.hotkey is None:
            return False
        if not self.config.hotkey.pressed():
            return False
        self.toggle()
        return True

    def render(self) -> None:
        """Draw the panel body at the current cursor, with no window around it.

        Examples
        --------
        >>> from imgui_debugger import StyleEditor
        >>> StyleEditor().render()                        # doctest: +SKIP
        """
        raise NotImplementedError(f"{type(self).__name__} does not implement render()")

    def render_window(self, flags: int = 0) -> bool:
        """Draw the panel in its own window, honoring :attr:`visible`.

        Parameters
        ----------
        flags : int
            Extra ``imgui.WindowFlags_`` bits, added to the config's.

        Returns
        -------
        bool
            True when the body was drawn this frame.

        Examples
        --------
        >>> from imgui_debugger import StyleEditor
        >>> StyleEditor().render_window()                 # doctest: +SKIP
        True
        """
        self.poll_hotkey()
        if not self.visible:
            return False
        cfg = self.config
        if cfg.window_size and any(cfg.window_size):
            imgui.set_next_window_size(
                imgui.ImVec2(*cfg.window_size), imgui.Cond_.first_use_ever
            )
        if cfg.window_pos is not None:
            imgui.set_next_window_pos(
                imgui.ImVec2(*cfg.window_pos), imgui.Cond_.first_use_ever
            )
        expanded, opened = imgui.begin(
            self.window_id, True if cfg.closable else None, cfg.window_flags | flags
        )
        if cfg.closable and opened is not None:
            self.visible = opened
        if expanded:
            self.render()
        imgui.end()
        return expanded
