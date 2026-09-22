"""Layout and styling helpers the panels are built from.

Ported from the copies in ``masknmf.visualization.imgui.theme`` and
``mbo_utilities.gui._theme``, which had drifted apart.

Examples
--------
>>> from imgui_debugger import card, help_mark, section
>>> section("Detection")                    # doctest: +SKIP
>>> with card("stats", "Stats", height=120):  # doctest: +SKIP
...     help_mark("what these numbers mean")
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Sequence, Tuple

from imgui_bundle import imgui

from .theme import Theme, to_vec4

DEFAULT_THEME = Theme.dark()


def em(x: float = 1.0) -> float:
    """``x`` font heights in pixels; only valid inside a frame.

    Parameters
    ----------
    x : float
        How many font heights.

    Examples
    --------
    >>> from imgui_debugger import em
    >>> em(2.0)                 # doctest: +SKIP
    28.0
    """
    return imgui.get_font_size() * x


@contextmanager
def card(
    name: str,
    title: str,
    height: float,
    width: float = 0.0,
    theme: Theme = DEFAULT_THEME,
):
    """A bordered child window with an accent title.

    Parameters
    ----------
    name : str
        imgui id for the child.
    title : str
        Accent-coloured heading drawn inside it.
    height : float
        Fixed height, so cards laid out on one row line up.
    width : float
        ``0`` sizes the card to its content.
    theme : Theme
        Palette for the border and the title.

    Examples
    --------
    >>> from imgui_debugger import card
    >>> with card("stats", "Stats", height=120):   # doctest: +SKIP
    ...     imgui.text("12 ROIs")
    """
    flags = imgui.ChildFlags_.borders
    if width == 0:
        flags |= imgui.ChildFlags_.auto_resize_x
    imgui.push_style_color(imgui.Col_.border, to_vec4(theme.border))
    imgui.push_style_var(imgui.StyleVar_.child_rounding, theme.card_rounding)
    imgui.begin_child(
        name,
        imgui.ImVec2(width, height),
        child_flags=flags,
        window_flags=imgui.WindowFlags_.no_scrollbar,
    )
    imgui.text_colored(to_vec4(theme.accent), title)
    try:
        yield
    finally:
        imgui.end_child()
        imgui.pop_style_var()
        imgui.pop_style_color()


def section(title: str, theme: Theme = DEFAULT_THEME) -> None:
    """An accent heading with a rule under it.

    Parameters
    ----------
    title : str
        Heading text.
    theme : Theme
        Palette for the heading.

    Examples
    --------
    >>> from imgui_debugger import section
    >>> section("Detection")     # doctest: +SKIP
    """
    imgui.dummy(imgui.ImVec2(0, em(0.3)))
    imgui.text_colored(to_vec4(theme.accent), title)
    imgui.separator()
    imgui.dummy(imgui.ImVec2(0, em(0.2)))


def help_mark(text: str) -> None:
    """A dim ``(?)`` after the last item, with ``text`` as its tooltip.

    Parameters
    ----------
    text : str
        Tooltip body.

    Examples
    --------
    >>> from imgui_debugger import help_mark
    >>> help_mark("only the frames on screen are read")   # doctest: +SKIP
    """
    imgui.same_line(0, em(0.3))
    imgui.text_disabled("(?)")
    if imgui.is_item_hovered():
        imgui.set_tooltip(text)


def right_aligned_text(text: str) -> None:
    """Dim ``text`` flush with the right edge, wrapping when the line is full.

    Parameters
    ----------
    text : str
        The text to draw.

    Examples
    --------
    >>> from imgui_debugger import right_aligned_text
    >>> right_aligned_text("3 of 40")     # doctest: +SKIP
    """
    room = imgui.get_content_region_avail().x - imgui.calc_text_size(text).x
    if room < 0:
        imgui.new_line()
        room = imgui.get_content_region_avail().x - imgui.calc_text_size(text).x
    if room > 0:
        imgui.set_cursor_pos_x(imgui.get_cursor_pos_x() + room)
    imgui.align_text_to_frame_padding()
    imgui.text_disabled(text)


@contextmanager
def button_colors(fill, hover, text=None, on: bool = True):
    """Fill, hover and optionally text colours for the buttons drawn inside.

    Parameters
    ----------
    fill, hover : tuple | imgui.ImVec4
        Button and hovered/active colours.
    text : tuple | imgui.ImVec4 | None
        Label colour; left alone when None.
    on : bool
        False makes the whole thing a no-op, so a caller can gate it.

    Examples
    --------
    >>> from imgui_debugger import Theme, button_colors
    >>> t = Theme.dark()
    >>> with button_colors(t.danger, t.danger_hover):    # doctest: +SKIP
    ...     imgui.button("delete all")
    """
    if on:
        imgui.push_style_color(imgui.Col_.button, to_vec4(fill))
        imgui.push_style_color(imgui.Col_.button_hovered, to_vec4(hover))
        imgui.push_style_color(imgui.Col_.button_active, to_vec4(hover))
        if text is not None:
            imgui.push_style_color(imgui.Col_.text, to_vec4(text))
    try:
        yield
    finally:
        if on:
            imgui.pop_style_color(4 if text is not None else 3)


def popup(title: str, is_open: bool, theme: Theme = DEFAULT_THEME) -> Tuple[bool, bool]:
    """Begin a centered, auto-sized, closable window.

    Parameters
    ----------
    title : str
        Window title; also its stable id.
    is_open : bool
        Current open state.
    theme : Theme
        Palette for the rounding.

    Returns
    -------
    tuple[bool, bool]
        ``(draw_contents, still_open)``. Call ``imgui.end()`` either way.

    Examples
    --------
    >>> from imgui_debugger import popup
    >>> opened, is_open = popup("Keybinds", True)   # doctest: +SKIP
    >>> imgui.end()                                  # doctest: +SKIP
    """
    imgui.set_next_window_pos(
        imgui.get_main_viewport().get_center(),
        imgui.Cond_.appearing,
        pivot=imgui.ImVec2(0.5, 0.5),
    )
    imgui.push_style_var(imgui.StyleVar_.window_rounding, theme.rounding)
    imgui.push_style_var(imgui.StyleVar_.window_padding, imgui.ImVec2(em(1.0), em(0.8)))
    opened, is_open = imgui.begin(
        f"{title}###{title}",
        is_open,
        flags=imgui.WindowFlags_.no_saved_settings
        | imgui.WindowFlags_.always_auto_resize,
    )
    imgui.pop_style_var(2)
    return opened, is_open


def close_button(label: str = "Close") -> bool:
    """A Close button of the width every popup here uses.

    Parameters
    ----------
    label : str
        Button text.

    Examples
    --------
    >>> from imgui_debugger import close_button
    >>> close_button()          # doctest: +SKIP
    False
    """
    imgui.dummy(imgui.ImVec2(0, em(0.3)))
    return imgui.button(label, imgui.ImVec2(em(6), 0))


@dataclass(frozen=True)
class Grid:
    """Three aligned columns: a caption, then two equal cells.

    A cell holds a ``w``-wide control and its :func:`help_mark`; ``span`` is a
    control across both cells, its mark in line with the second cell's.

    Parameters
    ----------
    cell_x : tuple
        Window-local x of each cell.
    cell_w : float
        Width of one cell.
    gap : float
        Space between the columns.
    mark_w : float
        Width reserved for a trailing ``(?)``.

    Examples
    --------
    >>> from imgui_debugger import grid
    >>> g = grid(["threshold", "engine"])    # doctest: +SKIP
    >>> g.row("threshold")                   # doctest: +SKIP
    """

    cell_x: tuple
    cell_w: float
    gap: float
    mark_w: float

    @property
    def w(self) -> float:
        """Width of a control that leaves room for its help mark.

        Examples
        --------
        >>> from imgui_debugger import Grid
        >>> Grid((0.0, 100.0), 100.0, 8.0, 20.0).w
        80.0
        """
        return self.cell_w - self.mark_w

    @property
    def span(self) -> float:
        """Width of a control stretching across both cells.

        Examples
        --------
        >>> from imgui_debugger import Grid
        >>> Grid((0.0, 100.0), 100.0, 8.0, 20.0).span
        188.0
        """
        return 2 * self.cell_w + self.gap - self.mark_w

    def row(self, caption: str) -> None:
        """Start a row: the dim caption on its widgets' baseline, cursor in cell 0.

        Parameters
        ----------
        caption : str
            Row label.

        Examples
        --------
        >>> from imgui_debugger import grid
        >>> grid(["engine"]).row("engine")    # doctest: +SKIP
        """
        imgui.align_text_to_frame_padding()
        imgui.text_disabled(caption)
        self.cell(0)

    def cell(self, i: int) -> None:
        """Continue the row in cell ``i``, wrapping when the last item overruns it.

        Parameters
        ----------
        i : int
            Cell index, ``0`` or ``1``.

        Examples
        --------
        >>> from imgui_debugger import grid
        >>> grid(["engine"]).cell(1)          # doctest: +SKIP
        """
        x = self.cell_x[i]
        edge = imgui.get_window_pos().x - imgui.get_scroll_x() + x - self.gap
        if imgui.get_item_rect_max().x > edge:
            imgui.new_line()
            x = self.cell_x[0]
        imgui.same_line(x)


def grid(captions: Sequence[str]) -> Grid:
    """Measure a :class:`Grid` at the cursor from the longest caption.

    The caption column fits the widest of ``captions`` as a checkbox; the rest
    of the line splits in two.

    Parameters
    ----------
    captions : Sequence[str]
        Every caption the grid will draw, so the column is measured once.

    Examples
    --------
    >>> from imgui_debugger import grid
    >>> g = grid(["threshold", "engine", "where"])   # doctest: +SKIP
    >>> g.cell_w > 0                                  # doctest: +SKIP
    True
    """
    gap = em(0.6)
    x0 = imgui.get_cursor_pos_x()
    caption_w = (
        max(imgui.calc_text_size(c).x for c in captions)
        + imgui.get_frame_height()
        + imgui.get_style().item_inner_spacing.x
        + gap
    )
    cell_w = (imgui.get_content_region_avail().x - caption_w - gap) / 2
    return Grid(
        (x0 + caption_w, x0 + caption_w + cell_w + gap),
        cell_w,
        gap,
        imgui.calc_text_size("(?)").x + em(0.3),
    )
