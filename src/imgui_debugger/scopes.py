"""Where the debugger's rows come from: scopes and the children of a value.

A :class:`Scope` is a named, collapsible root; :func:`children_of` turns any
value below it into the next level of rows.

Examples
--------
>>> from imgui_debugger.scopes import children_of, object_scopes
>>> [c.name for c in children_of({"fs": 10.0, "dz": 5})]
['fs', 'dz']
>>> class W:
...     def __init__(self):
...         self.visible = True
>>> [s.name for s in object_scopes(W())]
['instance', 'properties', 'class']
"""

from __future__ import annotations

import functools
from collections.abc import Mapping, MutableMapping, MutableSequence, Sequence
from dataclasses import dataclass
from typing import Any, Callable, List, Optional

MAX_ITEMS = 200


@dataclass(frozen=True)
class Child:
    """One row: its label, its current value, where it came from, how to write it.

    Parameters
    ----------
    name : str
        Label shown in the tree.
    value : object
        The value as read this frame, or the exception when ``kind`` is
        ``"error"``.
    kind : str
        One of ``attr``, ``prop``, ``class``, ``item``, ``index``, ``local``,
        ``global``, ``error``.
    setter : callable | None
        ``setter(new_value)`` writes the value back; None for read-only rows.

    Examples
    --------
    >>> from imgui_debugger.scopes import Child
    >>> row = Child("fs", 9.6, "attr")
    >>> row.name, row.kind, row.editable
    ('fs', 'attr', False)
    """

    name: str
    value: Any
    kind: str = "attr"
    setter: Optional[Callable[[Any], None]] = None

    @property
    def editable(self) -> bool:
        """True when this row can be written back.

        Examples
        --------
        >>> from imgui_debugger.scopes import Child
        >>> Child("n", 1, "item", lambda v: None).editable
        True
        """
        return self.setter is not None


@dataclass(frozen=True)
class Scope:
    """A named, collapsible root whose rows are recomputed every frame.

    Parameters
    ----------
    name : str
        Header text.
    children : callable
        ``children()`` returns the scope's rows; called once per frame.
    role : str
        Name of the :class:`~imgui_debugger.theme.Theme` color used for rows.
    hint : str
        Hover tooltip on the header.
    start_open : bool
        Whether the header is expanded the first time it is drawn.

    Examples
    --------
    >>> from imgui_debugger.scopes import Scope, Child
    >>> s = Scope("counters", lambda: [Child("frames", 12)])
    >>> s.children()[0].value
    12
    """

    name: str
    children: Callable[[], List[Child]]
    role: str = "name"
    hint: str = ""
    start_open: bool = True


def _is_dunder(name: str) -> bool:
    """True for ``__name__``-style attributes.

    Examples
    --------
    >>> from imgui_debugger.scopes import _is_dunder
    >>> _is_dunder("__init__"), _is_dunder("_x"), _is_dunder("x")
    (True, False, False)
    """
    return name.startswith("__") and name.endswith("__")


def _keep(name: str, private: bool) -> bool:
    """Whether an attribute name survives the private/dunder filter.

    Examples
    --------
    >>> from imgui_debugger.scopes import _keep
    >>> _keep("_cache", False), _keep("_cache", True), _keep("__x__", True)
    (False, True, False)
    """
    if _is_dunder(name):
        return False
    return private or not name.startswith("_")


def _set_item(container, key, new_value) -> None:
    """Write ``container[key] = new_value``.

    Examples
    --------
    >>> from imgui_debugger.scopes import _set_item
    >>> d = {}
    >>> _set_item(d, "a", 1)
    >>> d
    {'a': 1}
    """
    container[key] = new_value


def _read(obj, name: str, kind: str, writable: bool = True) -> Child:
    """Read one attribute, turning a raising getter into an ``error`` row.

    Examples
    --------
    >>> from imgui_debugger.scopes import _read
    >>> class W:
    ...     @property
    ...     def boom(self):
    ...         raise RuntimeError("no")
    >>> _read(W(), "boom", "prop").kind
    'error'
    """
    try:
        value = getattr(obj, name)
    except Exception as exc:
        return Child(name, exc, "error")
    setter = functools.partial(setattr, obj, name) if writable else None
    return Child(name, value, kind, setter)


def mapping_children(
    value: Mapping, max_items: int = MAX_ITEMS, sort: bool = False
) -> List[Child]:
    """Rows for a mapping, writable when the mapping is mutable.

    Parameters
    ----------
    value : Mapping
        The mapping to expand.
    max_items : int
        Stop after this many keys.
    sort : bool
        Sort keys by name instead of keeping insertion order.

    Examples
    --------
    >>> from imgui_debugger.scopes import mapping_children
    >>> d = {"b": 2, "a": 1}
    >>> [c.name for c in mapping_children(d, sort=True)]
    ['a', 'b']
    >>> mapping_children(d)[0].setter(9)
    >>> d["b"]
    9
    """
    keys = list(value.keys())
    if sort:
        keys.sort(key=str)
    writable = isinstance(value, MutableMapping)
    out: List[Child] = []
    for key in keys[:max_items]:
        setter = functools.partial(_set_item, value, key) if writable else None
        out.append(Child(str(key), value[key], "item", setter))
    return out


def sequence_children(value: Sequence, max_items: int = MAX_ITEMS) -> List[Child]:
    """Rows for a sequence, labelled ``[i]`` and writable when it is mutable.

    Parameters
    ----------
    value : Sequence
        The sequence to expand.
    max_items : int
        Stop after this many entries.

    Examples
    --------
    >>> from imgui_debugger.scopes import sequence_children
    >>> [c.name for c in sequence_children([10, 20])]
    ['[0]', '[1]']
    >>> sequence_children((1, 2))[0].editable
    False
    """
    writable = isinstance(value, MutableSequence)
    out: List[Child] = []
    for i, item in enumerate(value):
        if i >= max_items:
            break
        setter = functools.partial(_set_item, value, i) if writable else None
        out.append(Child(f"[{i}]", item, "index", setter))
    return out


def instance_children(
    obj, private: bool = False, max_items: int = MAX_ITEMS
) -> List[Child]:
    """Rows for an object's own ``__dict__`` and ``__slots__`` state.

    Parameters
    ----------
    obj : object
        The object to inspect.
    private : bool
        Include ``_name`` attributes.
    max_items : int
        Stop after this many attributes.

    Examples
    --------
    >>> from imgui_debugger.scopes import instance_children
    >>> class W:
    ...     def __init__(self):
    ...         self.visible = True
    ...         self._cache = {}
    >>> [c.name for c in instance_children(W())]
    ['visible']
    >>> [c.name for c in instance_children(W(), private=True)]
    ['visible', '_cache']
    """
    names: List[str] = []
    seen = set()
    for name in vars(obj) if hasattr(obj, "__dict__") else ():
        if _keep(name, private) and name not in seen:
            seen.add(name)
            names.append(name)
    for cls in type(obj).__mro__:
        for name in getattr(cls, "__slots__", ()) or ():
            if _keep(name, private) and name not in seen:
                seen.add(name)
                names.append(name)
    return [_read(obj, name, "attr") for name in names[:max_items]]


def property_children(
    obj, private: bool = False, max_items: int = MAX_ITEMS
) -> List[Child]:
    """Rows for the live values of an object's ``property`` descriptors.

    A property that raises shows the exception; one without a setter is
    read-only.

    Parameters
    ----------
    obj : object
        The object to inspect.
    private : bool
        Include ``_name`` properties.
    max_items : int
        Stop after this many properties.

    Examples
    --------
    >>> from imgui_debugger.scopes import property_children
    >>> class W:
    ...     @property
    ...     def area(self):
    ...         return 42
    >>> row = property_children(W())[0]
    >>> row.name, row.value, row.editable
    ('area', 42, False)
    """
    descriptors = {}
    for cls in reversed(type(obj).__mro__):
        for name, attr in vars(cls).items():
            if not _keep(name, private):
                continue
            if isinstance(attr, (property, functools.cached_property)):
                descriptors[name] = attr
    out: List[Child] = []
    for name, attr in list(descriptors.items())[:max_items]:
        writable = isinstance(attr, property) and attr.fset is not None
        out.append(_read(obj, name, "prop", writable))
    return out


def class_children(obj, private: bool = False, max_items: int = MAX_ITEMS) -> List[Child]:
    """Rows for class-level attributes that are not properties or callables.

    Parameters
    ----------
    obj : object | type
        An instance or the class itself.
    private : bool
        Include ``_name`` attributes.
    max_items : int
        Stop after this many attributes.

    Examples
    --------
    >>> from imgui_debugger.scopes import class_children
    >>> class W:
    ...     name = "Voltage"
    ...     def draw(self): ...
    >>> [(c.name, c.value) for c in class_children(W())]
    [('name', 'Voltage')]
    """
    cls = obj if isinstance(obj, type) else type(obj)
    found = {}
    for base in reversed(cls.__mro__):
        if base is object:
            continue
        for name, attr in vars(base).items():
            if not _keep(name, private):
                continue
            if isinstance(attr, (property, functools.cached_property, staticmethod, classmethod)):
                continue
            if callable(attr):
                continue
            found[name] = attr
    out: List[Child] = []
    for name, value in list(found.items())[:max_items]:
        out.append(Child(name, value, "class", functools.partial(setattr, cls, name)))
    return out


def children_of(
    value,
    private: bool = False,
    properties: bool = True,
    max_items: int = MAX_ITEMS,
) -> List[Child]:
    """The next level of rows below any value.

    Mappings and sequences expand into their items; anything else expands into
    its instance attributes and, optionally, its properties.

    Parameters
    ----------
    value : object
        The value to expand.
    private : bool
        Include ``_name`` attributes.
    properties : bool
        Evaluate ``property`` descriptors.
    max_items : int
        Stop after this many rows.

    Examples
    --------
    >>> from imgui_debugger.scopes import children_of
    >>> [c.name for c in children_of([7, 8])]
    ['[0]', '[1]']
    >>> class P:
    ...     def __init__(self):
    ...         self.n = 1
    ...     @property
    ...     def double(self):
    ...         return self.n * 2
    >>> [(c.name, c.value) for c in children_of(P())]
    [('n', 1), ('double', 2)]
    """
    if isinstance(value, Mapping):
        return mapping_children(value, max_items)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return sequence_children(value, max_items)
    if isinstance(value, (set, frozenset)):
        return sequence_children(sorted(value, key=str), max_items)
    out = instance_children(value, private, max_items)
    if properties:
        out += property_children(value, private, max_items)
    return out


def has_children(value, private: bool = False, properties: bool = True) -> bool:
    """Whether a value would expand into at least one row.

    Parameters
    ----------
    value : object
        The value to test.
    private : bool
        Include ``_name`` attributes.
    properties : bool
        Count ``property`` descriptors.

    Examples
    --------
    >>> from imgui_debugger.scopes import has_children
    >>> has_children(3), has_children({"a": 1})
    (False, True)
    """
    try:
        return bool(children_of(value, private, properties, max_items=1))
    except Exception:
        return False


def object_scopes(
    obj,
    private: bool = False,
    properties: bool = True,
    class_attrs: bool = True,
) -> List[Scope]:
    """The ``instance`` / ``properties`` / ``class`` scopes for one object.

    Parameters
    ----------
    obj : object
        The widget or other object being debugged.
    private : bool
        Include ``_name`` attributes.
    properties : bool
        Include the ``properties`` scope.
    class_attrs : bool
        Include the ``class`` scope.

    Examples
    --------
    >>> from imgui_debugger.scopes import object_scopes
    >>> class W:
    ...     name = "ROIs"
    ...     def __init__(self):
    ...         self.open = False
    >>> scopes = object_scopes(W(), properties=False)
    >>> [s.name for s in scopes]
    ['instance', 'class']
    >>> scopes[1].children()[0].value
    'ROIs'
    """
    out = [
        Scope(
            "instance",
            functools.partial(instance_children, obj, private),
            "name",
            f"{type(obj).__name__} instance state (__dict__ and __slots__)",
        )
    ]
    if properties:
        out.append(
            Scope(
                "properties",
                functools.partial(property_children, obj, private),
                "prop",
                "property descriptors, evaluated every frame",
                start_open=False,
            )
        )
    if class_attrs:
        out.append(
            Scope(
                "class",
                functools.partial(class_children, obj, private),
                "cls",
                f"class attributes on {type(obj).__name__} and its bases",
                start_open=False,
            )
        )
    return out


def frame_children(
    frame, kind: str = "local", private: bool = False, max_items: int = MAX_ITEMS
) -> List[Child]:
    """Rows for a stack frame's locals or globals, skipping imported modules.

    Locals are read-only because writing a frame's locals does not stick;
    globals are writable.

    Parameters
    ----------
    frame : types.FrameType | None
        The frame to read.
    kind : str
        ``"local"`` or ``"global"``.
    private : bool
        Include ``_name`` bindings.
    max_items : int
        Stop after this many names.

    Examples
    --------
    >>> import sys
    >>> from imgui_debugger.scopes import frame_children
    >>> answer = 42
    >>> rows = frame_children(sys._getframe())
    >>> any(c.name == "answer" for c in rows)
    True
    >>> rows[0].editable
    False
    """
    if frame is None:
        return []
    import types

    namespace = frame.f_locals if kind == "local" else frame.f_globals
    names = sorted(n for n in namespace if _keep(n, private))
    out: List[Child] = []
    for name in names[:max_items]:
        value = namespace[name]
        if isinstance(value, types.ModuleType):
            continue
        setter = functools.partial(_set_item, namespace, name) if kind == "global" else None
        out.append(Child(name, value, kind, setter))
    return out


def frame_scopes(frame, private: bool = False) -> List[Scope]:
    """The ``locals`` and ``globals`` scopes for a captured stack frame.

    Parameters
    ----------
    frame : types.FrameType | None
        The frame captured at attach time.
    private : bool
        Include ``_name`` bindings.

    Examples
    --------
    >>> import sys
    >>> from imgui_debugger.scopes import frame_scopes
    >>> [s.name for s in frame_scopes(sys._getframe())]
    ['locals', 'globals']
    """
    code = frame.f_code if frame else None
    where = f"{code.co_name}() at {code.co_filename}:{frame.f_lineno}" if code else "no frame"
    module = frame.f_globals.get("__name__", "?") if frame else "?"
    return [
        Scope(
            "locals",
            functools.partial(frame_children, frame, "local", private),
            "local",
            where,
        ),
        Scope(
            "globals",
            functools.partial(frame_children, frame, "global", private),
            "glob",
            f"module globals of {module}",
            start_open=False,
        ),
    ]


def runtime_children() -> List[Child]:
    """Rows for imgui's live per-frame state, read inside an active frame.

    Examples
    --------
    >>> from imgui_debugger.scopes import runtime_children
    >>> [c.name for c in runtime_children()]   # doctest: +SKIP
    ['io', 'mouse', 'keyboard', 'window', 'style']
    """
    from imgui_bundle import imgui

    io = imgui.get_io()
    style = imgui.get_style()
    pos, avail = imgui.get_window_pos(), imgui.get_content_region_avail()
    cursor = imgui.get_cursor_screen_pos()
    return [
        Child(
            "io",
            {
                "framerate": round(float(io.framerate), 1),
                "delta_time": round(float(io.delta_time), 5),
                "display_size": (io.display_size.x, io.display_size.y),
                "framebuffer_scale": (
                    io.display_framebuffer_scale.x,
                    io.display_framebuffer_scale.y,
                ),
                "want_capture_mouse": bool(io.want_capture_mouse),
                "want_capture_keyboard": bool(io.want_capture_keyboard),
                "want_text_input": bool(io.want_text_input),
            },
            "item",
        ),
        Child(
            "mouse",
            {
                "pos": (io.mouse_pos.x, io.mouse_pos.y),
                "delta": (io.mouse_delta.x, io.mouse_delta.y),
                "wheel": float(io.mouse_wheel),
                "down": [bool(io.mouse_down[i]) for i in range(3)],
            },
            "item",
        ),
        Child(
            "keyboard",
            {
                "ctrl": bool(io.key_ctrl),
                "shift": bool(io.key_shift),
                "alt": bool(io.key_alt),
                "super": bool(io.key_super),
            },
            "item",
        ),
        Child(
            "window",
            {
                "pos": (pos.x, pos.y),
                "size": (imgui.get_window_width(), imgui.get_window_height()),
                "content_avail": (avail.x, avail.y),
                "cursor_screen_pos": (cursor.x, cursor.y),
                "scroll": (imgui.get_scroll_x(), imgui.get_scroll_y()),
                "scroll_max": (imgui.get_scroll_max_x(), imgui.get_scroll_max_y()),
            },
            "item",
        ),
        Child(
            "style",
            {
                "font_size": imgui.get_font_size(),
                "frame_height": imgui.get_frame_height(),
                "text_line_height": imgui.get_text_line_height(),
                "window_padding": (style.window_padding.x, style.window_padding.y),
                "frame_padding": (style.frame_padding.x, style.frame_padding.y),
                "item_spacing": (style.item_spacing.x, style.item_spacing.y),
                "item_inner_spacing": (
                    style.item_inner_spacing.x,
                    style.item_inner_spacing.y,
                ),
                "indent_spacing": style.indent_spacing,
                "scrollbar_size": style.scrollbar_size,
            },
            "item",
        ),
    ]


def runtime_scope() -> Scope:
    """The ``imgui`` scope: io, mouse, keyboard, window rect and style metrics.

    Examples
    --------
    >>> from imgui_debugger.scopes import runtime_scope
    >>> runtime_scope().name
    'imgui'
    """
    return Scope(
        "imgui",
        runtime_children,
        "runtime",
        "live imgui state for the window the debugger is drawn in",
        start_open=False,
    )


@dataclass
class Watch:
    """An extra scope holding one value, or a callable re-read every frame.

    Parameters
    ----------
    name : str
        Header text.
    source : object | callable
        The value, or a zero-argument callable returning it.
    role : str
        Theme color role for its rows.
    start_open : bool
        Whether the header starts expanded.
    private : bool
        Include ``_name`` attributes of the watched value.

    Examples
    --------
    >>> from imgui_debugger.scopes import Watch
    >>> Watch("counters", lambda: {"frames": 3}).read()
    {'frames': 3}
    """

    name: str
    source: Any
    role: str = "name"
    start_open: bool = True
    private: bool = False

    def read(self):
        """Return the watched value, calling ``source`` when it is a callable.

        Examples
        --------
        >>> from imgui_debugger.scopes import Watch
        >>> Watch("n", 5).read()
        5
        """
        return self.source() if callable(self.source) else self.source

    def children(self) -> List[Child]:
        """Rows for the watched value this frame.

        Examples
        --------
        >>> from imgui_debugger.scopes import Watch
        >>> [c.name for c in Watch("m", {"a": 1}).children()]
        ['a']
        """
        try:
            return children_of(self.read(), self.private)
        except Exception as exc:
            return [Child(self.name, exc, "error")]

    def scope(self) -> Scope:
        """This watch as a :class:`Scope`.

        Examples
        --------
        >>> from imgui_debugger.scopes import Watch
        >>> Watch("m", {"a": 1}).scope().name
        'm'
        """
        return Scope(self.name, self.children, self.role, "watch", self.start_open)
