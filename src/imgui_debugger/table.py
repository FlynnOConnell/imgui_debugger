"""A sortable, filterable, clipped item table and the ordering behind it.

Merged from the two copies that had drifted apart:
``masknmf.visualization.imgui.table`` (name-based sort, a pinned column, float
ranges, prefix rows, row colours) and ``mbo_utilities.gui.imgui.table`` (label
filtering, row action buttons, ``next_unlabeled``, ``step_group``). This one
does both; a feature you do not use costs nothing.

Examples
--------
>>> import numpy as np
>>> from imgui_debugger import RoiOrder
>>> order = RoiOrder({"area": np.array([10, 30, 20])}, n_items=3)
>>> order.sort_by, order.ascending = "area", True
>>> order.rebuild()
>>> order.order.tolist()
[0, 2, 1]
"""

from __future__ import annotations

from typing import Callable, NamedTuple, Optional, Sequence

import numpy as np
from imgui_bundle import imgui

from .theme import Theme, to_vec4

# filter_label sentinels: show everything, and "items with no label"
FILTER_ALL = -2
UNLABELED = -1


class RowAction(NamedTuple):
    """One icon button in the table's trailing actions column.

    Parameters
    ----------
    icon : str
        Glyph drawn on the button; the name belongs in ``tooltip``.
    tooltip : str
        Hover text.
    on_click : Callable[[int], None]
        Called with the item index on press.
    disabled : Callable[[int], str | None] | None
        Why the action cannot run for that item; greys the button and replaces
        the tooltip. ``None`` means available.

    Examples
    --------
    >>> from imgui_debugger import RowAction
    >>> action = RowAction("x", "delete", lambda i: None)
    >>> action.icon, action.disabled
    ('x', None)
    """

    icon: str
    tooltip: str
    on_click: Callable[[int], None]
    disabled: Optional[Callable[[int], Optional[str]]] = None


class RoiOrder:
    """Filter and stable sort over per-item columns; yields the visible order.

    Parameters
    ----------
    columns : dict
        Name to one value per item.
    n_items : int
        How many items there are.
    pinned : str | None
        A column whose nonzero items always sort first.
    labels : numpy.ndarray | None
        One class index per item, ``-1`` for unlabeled; enables the label
        filter and :meth:`next_unlabeled` / :meth:`step_group`.

    Examples
    --------
    >>> import numpy as np
    >>> from imgui_debugger import RoiOrder
    >>> order = RoiOrder({"area": np.array([10.0, 30.0, 20.0])}, 3)
    >>> order.set_range_column("area")
    >>> order.range_span
    (10.0, 30.0)
    >>> order.range_limits = (15.0, 40.0)
    >>> order.rebuild()
    >>> order.order.tolist()
    [1, 2]
    """

    def __init__(
        self,
        columns: dict,
        n_items: int,
        pinned: Optional[str] = None,
        labels: Optional[np.ndarray] = None,
    ):
        self.columns = columns
        self.n_items = n_items
        self.pinned = pinned
        self.labels = labels
        self.filter_label = FILTER_ALL
        self.range_column: Optional[str] = None
        self.range_span = (0.0, 0.0)
        self.range_limits = (0.0, 0.0)
        self.sort_by: Optional[str] = None
        self.ascending = True
        self.order = np.arange(n_items)
        self.pos = 0

    def set_range_column(self, name: str) -> None:
        """Filter on ``name``, with the limits reset to its full span.

        Parameters
        ----------
        name : str
            A key of ``columns``.

        Examples
        --------
        >>> import numpy as np
        >>> from imgui_debugger import RoiOrder
        >>> order = RoiOrder({"area": np.array([1.0, 5.0])}, 2)
        >>> order.set_range_column("area")
        >>> order.range_limits
        (1.0, 5.0)
        """
        self.range_column = name
        values = np.asarray(self.columns[name], dtype=np.float64)
        values = values[np.isfinite(values)]
        span = (float(values.min()), float(values.max())) if values.size else (0.0, 0.0)
        self.range_span = span
        self.range_limits = span

    @property
    def current(self) -> Optional[int]:
        """The item under the cursor, or None when nothing is in view.

        Examples
        --------
        >>> import numpy as np
        >>> from imgui_debugger import RoiOrder
        >>> RoiOrder({"a": np.array([1])}, 1).current
        0
        """
        if len(self.order) == 0:
            return None
        return int(self.order[self.pos])

    def rebuild(self) -> None:
        """Reapply the filters and the sort, keeping the cursor on its item.

        Examples
        --------
        >>> import numpy as np
        >>> from imgui_debugger import RoiOrder
        >>> order = RoiOrder({"a": np.array([3.0, 1.0])}, 2)
        >>> order.sort_by = "a"
        >>> order.rebuild()
        >>> order.order.tolist()
        [1, 0]
        """
        current = self.current
        mask = np.ones(self.n_items, dtype=bool)
        if self.range_column is not None:
            values = np.asarray(self.columns[self.range_column], dtype=np.float64)
            mask &= (values >= self.range_limits[0]) & (values <= self.range_limits[1])
        if self.labels is not None and self.filter_label >= UNLABELED:
            mask &= self.labels == self.filter_label
        idx = np.flatnonzero(mask)
        if self.sort_by is not None:
            key = np.asarray(self.columns[self.sort_by])[idx]
            idx = idx[np.argsort(key if self.ascending else -key, kind="stable")]
        elif not self.ascending:
            idx = idx[::-1]
        if self.pinned is not None:
            idx = idx[np.argsort(np.asarray(self.columns[self.pinned])[idx] == 0, kind="stable")]
        self.order = idx
        hits = np.flatnonzero(self.order == current) if current is not None else ()
        self.pos = int(hits[0]) if len(hits) else int(min(self.pos, max(len(idx) - 1, 0)))

    def step(self, delta: int) -> bool:
        """Move the cursor by ``delta``, clamped to the view.

        Parameters
        ----------
        delta : int
            Rows to move; negative goes up.

        Examples
        --------
        >>> import numpy as np
        >>> from imgui_debugger import RoiOrder
        >>> order = RoiOrder({"a": np.array([1, 2, 3])}, 3)
        >>> order.step(2)
        True
        >>> order.pos
        2
        """
        if not len(self.order):
            return False
        self.pos = int(np.clip(self.pos + delta, 0, len(self.order) - 1))
        return True

    def goto(self, item: int) -> bool:
        """Put the cursor on ``item``; False when it is not in view.

        Parameters
        ----------
        item : int
            Item index.

        Examples
        --------
        >>> import numpy as np
        >>> from imgui_debugger import RoiOrder
        >>> RoiOrder({"a": np.array([1, 2])}, 2).goto(1)
        True
        """
        hits = np.flatnonzero(self.order == item)
        if not len(hits):
            return False
        self.pos = int(hits[0])
        return True

    def hidden_by(self, item: int) -> list:
        """Names of the filters keeping ``item`` out of the current view.

        Parameters
        ----------
        item : int
            Item index.

        Examples
        --------
        >>> import numpy as np
        >>> from imgui_debugger import RoiOrder
        >>> order = RoiOrder({"area": np.array([1.0, 50.0])}, 2)
        >>> order.set_range_column("area")
        >>> order.range_limits = (0.0, 10.0)
        >>> order.hidden_by(1)
        ['area']
        """
        out = []
        if (
            self.labels is not None
            and self.filter_label >= UNLABELED
            and int(self.labels[item]) != self.filter_label
        ):
            out.append("label")
        if self.range_column is not None:
            value = float(self.columns[self.range_column][item])
            if not self.range_limits[0] <= value <= self.range_limits[1]:
                out.append(self.range_column)
        return out

    def hidden(self, item: int) -> bool:
        """Whether any filter keeps ``item`` out of the view.

        Examples
        --------
        >>> import numpy as np
        >>> from imgui_debugger import RoiOrder
        >>> RoiOrder({"a": np.array([1, 2])}, 2).hidden(0)
        False
        """
        return bool(self.hidden_by(item))

    def clear_filter(self, name: str) -> None:
        """Drop one filter by the name :meth:`hidden_by` reported.

        Parameters
        ----------
        name : str
            ``"label"`` or the range column's name.

        Examples
        --------
        >>> import numpy as np
        >>> from imgui_debugger import RoiOrder
        >>> order = RoiOrder({"area": np.array([1.0, 50.0])}, 2)
        >>> order.set_range_column("area")
        >>> order.range_limits = (0.0, 10.0)
        >>> order.clear_filter("area")
        >>> order.range_limits
        (1.0, 50.0)
        """
        if name == "label":
            self.filter_label = FILTER_ALL
        elif name == self.range_column:
            self.set_range_column(self.range_column)

    def reveal(self, item: int) -> list:
        """Put ``item`` under the cursor, dropping whatever filters hide it.

        Parameters
        ----------
        item : int
            Item index.

        Returns
        -------
        list
            The filters cleared, so a caller can say which ones it undid.

        Examples
        --------
        >>> import numpy as np
        >>> from imgui_debugger import RoiOrder
        >>> order = RoiOrder({"area": np.array([1.0, 50.0])}, 2)
        >>> order.set_range_column("area")
        >>> order.range_limits = (0.0, 10.0)
        >>> order.rebuild()
        >>> order.reveal(1)
        ['area']
        """
        cleared = self.hidden_by(item)
        for name in cleared:
            self.clear_filter(name)
        if cleared:
            self.rebuild()
        self.goto(item)
        return cleared

    def next_unlabeled(self) -> bool:
        """Move to the first unlabeled item after the cursor, wrapping.

        Examples
        --------
        >>> import numpy as np
        >>> from imgui_debugger import RoiOrder
        >>> order = RoiOrder({"a": np.array([1, 2])}, 2, labels=np.array([0, -1]))
        >>> order.next_unlabeled()
        True
        >>> order.pos
        1
        """
        if self.labels is None:
            return False
        hits = np.flatnonzero(self.labels[self.order] < 0)
        if not len(hits):
            return False
        after = hits[hits > self.pos]
        self.pos = int(after[0] if len(after) else hits[0])
        return True

    def step_group(self, direction: int) -> bool:
        """Move to the first item in view of the next or previous label class.

        Parameters
        ----------
        direction : int
            ``1`` for the next class, ``-1`` for the previous.

        Examples
        --------
        >>> import numpy as np
        >>> from imgui_debugger import RoiOrder
        >>> order = RoiOrder({"a": np.array([1, 2])}, 2, labels=np.array([0, 1]))
        >>> order.step_group(1)
        True
        >>> order.pos
        1
        """
        if self.labels is None or self.current is None:
            return False
        labels = self.labels[self.order]
        values = np.unique(labels)
        if len(values) < 2:
            return False
        i = int(np.flatnonzero(values == int(self.labels[self.current]))[0])
        target = values[(i + direction) % len(values)]
        self.pos = int(np.flatnonzero(labels == target)[0])
        return True


def draw_table(
    order: RoiOrder,
    column_names: Sequence[str],
    formatters: dict,
    scroll_to_current: bool,
    table_id: str = "items",
    cursor: bool = True,
    on_select: Optional[Callable[[int], None]] = None,
    actions: Sequence[RowAction] = (),
    is_grouped: Optional[Callable[[int], bool]] = None,
    on_ctrl_select: Optional[Callable[[int], None]] = None,
    on_shift_select: Optional[Callable[[int], None]] = None,
    row_color: Optional[Callable[[int], Optional[tuple]]] = None,
    prefix_rows: Sequence[tuple] = (),
    label_set=None,
    theme: Optional[Theme] = None,
) -> bool:
    """A sortable, clipped table over ``order``; returns the new scroll flag.

    ``column_names[0]`` is the id column; every other name is rendered by
    ``formatters[name](item)`` and is sortable when it is a key of
    ``order.columns``. A column named ``"label"`` is drawn in its class colour
    when ``label_set`` is given.

    Parameters
    ----------
    order : RoiOrder
        The ordering; its ``sort_by`` and ``ascending`` follow the header.
    column_names : Sequence[str]
        Header labels, id column first.
    formatters : dict
        Name to ``formatter(item) -> str`` for every non-id column.
    scroll_to_current : bool
        Scroll the cursor row into view once; the returned value is the flag
        for the next frame.
    table_id : str
        imgui id.
    cursor : bool
        Highlight the row under ``order.pos``; off means nothing is selected
        and the cursor only seeds up / down.
    on_select, on_ctrl_select, on_shift_select : Callable[[int], None] | None
        Row click handlers; ctrl and shift fall back to ``on_select``.
    actions : Sequence[RowAction]
        A trailing, unsortable column of icon buttons per row.
    is_grouped : Callable[[int], bool] | None
        Highlights rows beyond the cursor, for a multi-selection.
    row_color : Callable[[int], tuple | None] | None
        Tints the id cell; rgb in 0-1.
    prefix_rows : Sequence[tuple]
        ``(item, label)`` pairs pinned above the sorted rows, outside ``order``
        but routed to the same formatters and callbacks.
    label_set : object | None
        Anything with ``labels``, ``names`` and ``color(i)``, for the label
        column.
    theme : Theme | None
        Palette; the dark default when omitted.

    Examples
    --------
    >>> import numpy as np
    >>> from imgui_debugger import RoiOrder, draw_table
    >>> order = RoiOrder({"area": np.array([10.0, 20.0])}, 2)
    >>> draw_table(order, ["id", "area"],
    ...            {"area": lambda i: f"{i}"}, False)   # doctest: +SKIP
    False
    """
    theme = theme or Theme.dark()
    flags = (
        imgui.TableFlags_.sortable
        | imgui.TableFlags_.row_bg
        | imgui.TableFlags_.resizable
        | imgui.TableFlags_.scroll_y
    )
    avail = imgui.get_content_region_avail()
    n_columns = len(column_names) + bool(actions)
    if not imgui.begin_table(table_id, n_columns, flags, imgui.ImVec2(0, avail.y)):
        return scroll_to_current
    imgui.table_setup_scroll_freeze(0, 1)
    # the current sort seeds imgui's default, so it survives a change of columns
    descending = 0 if order.ascending else imgui.TableColumnFlags_.prefer_sort_descending
    imgui.table_setup_column(
        column_names[0],
        imgui.TableColumnFlags_.default_sort | descending if order.sort_by is None else 0,
    )
    for name in column_names[1:]:
        col_flags = 0 if name in order.columns else imgui.TableColumnFlags_.no_sort
        if name == order.sort_by:
            col_flags |= imgui.TableColumnFlags_.default_sort | descending
        imgui.table_setup_column(name, col_flags)
    if actions:
        imgui.table_setup_column(
            "##actions",
            imgui.TableColumnFlags_.no_sort | imgui.TableColumnFlags_.width_fixed,
            len(actions) * imgui.get_font_size() * 2.0,
        )
    imgui.table_headers_row()

    specs = imgui.table_get_sort_specs()
    if specs is not None and specs.specs_dirty:
        if specs.specs_count > 0:
            index = int(specs.specs.column_index)
            order.sort_by = column_names[index] if index else None
            order.ascending = specs.specs.sort_direction == imgui.SortDirection.ascending
        specs.specs_dirty = False
        order.rebuild()

    pinned = len(prefix_rows)
    clipper = imgui.ListClipper()
    clipper.begin(pinned + len(order.order))
    if scroll_to_current:
        clipper.include_item_by_index(pinned + order.pos)
    while clipper.step():
        for row in range(clipper.display_start, clipper.display_end):
            if row < pinned:
                item, label = prefix_rows[row]
                highlighted = is_grouped is not None and is_grouped(item)
            else:
                item = int(order.order[row - pinned])
                label = f"{item}"
                highlighted = (cursor and row - pinned == order.pos) or (
                    is_grouped is not None and is_grouped(item)
                )
            imgui.table_next_row()
            imgui.table_next_column()
            sel_flags = imgui.SelectableFlags_.span_all_columns
            if actions:
                sel_flags |= imgui.SelectableFlags_.allow_overlap
            rgb = row_color(item) if row_color is not None else None
            if rgb is not None:
                imgui.push_style_color(imgui.Col_.text, imgui.ImVec4(*rgb[:3], 1.0))
            clicked, _ = imgui.selectable(f"{label}##row{row}", highlighted, sel_flags)
            if rgb is not None:
                imgui.pop_style_color()
            if clicked:
                io = imgui.get_io()
                if io.key_ctrl and on_ctrl_select is not None:
                    on_ctrl_select(item)
                elif io.key_shift and on_shift_select is not None:
                    on_shift_select(item)
                else:
                    if row >= pinned:
                        order.pos = row - pinned
                    if on_select is not None:
                        on_select(item)
            if row - pinned == order.pos and scroll_to_current:
                imgui.set_scroll_here_y(0.5)
                scroll_to_current = False
            for name in column_names[1:]:
                imgui.table_next_column()
                if name == "label" and label_set is not None:
                    _draw_label_cell(label_set, item, theme)
                else:
                    imgui.text(formatters[name](item))
            if actions:
                imgui.table_next_column()
                _draw_row_actions(actions, item, row)
    imgui.end_table()
    return scroll_to_current


def _draw_label_cell(label_set, item: int, theme: Theme) -> None:
    """Draw an item's class name in its colour, or a dash when unlabeled.

    Examples
    --------
    >>> from imgui_debugger.table import _draw_label_cell   # doctest: +SKIP
    """
    label = int(label_set.labels[item])
    if label >= 0:
        imgui.text_colored(to_vec4(label_set.color(label)), label_set.names[label])
    else:
        imgui.text("-")


def _draw_row_actions(actions: Sequence[RowAction], item: int, row: int) -> None:
    """Icon buttons for one row; ``row`` only keeps the imgui ids unique.

    Examples
    --------
    >>> from imgui_debugger.table import _draw_row_actions   # doctest: +SKIP
    """
    for k, action in enumerate(actions):
        if k:
            imgui.same_line(0, 2)
        reason = action.disabled(item) if action.disabled is not None else None
        if reason is not None:
            imgui.begin_disabled()
        if imgui.small_button(f"{action.icon}##act{k}_{row}"):
            action.on_click(item)
        if reason is not None:
            imgui.end_disabled()
        if imgui.is_item_hovered(imgui.HoveredFlags_.allow_when_disabled):
            imgui.set_tooltip(reason or action.tooltip)


def draw_range_filter(order: RoiOrder, id_suffix: str = "", width: float = -1) -> bool:
    """A column picker and a range slider over ``order.range_column``.

    Draws nothing when no range column is set. Does not rebuild.

    Parameters
    ----------
    order : RoiOrder
        The ordering to filter.
    id_suffix : str
        Appended to the imgui ids, for two filters in one window.
    width : float
        Slider width; ``-1`` fills the line.

    Returns
    -------
    bool
        True when the column or the limits changed.

    Examples
    --------
    >>> import numpy as np
    >>> from imgui_debugger import RoiOrder, draw_range_filter
    >>> order = RoiOrder({"area": np.array([1.0, 5.0])}, 2)
    >>> draw_range_filter(order)
    False
    """
    if order.range_column is None:
        return False
    names = list(order.columns)
    imgui.set_next_item_width(imgui.get_font_size() * 5.5)
    picked, index = imgui.combo(
        f"##range_column{id_suffix}", names.index(order.range_column), names
    )
    if picked:
        order.set_range_column(names[index])
    imgui.same_line()
    kind = np.asarray(order.columns[order.range_column]).dtype.kind
    fmt = "%.0f" if kind in "iub" else "%.3g"
    lo, hi = order.range_span
    imgui.set_next_item_width(width)
    changed, lo_v, hi_v = imgui.drag_float_range2(
        f"##range{id_suffix}",
        float(order.range_limits[0]),
        float(order.range_limits[1]),
        max((hi - lo) / 200, 1e-6),
        lo,
        hi,
        f"{order.range_column} >= {fmt}",
        f"{order.range_column} <= {fmt}",
    )
    if changed:
        order.range_limits = (lo_v, hi_v)
    return picked or changed


def draw_label_filter(
    order: RoiOrder, label_set, id_suffix: str = "", width: float = -1
) -> bool:
    """The label filter combo on its own. Does not rebuild.

    Parameters
    ----------
    order : RoiOrder
        The ordering to filter.
    label_set : object
        Anything with a ``names`` sequence.
    id_suffix : str
        Appended to the imgui id.
    width : float
        Combo width.

    Returns
    -------
    bool
        True when the selection changed.

    Examples
    --------
    >>> import numpy as np
    >>> from imgui_debugger import RoiOrder, draw_label_filter
    >>> order = RoiOrder({"a": np.array([1])}, 1, labels=np.array([-1]))
    >>> draw_label_filter(order, None)      # doctest: +SKIP
    False
    """
    names = ("all", "unlabeled", *label_set.names)
    imgui.set_next_item_width(width)
    changed, sel = imgui.combo(
        f"##filter{id_suffix}", order.filter_label + 2, list(names)
    )
    if changed:
        order.filter_label = sel - 2
    return changed


def draw_filter_row(order: RoiOrder, label_set=None, id_suffix: str = "") -> bool:
    """The label filter, the range filter and an "n/total in view" count.

    Rebuilds ``order`` when anything changed.

    Parameters
    ----------
    order : RoiOrder
        The ordering to filter.
    label_set : object | None
        Enables the label combo when given.
    id_suffix : str
        Appended to the imgui ids.

    Examples
    --------
    >>> import numpy as np
    >>> from imgui_debugger import RoiOrder, draw_filter_row
    >>> draw_filter_row(RoiOrder({"a": np.array([1])}, 1))   # doctest: +SKIP
    False
    """
    changed = False
    if label_set is not None:
        changed |= draw_label_filter(order, label_set, id_suffix)
    changed |= draw_range_filter(order, id_suffix)
    imgui.text(f"{len(order.order)}/{order.n_items} in view")
    if changed:
        order.rebuild()
    return changed
