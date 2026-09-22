"""The :class:`Debugger` widget and its configuration.

Examples
--------
>>> from imgui_debugger import attach
>>> class W:
...     def __init__(self):
...         self.visible = True
>>> dbg = attach(W(), show_frame=False, show_runtime=False)
>>> [s.name for s in dbg.scopes()]
['instance', 'properties', 'class']
"""

from __future__ import annotations

import functools
import sys
from dataclasses import dataclass
from typing import Any, List, Optional, Sequence, Tuple

from imgui_bundle import imgui, imgui_ctx

from .panel import Panel, PanelConfig
from .scopes import Scope, Watch, frame_scopes, object_scopes, runtime_scope
from .search import clear_cache
from .theme import to_vec4
from .tree import TreeStyle, draw_scope


@dataclass
class DebuggerConfig(PanelConfig):
    """What the debugger inspects and how it draws it.

    Parameters
    ----------
    target : object | None
        The object whose scopes are shown first, usually the widget being
        debugged.
    private : bool
        Show ``_name`` attributes.
    properties : bool
        Show the ``properties`` scope and expand properties of nested values.
    class_attrs : bool
        Show the ``class`` scope.
    editable : bool
        Draw inline editors for writable leaves.
    show_frame : bool
        Show ``locals`` and ``globals`` from the captured call frame.
    show_runtime : bool
        Show the live ``imgui`` scope.
    max_depth : int
        Deepest level the tree expands.
    max_items : int
        Rows rendered per container.
    value_col : float
        Pixel column values are aligned at; ``0`` packs them after the name.
    show_toolbar : bool
        Draw the filter box and toggles above the tree.
    show_title : bool
        Draw the title line inside the panel body.
    os_window_title : str
        OS window title in one-shot mode; the panel title when empty.
    resizable : bool
        Whether the one-shot OS window can be resized.
    ini_path : str | None
        Where hello_imgui saves the layout in one-shot mode.
    assets_folder : str | None
        Folder providing the icon font; unset never overrides a host app's.

    Every :class:`~imgui_debugger.panel.PanelConfig` field is also accepted.

    Examples
    --------
    >>> from imgui_debugger import DebuggerConfig, Theme
    >>> cfg = DebuggerConfig(title="Voltage tab", theme=Theme.light(), private=True)
    >>> cfg.title, cfg.private
    ('Voltage tab', True)
    """

    target: Any = None
    title: str = "Debugger"
    window_size: Tuple[int, int] = (520, 780)
    private: bool = False
    properties: bool = True
    class_attrs: bool = True
    editable: bool = True
    show_frame: bool = True
    show_runtime: bool = True
    max_depth: int = 8
    max_items: int = 200
    value_col: float = 0.0
    show_toolbar: bool = True
    show_title: bool = True
    os_window_title: str = ""
    resizable: bool = True
    ini_path: Optional[str] = None
    assets_folder: Optional[str] = None


class Debugger(Panel):
    """A live variable inspector drawn inside any imgui frame.

    Parameters
    ----------
    config : DebuggerConfig | None
        What to inspect and how. Defaults to an empty debugger you add
        watches to.
    frame_depth : int
        Which stack frame to capture for the ``locals`` / ``globals`` scopes;
        ``1`` is the caller of the constructor.

    Examples
    --------
    >>> from imgui_debugger import Debugger, DebuggerConfig
    >>> class Widget:
    ...     def __init__(self):
    ...         self.open = True
    >>> cfg = DebuggerConfig(target=Widget(), show_frame=False, show_runtime=False)
    >>> dbg = Debugger(cfg)
    >>> dbg.watch("counters", {"frames": 0})
    >>> [s.name for s in dbg.scopes()][-1]
    'counters'
    >>> dbg.render()                     # doctest: +SKIP
    """

    config_class = DebuggerConfig
    state_fields = (
        "private",
        "properties",
        "class_attrs",
        "editable",
        "show_frame",
        "show_runtime",
        "max_depth",
        "max_items",
        "value_col",
        "show_toolbar",
    )

    def __init__(self, config: Optional[DebuggerConfig] = None, frame_depth: int = 1):
        super().__init__(config or DebuggerConfig())
        self.filter = ""
        self._watches: List[Watch] = []
        self._frame = None
        self._force_open: Optional[bool] = None
        self._focus_filter = False
        if self.config.show_frame:
            self.capture(frame_depth + 1)

    @property
    def target(self):
        """The object whose scopes are listed first.

        Examples
        --------
        >>> from imgui_debugger import attach
        >>> attach({"fs": 9.6}).target
        {'fs': 9.6}
        """
        return self.config.target

    def set_target(self, target) -> None:
        """Point the debugger at another object.

        Parameters
        ----------
        target : object
            The new object to inspect.

        Examples
        --------
        >>> from imgui_debugger import attach
        >>> dbg = attach({"a": 1})
        >>> dbg.set_target({"b": 2})
        >>> dbg.target
        {'b': 2}
        """
        self.config.target = target

    def capture(self, depth: int = 1) -> None:
        """Capture a stack frame for the ``locals`` / ``globals`` scopes.

        Call it from inside the function you want to watch — a widget's draw
        method, say — to follow that function's locals live.

        Parameters
        ----------
        depth : int
            ``1`` is the caller of :meth:`capture`.

        Examples
        --------
        >>> from imgui_debugger import Debugger
        >>> dbg = Debugger()
        >>> rows = 12
        >>> dbg.capture()
        >>> any(s.name == "locals" for s in dbg.scopes())
        True
        """
        try:
            self._frame = sys._getframe(depth)
        except ValueError:
            self._frame = None

    def watch(self, name: str, source, role: str = "name", start_open: bool = True) -> None:
        """Add an extra scope for a value or a callable re-read every frame.

        Parameters
        ----------
        name : str
            Scope header text; adding the same name twice replaces it.
        source : object | callable
            The value, or a zero-argument callable returning it.
        role : str
            Theme color role for its rows.
        start_open : bool
            Whether the header starts expanded.

        Examples
        --------
        >>> from imgui_debugger import Debugger, DebuggerConfig
        >>> dbg = Debugger(DebuggerConfig(show_frame=False, show_runtime=False))
        >>> state = {"frames": 0}
        >>> dbg.watch("state", state)
        >>> dbg.watch("fps", lambda: {"now": 60.0}, role="runtime")
        >>> [s.name for s in dbg.scopes()]
        ['state', 'fps']
        """
        self.unwatch(name)
        self._watches.append(Watch(name, source, role, start_open, self.config.private))

    def unwatch(self, name: str) -> None:
        """Remove a watch added by :meth:`watch`.

        Parameters
        ----------
        name : str
            The watch's scope name.

        Examples
        --------
        >>> from imgui_debugger import Debugger, DebuggerConfig
        >>> dbg = Debugger(DebuggerConfig(show_frame=False, show_runtime=False))
        >>> dbg.watch("state", {"a": 1})
        >>> dbg.unwatch("state")
        >>> dbg.scopes()
        []
        """
        self._watches = [w for w in self._watches if w.name != name]

    def scopes(self) -> List[Scope]:
        """Every scope the tree draws this frame, in display order.

        Examples
        --------
        >>> from imgui_debugger import attach
        >>> dbg = attach({"fs": 9.6}, show_frame=False, show_runtime=False)
        >>> [s.name for s in dbg.scopes()]
        ['instance', 'properties', 'class']
        """
        cfg = self.config
        out: List[Scope] = []
        if cfg.target is not None:
            out += object_scopes(cfg.target, cfg.private, cfg.properties, cfg.class_attrs)
        out += [w.scope() for w in self._watches]
        if cfg.show_frame and self._frame is not None:
            out += frame_scopes(self._frame, cfg.private)
        if cfg.show_runtime:
            out.append(runtime_scope())
        return out

    def style(self) -> TreeStyle:
        """The :class:`~imgui_debugger.tree.TreeStyle` for this frame.

        Examples
        --------
        >>> from imgui_debugger import Debugger, DebuggerConfig
        >>> Debugger(DebuggerConfig(value_col=200.0)).style().value_col
        200.0
        """
        cfg = self.config
        return TreeStyle(
            theme=cfg.theme,
            filter=self.filter,
            editable=cfg.editable,
            private=cfg.private,
            properties=cfg.properties,
            max_depth=cfg.max_depth,
            max_items=cfg.max_items,
            value_col=cfg.value_col,
            force_open=self._force_open,
        )

    def expand_all(self) -> None:
        """Expand every node on the next frame.

        Examples
        --------
        >>> from imgui_debugger import Debugger
        >>> dbg = Debugger()
        >>> dbg.expand_all()
        """
        self._force_open = True

    def collapse_all(self) -> None:
        """Collapse every node on the next frame.

        Examples
        --------
        >>> from imgui_debugger import Debugger
        >>> dbg = Debugger()
        >>> dbg.collapse_all()
        """
        self._force_open = False

    def set_filter(self, text: str) -> None:
        """Set the filter text and drop the stale match cache.

        Parameters
        ----------
        text : str
            Case-insensitive filter over names and leaf values.

        Examples
        --------
        >>> from imgui_debugger import Debugger
        >>> dbg = Debugger()
        >>> dbg.set_filter("fs")
        >>> dbg.filter
        'fs'
        """
        self.filter = text
        clear_cache()

    def render(self) -> None:
        """Draw the toolbar and the whole tree at the current cursor.

        Call it inside your own frame, e.g. from a dock space window or a
        pipeline widget's config panel.

        Examples
        --------
        >>> from imgui_debugger import attach
        >>> dbg = attach(object())
        >>> dbg.render()                 # doctest: +SKIP
        """
        if self.config.show_toolbar:
            self.draw_toolbar()
        self.draw_tree()
        self._force_open = None

    def draw_toolbar(self) -> None:
        """Draw the title, filter box, expand/collapse and the display toggles.

        Examples
        --------
        >>> from imgui_debugger import attach
        >>> attach(object()).draw_toolbar()     # doctest: +SKIP
        """
        cfg = self.config
        if cfg.show_title and cfg.title:
            imgui.text_colored(to_vec4(cfg.theme.accent), cfg.title)
            if cfg.target is not None and imgui.is_item_hovered():
                imgui.set_tooltip(f"{type(cfg.target).__name__} at 0x{id(cfg.target):x}")
            imgui.same_line()
        imgui.text_disabled(f"{len(self.scopes())} scopes")

        if self._focus_filter:
            imgui.set_keyboard_focus_here()
            self._focus_filter = False
        imgui.set_next_item_width(-1)
        changed, text = imgui.input_text_with_hint(
            "##debug_filter", "filter by name or value...", self.filter
        )
        if changed:
            self.set_filter(text)

        if imgui.small_button("expand"):
            self.expand_all()
        imgui.same_line()
        if imgui.small_button("collapse"):
            self.collapse_all()
        imgui.same_line()
        _, cfg.private = imgui.checkbox("private", cfg.private)
        imgui.same_line()
        _, cfg.editable = imgui.checkbox("edit", cfg.editable)
        imgui.separator()

    def draw_tree(self) -> None:
        """Draw every scope in a scrollable child, without the toolbar.

        Examples
        --------
        >>> from imgui_debugger import attach
        >>> attach(object()).draw_tree()        # doctest: +SKIP
        """
        style = self.style()
        with imgui_ctx.begin_child("##debug_tree"):
            imgui.push_style_var(imgui.StyleVar_.item_spacing, imgui.ImVec2(8, 4))
            try:
                for scope in self.scopes():
                    draw_scope(scope, style)
            finally:
                imgui.pop_style_var()

    def focus_filter(self) -> None:
        """Put the keyboard cursor in the filter box on the next frame.

        Examples
        --------
        >>> from imgui_debugger import Debugger
        >>> dbg = Debugger()
        >>> dbg.focus_filter()
        """
        self._focus_filter = True


def attach(target=None, config: Optional[DebuggerConfig] = None, **kwargs) -> Debugger:
    """Build a :class:`Debugger` for one object in a single call.

    Parameters
    ----------
    target : object | None
        The object to inspect.
    config : DebuggerConfig | None
        A prebuilt config; ``target`` and ``kwargs`` override its fields.
    **kwargs
        Any :class:`DebuggerConfig` field.

    Returns
    -------
    Debugger
        Ready to render; keep it on your widget, not per frame.

    Examples
    --------
    >>> from imgui_debugger import attach
    >>> class Tab:
    ...     def __init__(self):
    ...         self.selected = 2
    >>> dbg = attach(Tab(), title="Voltage tab", show_runtime=False)
    >>> dbg.config.title
    'Voltage tab'
    >>> dbg.render_window()          # doctest: +SKIP
    """
    cfg = config or DebuggerConfig()
    if target is not None:
        cfg.target = target
    for key, value in kwargs.items():
        if not hasattr(cfg, key):
            raise TypeError(f"DebuggerConfig has no field {key!r}")
        setattr(cfg, key, value)
    return Debugger(cfg, frame_depth=2)


def watch_all(target, names: Sequence[str], **kwargs) -> Debugger:
    """Attach to an object and add one watch per named attribute.

    Parameters
    ----------
    target : object
        The object to inspect.
    names : Sequence[str]
        Attribute names to promote to top-level scopes.
    **kwargs
        Any :class:`DebuggerConfig` field.

    Returns
    -------
    Debugger
        With one extra scope per name, re-read every frame.

    Examples
    --------
    >>> from imgui_debugger import watch_all
    >>> class Viewer:
    ...     def __init__(self):
    ...         self.metadata = {"fs": 9.6}
    ...         self.indices = {"t": 0}
    >>> dbg = watch_all(Viewer(), ["metadata", "indices"],
    ...                 show_frame=False, show_runtime=False)
    >>> [s.name for s in dbg.scopes()][-2:]
    ['metadata', 'indices']
    """
    dbg = attach(target, **kwargs)
    for name in names:
        dbg.watch(name, functools.partial(getattr, target, name))
    return dbg
