"""The keybinds and path popups, as draw functions and as panels.

``draw_keybinds_popup`` existed in both ``masknmf.visualization.imgui.panels``
and ``mbo_utilities.gui.imgui.panels``; this is the one copy. The
:class:`KeybindsPanel` wrapper gives it the standard panel surface so it can go
on a menu beside the debug tools.

Examples
--------
>>> from imgui_debugger import KeybindsPanel
>>> panel = KeybindsPanel(bindings=[("t", "trace the selected ROI")])
>>> panel.title
'Keybinds'
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence, Tuple

from imgui_bundle import imgui

from .panel import Panel, PanelConfig
from .theme import Theme, to_vec4
from .widgets import close_button, em, help_mark, popup


def draw_keybinds_popup(
    bindings: Sequence[tuple],
    is_open: bool,
    title: str = "Keybinds",
    theme: Optional[Theme] = None,
) -> bool:
    """A key reference window built from ``(key, action)`` pairs.

    Parameters
    ----------
    bindings : Sequence[tuple]
        ``(key, action)`` pairs, one row each.
    is_open : bool
        Current open state; False draws nothing.
    title : str
        Window title.
    theme : Theme | None
        Palette for the key column.

    Returns
    -------
    bool
        The new open state.

    Examples
    --------
    >>> from imgui_debugger import draw_keybinds_popup
    >>> draw_keybinds_popup([("t", "trace")], False)
    False
    """
    if not is_open:
        return False
    theme = theme or Theme.dark()
    opened, is_open = popup(title, is_open, theme)
    if opened:
        flags = imgui.TableFlags_.row_bg | imgui.TableFlags_.borders_inner_h
        if imgui.begin_table("##keybinds-table", 2, flags):
            imgui.table_setup_column("key", imgui.TableColumnFlags_.width_fixed, em(10))
            imgui.table_setup_column("action")
            for key, action in bindings:
                imgui.table_next_row()
                imgui.table_next_column()
                imgui.text_colored(to_vec4(theme.warn), key)
                imgui.table_next_column()
                imgui.text(action)
            imgui.end_table()
        if close_button():
            is_open = False
    imgui.end()
    return is_open


def draw_path_popup(
    title: str,
    is_open: bool,
    path: str,
    hint: str,
    action: str,
    browse: Optional[Callable[[], None]] = None,
    note: str = "",
    theme: Optional[Theme] = None,
) -> Tuple[bool, str, bool]:
    """A path field with an optional browse button and an action button.

    Enter in the field counts as the action.

    Parameters
    ----------
    title : str
        Window title.
    is_open : bool
        Current open state; False draws nothing.
    path : str
        Current text.
    hint : str
        Placeholder shown while the field is empty.
    action : str
        Label of the confirm button.
    browse : Callable[[], None] | None
        Starts a native dialog whose pick the caller writes back into ``path``.
    note : str
        Wrapped dim text under the field.
    theme : Theme | None
        Palette.

    Returns
    -------
    tuple[bool, str, bool]
        ``(still_open, path, action_pressed)``.

    Examples
    --------
    >>> from imgui_debugger import draw_path_popup
    >>> draw_path_popup("Open", False, "", "path to a file", "Open")
    (False, '', False)
    """
    if not is_open:
        return False, path, False
    theme = theme or Theme.dark()
    opened, is_open = popup(title, is_open, theme)
    confirmed = False
    if opened:
        imgui.set_next_item_width(em(26))
        entered, path = imgui.input_text_with_hint(
            "##path", hint, path, imgui.InputTextFlags_.enter_returns_true
        )
        if browse is not None:
            imgui.same_line(0, em(0.4))
            if imgui.button("browse"):
                browse()
            help_mark(
                "native file dialog on the machine running python; "
                "on a remote kernel type the path"
            )
        if note:
            imgui.push_text_wrap_pos(em(32))
            imgui.text_disabled(note)
            imgui.pop_text_wrap_pos()
        imgui.dummy(imgui.ImVec2(0, em(0.3)))
        if imgui.button(action, imgui.ImVec2(em(6), 0)) or entered:
            confirmed = bool(path.strip())
        imgui.same_line(0, em(0.6))
        if imgui.button("Close", imgui.ImVec2(em(6), 0)):
            is_open = False
    imgui.end()
    return is_open, path, confirmed


@dataclass
class KeybindsConfig(PanelConfig):
    """Panel settings plus the key table's rows.

    Parameters
    ----------
    bindings : Sequence[tuple]
        ``(key, action)`` pairs.

    Examples
    --------
    >>> from imgui_debugger import KeybindsConfig
    >>> KeybindsConfig(bindings=[("t", "trace")]).bindings[0]
    ('t', 'trace')
    """

    title: str = "Keybinds"
    visible: bool = False
    bindings: Sequence[tuple] = field(default_factory=tuple)


class KeybindsPanel(Panel):
    """The key reference as a panel, so it mounts on a menu like the rest.

    Parameters
    ----------
    config : KeybindsConfig | None
        Panel settings and the bindings.
    bindings : Sequence[tuple] | None
        Shorthand for ``KeybindsConfig(bindings=...)``.

    Examples
    --------
    >>> from imgui_debugger import KeybindsPanel
    >>> panel = KeybindsPanel(bindings=[("t", "trace"), ("d", "delete")])
    >>> len(panel.config.bindings)
    2
    >>> panel.render_window()        # doctest: +SKIP
    """

    config_class = KeybindsConfig

    def __init__(self, config: Optional[KeybindsConfig] = None, bindings=None):
        super().__init__(config or KeybindsConfig())
        if bindings is not None:
            self.config.bindings = bindings

    def render(self) -> None:
        """Draw the key table at the current cursor.

        Examples
        --------
        >>> from imgui_debugger import KeybindsPanel
        >>> KeybindsPanel().render()     # doctest: +SKIP
        """
        flags = imgui.TableFlags_.row_bg | imgui.TableFlags_.borders_inner_h
        if not imgui.begin_table("##keybinds-table", 2, flags):
            return
        imgui.table_setup_column("key", imgui.TableColumnFlags_.width_fixed, em(10))
        imgui.table_setup_column("action")
        for key, action in self.config.bindings:
            imgui.table_next_row()
            imgui.table_next_column()
            imgui.text_colored(to_vec4(self.theme.warn), key)
            imgui.table_next_column()
            imgui.text(action)
        imgui.end_table()
