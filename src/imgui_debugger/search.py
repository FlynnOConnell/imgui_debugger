"""The tree's filter: a bounded, memoized match over a value and its children.

The walk is capped in width and depth so a multi-megabyte attribute dict cannot
cost milliseconds per frame, and results are cached for the lifetime of one
filter string.

Examples
--------
>>> from imgui_debugger.search import matches
>>> matches("metadata", {"fs": 9.6}, "fs")
True
>>> matches("metadata", {"fs": 9.6}, "dz")
False
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

MAX_ITEMS = 64
MAX_DEPTH = 6
CACHE_MAX = 4096

_cache: dict = {}
_cache_filter: str | None = None


def clear_cache() -> None:
    """Drop every memoized match result.

    Examples
    --------
    >>> from imgui_debugger.search import clear_cache, matches
    >>> matches("a", 1, "a")
    True
    >>> clear_cache()
    """
    global _cache_filter
    _cache.clear()
    _cache_filter = None


def matches_shallow(name, value, text: str) -> bool:
    """Whether a name, or a non-container value, contains ``text``.

    Parameters
    ----------
    name : object
        The row label.
    value : object
        The row value.
    text : str
        Filter text; an empty string matches everything.

    Examples
    --------
    >>> from imgui_debugger.search import matches_shallow
    >>> matches_shallow("frame_rate", 30, "rate")
    True
    >>> matches_shallow("frame_rate", 30, "30")
    True
    >>> matches_shallow("frame_rate", [30], "30")
    False
    """
    if not text:
        return True
    low = text.lower()
    if low in str(name).lower():
        return True
    if isinstance(value, (Mapping, list, tuple)):
        return False
    try:
        return low in str(value).lower()
    except Exception:
        return False


def matches(name, value, text: str, depth: int = 0) -> bool:
    """Whether a row or any of its bounded descendants matches ``text``.

    Parameters
    ----------
    name : object
        The row label.
    value : object
        The row value.
    text : str
        Filter text; an empty string matches everything.
    depth : int
        Current recursion depth, used internally.

    Examples
    --------
    >>> from imgui_debugger.search import matches
    >>> matches("arr", {"meta": {"dz": 5}}, "dz")
    True
    >>> matches("arr", [1, 2, 3], "2")
    True
    >>> matches("arr", "hello", "ell")
    True
    """
    global _cache_filter
    if not text:
        return True
    if text != _cache_filter:
        _cache.clear()
        _cache_filter = text
    key = (str(name), id(value), depth)
    hit = _cache.get(key)
    if hit is not None and hit[0] is value:
        return hit[1]
    result = _walk(name, value, text, depth)
    if len(_cache) >= CACHE_MAX:
        _cache.clear()
    _cache[key] = (value, result)
    return result


def _walk(name, value, text: str, depth: int) -> bool:
    """Do the bounded recursive match behind :func:`matches`.

    Examples
    --------
    >>> from imgui_debugger.search import _walk
    >>> _walk("cfg", {"a": {"b": 1}}, "b", 0)
    True
    >>> _walk("cfg", {"a": {"b": 1}}, "b", 6)
    False
    """
    if matches_shallow(name, value, text):
        return True
    if depth >= MAX_DEPTH:
        return False
    if isinstance(value, Mapping):
        for i, (k, v) in enumerate(value.items()):
            if i >= MAX_ITEMS:
                break
            if matches(k, v, text, depth + 1):
                return True
        return False
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for i, v in enumerate(value):
            if i >= MAX_ITEMS:
                break
            if matches(f"[{i}]", v, text, depth + 1):
                return True
    return False


def filter_children(children, text: str):
    """Keep only the rows that match ``text``.

    Parameters
    ----------
    children : list[imgui_debugger.scopes.Child]
        Rows to filter.
    text : str
        Filter text; an empty string keeps everything.

    Examples
    --------
    >>> from imgui_debugger.scopes import Child
    >>> from imgui_debugger.search import filter_children
    >>> rows = [Child("fs", 9.6), Child("dz", 5)]
    >>> [c.name for c in filter_children(rows, "dz")]
    ['dz']
    """
    if not text:
        return list(children)
    return [c for c in children if matches(c.name, c.value, text)]
