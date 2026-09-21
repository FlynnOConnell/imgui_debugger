"""The collapsible tree: one scope header per root, one row per value below it.

Examples
--------
>>> from imgui_debugger.tree import TreeStyle
>>> TreeStyle(filter="fs").filter
'fs'
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from imgui_bundle import imgui

from .edit import can_edit, edit_value
from .format import fmt_error, fmt_value, type_label
from .scopes import Child, Scope, children_of, has_children
from .search import filter_children, matches
from .theme import Theme, to_vec4

ROLE_COLORS = {
    "attr": "name",
    "prop": "prop",
    "class": "cls",
    "item": "name",
    "index": "index",
    "local": "local",
    "global": "glob",
    "runtime": "runtime",
    "error": "error",
}


@dataclass(frozen=True)
class TreeStyle:
    """Everything the row renderer needs besides the rows themselves.

    Parameters
    ----------
    theme : Theme
        Palette.
    filter : str
        Case-insensitive filter; empty shows everything.
    editable : bool
        Draw inline editors for writable leaves.
    private : bool
        Expand ``_name`` attributes of nested values.
    properties : bool
        Expand ``property`` descriptors of nested values.
    max_depth : int
        Deepest level expanded before a row is shown as a summary only.
    max_items : int
        Rows rendered per container before a "+N more" line.
    value_col : float
        Pixel column the value is drawn at; ``0`` packs it after the name.
    force_open : bool | None
        For one frame, expand (True) or collapse (False) every node.

    Examples
    --------
    >>> from imgui_debugger.tree import TreeStyle
    >>> from imgui_debugger import Theme
    >>> TreeStyle(theme=Theme.light(), value_col=220.0).value_col
    220.0
    """

    theme: Theme = field(default_factory=Theme.dark)
    filter: str = ""
    editable: bool = True
    private: bool = False
    properties: bool = True
    max_depth: int = 8
    max_items: int = 200
    value_col: float = 0.0
    force_open: Optional[bool] = None


def role_color(style: TreeStyle, kind: str):
    """The theme color a row of the given kind is drawn in.

    Parameters
    ----------
    style : TreeStyle
        Active style.
    kind : str
        A :class:`~imgui_debugger.scopes.Child` kind, or a theme field name.

    Examples
    --------
    >>> from imgui_debugger.tree import TreeStyle, role_color
    >>> role_color(TreeStyle(), "index") == TreeStyle().theme.index
    True
    """
    name = ROLE_COLORS.get(kind, kind)
    return getattr(style.theme, name, style.theme.name)


def draw_value(child: Child, path: str, style: TreeStyle) -> None:
    """Draw a leaf's value, as an editor when it is writable and editable.

    Parameters
    ----------
    child : Child
        The row.
    path : str
        Dotted path, used as the imgui id.
    style : TreeStyle
        Active style.

    Examples
    --------
    >>> from imgui_debugger.scopes import Child
    >>> from imgui_debugger.tree import TreeStyle, draw_value
    >>> draw_value(Child("fs", 9.6), "arr.fs", TreeStyle())   # doctest: +SKIP
    """
    if style.value_col > 0:
        imgui.same_line(style.value_col)
    else:
        imgui.same_line(spacing=16)
    if child.kind == "error":
        imgui.text_colored(to_vec4(style.theme.error), fmt_error(child.value))
        return
    if style.editable and child.editable and can_edit(child.value):
        edit_value(path, child.value, child.setter, style.theme)
        return
    imgui.text_colored(to_vec4(style.theme.value), fmt_value(child.value))
    if imgui.is_item_hovered():
        imgui.set_tooltip(f"{path}\n{type_label(child.value)}")


def draw_child(child: Child, prefix: str, depth: int, style: TreeStyle) -> None:
    """Draw one row, recursing into its children when it expands.

    Parameters
    ----------
    child : Child
        The row.
    prefix : str
        Dotted path of the parent, ``""`` at a scope root.
    depth : int
        Current depth, compared against ``style.max_depth``.
    style : TreeStyle
        Active style.

    Examples
    --------
    >>> from imgui_debugger.scopes import Child
    >>> from imgui_debugger.tree import TreeStyle, draw_child
    >>> draw_child(Child("md", {"fs": 9.6}), "", 0, TreeStyle())   # doctest: +SKIP
    """
    path = f"{prefix}{child.name}" if child.name.startswith("[") else f"{prefix}.{child.name}"
    path = path.lstrip(".")
    color = role_color(style, child.kind)
    expandable = (
        child.kind != "error"
        and depth < style.max_depth
        and has_children(child.value, style.private, style.properties)
    )

    if not expandable:
        imgui.text_colored(to_vec4(color), child.name)
        draw_value(child, path, style)
        return

    if style.force_open is not None:
        imgui.set_next_item_open(style.force_open)
    imgui.push_style_color(imgui.Col_.text, to_vec4(style.theme.node))
    open_ = imgui.tree_node(f"{child.name}##{path}")
    imgui.pop_style_color()
    if imgui.is_item_hovered():
        imgui.set_tooltip(f"{path}\n{type_label(child.value)}")
    imgui.same_line(style.value_col if style.value_col > 0 else 0.0)
    imgui.text_colored(to_vec4(style.theme.text_dim), type_label(child.value))
    if not open_:
        return
    try:
        rows = children_of(child.value, style.private, style.properties, style.max_items + 1)
    except Exception as exc:
        imgui.text_colored(to_vec4(style.theme.error), fmt_error(exc))
        imgui.tree_pop()
        return
    draw_children(rows, path, depth + 1, style)
    imgui.tree_pop()


def draw_children(rows, prefix: str, depth: int, style: TreeStyle) -> None:
    """Draw a list of rows, filtered and capped at ``style.max_items``.

    Parameters
    ----------
    rows : list[Child]
        Rows to draw.
    prefix : str
        Dotted path of the parent.
    depth : int
        Current depth.
    style : TreeStyle
        Active style.

    Examples
    --------
    >>> from imgui_debugger.scopes import Child
    >>> from imgui_debugger.tree import TreeStyle, draw_children
    >>> draw_children([Child("n", 1)], "cfg", 1, TreeStyle())   # doctest: +SKIP
    """
    shown = filter_children(rows, style.filter)
    for child in shown[: style.max_items]:
        draw_child(child, prefix, depth, style)
    hidden = len(shown) - style.max_items
    if hidden > 0:
        imgui.text_disabled(f"... +{hidden} more")


def draw_scope(scope: Scope, style: TreeStyle) -> str:
    """Draw one scope header and its rows, returning the scope name.

    Parameters
    ----------
    scope : Scope
        The scope to draw.
    style : TreeStyle
        Active style.

    Returns
    -------
    str
        ``scope.name``, so a caller can key per-scope state off the return.

    Examples
    --------
    >>> from imgui_debugger.scopes import Scope, Child
    >>> from imgui_debugger.tree import TreeStyle, draw_scope
    >>> s = Scope("counters", lambda: [Child("frames", 1)])
    >>> draw_scope(s, TreeStyle())      # doctest: +SKIP
    'counters'
    """
    try:
        rows = scope.children()
    except Exception as exc:
        imgui.text_colored(to_vec4(style.theme.error), f"{scope.name}: {fmt_error(exc)}")
        return scope.name
    shown = filter_children(rows, style.filter)
    if style.filter and not shown:
        return scope.name

    if style.force_open is not None:
        imgui.set_next_item_open(style.force_open)
    elif style.filter:
        imgui.set_next_item_open(True)
    else:
        imgui.set_next_item_open(scope.start_open, imgui.Cond_.first_use_ever)
    imgui.push_style_color(imgui.Col_.text, to_vec4(role_color(style, scope.role)))
    open_ = imgui.collapsing_header(f"{scope.name}##scope_{scope.name}")
    imgui.pop_style_color()
    if scope.hint and imgui.is_item_hovered():
        imgui.set_tooltip(scope.hint)
    imgui.same_line()
    imgui.text_disabled(f"({len(shown)})")
    if open_:
        imgui.indent()
        draw_children(shown, scope.name, 1, style)
        imgui.unindent()
    return scope.name


def row_matches(child: Child, text: str) -> bool:
    """Whether one row survives the filter, children included.

    Parameters
    ----------
    child : Child
        The row.
    text : str
        Filter text.

    Examples
    --------
    >>> from imgui_debugger.scopes import Child
    >>> from imgui_debugger.tree import row_matches
    >>> row_matches(Child("md", {"fs": 9.6}), "fs")
    True
    """
    return matches(child.name, child.value, text)
