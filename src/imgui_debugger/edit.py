"""Inline editors that write a leaf value back onto the object it came from.

Examples
--------
>>> from imgui_debugger.edit import can_edit
>>> can_edit(1.5), can_edit((0.2, 0.4, 0.6)), can_edit(object())
(True, True, False)
"""

from __future__ import annotations

from imgui_bundle import imgui

from .theme import Theme, to_vec4

MAX_EDIT_STR = 512


def is_color(value) -> bool:
    """Whether a value looks like an ``(r, g, b[, a])`` float tuple.

    Parameters
    ----------
    value : object
        The value to test.

    Examples
    --------
    >>> from imgui_debugger.edit import is_color
    >>> is_color((0.1, 0.2, 0.3)), is_color((1, 2, 3, 4, 5)), is_color("red")
    (True, False, False)
    """
    if not isinstance(value, (tuple, list)) or len(value) not in (3, 4):
        return False
    return all(isinstance(v, float) and 0.0 <= v <= 1.0 for v in value)


def can_edit(value) -> bool:
    """Whether :func:`edit_value` knows how to render an editor for a value.

    Parameters
    ----------
    value : object
        The value to test.

    Examples
    --------
    >>> from imgui_debugger.edit import can_edit
    >>> can_edit(True), can_edit("path"), can_edit([1, 2])
    (True, True, False)
    """
    if isinstance(value, bool) or isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        return len(value) <= MAX_EDIT_STR
    return is_color(value)


def edit_value(ident: str, value, setter, theme: Theme = None, width: float = -1.0):
    """Draw an editor for one leaf and call ``setter`` when it changes.

    Parameters
    ----------
    ident : str
        Unique imgui id for the widget, usually the row's dotted path.
    value : object
        Current value; its type picks the editor.
    setter : callable
        ``setter(new_value)``, called only on a real change.
    theme : Theme | None
        Palette for the editor frame.
    width : float
        Item width; ``-1`` fills the remaining line.

    Returns
    -------
    bool
        True when the value changed this frame.

    Examples
    --------
    >>> from imgui_debugger.edit import edit_value
    >>> box = {"fs": 9.6}
    >>> edit_value("md.fs", box["fs"], box.__setitem__)   # doctest: +SKIP
    False
    """
    theme = theme or Theme.dark()
    imgui.push_style_color(imgui.Col_.frame_bg, to_vec4(theme.frame_bg))
    imgui.push_style_var(imgui.StyleVar_.frame_rounding, theme.frame_rounding)
    imgui.set_next_item_width(width)
    try:
        changed, new_value = _draw_editor(ident, value)
    finally:
        imgui.pop_style_var()
        imgui.pop_style_color()
    if changed:
        try:
            setter(new_value)
        except Exception:
            return False
    return changed


def _draw_editor(ident: str, value):
    """Draw the type-appropriate imgui input and return ``(changed, value)``.

    Examples
    --------
    >>> from imgui_debugger.edit import _draw_editor
    >>> _draw_editor("##n", 3)          # doctest: +SKIP
    (False, 3)
    """
    label = f"##{ident}"
    if isinstance(value, bool):
        return imgui.checkbox(label, value)
    if is_color(value):
        rgba = list(value) + ([1.0] if len(value) == 3 else [])
        changed, out = imgui.color_edit4(label, imgui.ImVec4(*rgba))
        new = (out.x, out.y, out.z) if len(value) == 3 else (out.x, out.y, out.z, out.w)
        return changed, type(value)(new)
    if isinstance(value, int):
        return imgui.input_int(label, value)
    if isinstance(value, float):
        return imgui.input_float(label, value, 0.0, 0.0, "%.6g")
    return imgui.input_text(label, value)
