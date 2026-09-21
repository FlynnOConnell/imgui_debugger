"""Colors and rounding knobs for the debugger tree.

Examples
--------
>>> from imgui_debugger import Theme
>>> Theme.dark().replace(value=(1.0, 1.0, 1.0, 1.0)).value
(1.0, 1.0, 1.0, 1.0)
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Tuple

from imgui_bundle import imgui

Color = Tuple[float, float, float, float]


def to_vec4(color) -> "imgui.ImVec4":
    """Coerce an ``(r, g, b[, a])`` tuple (or an ImVec4) to ``imgui.ImVec4``.

    Parameters
    ----------
    color : tuple | imgui.ImVec4
        Components in the 0..1 range.

    Examples
    --------
    >>> from imgui_debugger import to_vec4
    >>> to_vec4((1.0, 0.0, 0.0)).w
    1.0
    """
    if isinstance(color, imgui.ImVec4):
        return color
    r, g, b = color[0], color[1], color[2]
    a = color[3] if len(color) > 3 else 1.0
    return imgui.ImVec4(r, g, b, a)


@dataclass(frozen=True)
class Theme:
    """Palette for the debugger, one ``(r, g, b, a)`` float tuple per role.

    Examples
    --------
    >>> from imgui_debugger import Theme
    >>> t = Theme.light()
    >>> t.node != Theme.dark().node
    True
    >>> Theme.dark().replace(accent=(1.0, 0.5, 0.0, 1.0)).accent
    (1.0, 0.5, 0.0, 1.0)
    """

    bg: Color = (0.11, 0.11, 0.12, 1.0)
    text: Color = (0.90, 0.90, 0.92, 1.0)
    text_dim: Color = (0.55, 0.55, 0.58, 1.0)
    accent: Color = (0.20, 0.50, 0.85, 1.0)
    border: Color = (0.35, 0.35, 0.37, 0.7)
    separator: Color = (0.35, 0.35, 0.37, 0.6)
    frame_bg: Color = (0.18, 0.18, 0.20, 1.0)
    # tree roles
    node: Color = (0.40, 0.80, 0.95, 1.0)
    name: Color = (0.95, 0.80, 0.30, 1.0)
    index: Color = (0.60, 0.95, 0.40, 1.0)
    value: Color = (0.85, 0.85, 0.85, 1.0)
    prop: Color = (0.70, 0.75, 1.00, 1.0)
    cls: Color = (0.85, 0.65, 1.00, 1.0)
    local: Color = (0.95, 0.80, 0.30, 1.0)
    glob: Color = (0.55, 0.85, 0.80, 1.0)
    runtime: Color = (0.90, 0.60, 0.40, 1.0)
    error: Color = (0.95, 0.40, 0.40, 1.0)
    changed: Color = (1.00, 0.85, 0.35, 1.0)
    frame_rounding: float = 4.0
    child_rounding: float = 4.0

    @staticmethod
    def dark() -> "Theme":
        """The default dark palette.

        Examples
        --------
        >>> from imgui_debugger import Theme
        >>> Theme.dark() == Theme()
        True
        """
        return Theme()

    @staticmethod
    def light() -> "Theme":
        """A light palette with the same role names.

        Examples
        --------
        >>> from imgui_debugger import Theme
        >>> Theme.light().bg[0] > 0.5
        True
        """
        return Theme(
            bg=(0.94, 0.94, 0.95, 1.0),
            text=(0.10, 0.10, 0.12, 1.0),
            text_dim=(0.42, 0.42, 0.46, 1.0),
            accent=(0.10, 0.45, 0.80, 1.0),
            border=(0.70, 0.70, 0.74, 0.9),
            separator=(0.70, 0.70, 0.74, 0.6),
            frame_bg=(0.88, 0.88, 0.90, 1.0),
            node=(0.05, 0.40, 0.60, 1.0),
            name=(0.55, 0.38, 0.05, 1.0),
            index=(0.15, 0.45, 0.10, 1.0),
            value=(0.18, 0.18, 0.20, 1.0),
            prop=(0.25, 0.30, 0.65, 1.0),
            cls=(0.45, 0.20, 0.60, 1.0),
            local=(0.55, 0.38, 0.05, 1.0),
            glob=(0.10, 0.45, 0.42, 1.0),
            runtime=(0.65, 0.35, 0.10, 1.0),
            error=(0.75, 0.15, 0.15, 1.0),
            changed=(0.60, 0.42, 0.00, 1.0),
        )

    def replace(self, **changes) -> "Theme":
        """Return a copy with the given fields overridden.

        Examples
        --------
        >>> from imgui_debugger import Theme
        >>> Theme.dark().replace(name=(1.0, 0.0, 0.0, 1.0)).name
        (1.0, 0.0, 0.0, 1.0)
        """
        return replace(self, **changes)
