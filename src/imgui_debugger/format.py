"""One-line renderings of arbitrary Python values for the tree's right column.

Examples
--------
>>> from imgui_debugger.format import fmt_value, type_label
>>> fmt_value(3.5)
'3.5'
>>> type_label([1, 2, 3])
'list[3]'
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

MAX_STR = 256
MAX_INLINE = 8


def is_container(value) -> bool:
    """True when a value is a mapping or a non-string sequence.

    Examples
    --------
    >>> from imgui_debugger.format import is_container
    >>> is_container({"a": 1}), is_container("abc"), is_container([1])
    (True, False, True)
    """
    if isinstance(value, Mapping):
        return True
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def type_label(value) -> str:
    """The type name, with a length or shape suffix when the value has one.

    Examples
    --------
    >>> from imgui_debugger.format import type_label
    >>> type_label({"a": 1})
    'dict[1]'
    >>> type_label(2.0)
    'float'
    """
    name = type(value).__name__
    shape = getattr(value, "shape", None)
    if shape is not None and not callable(shape):
        try:
            return f"{name}{tuple(shape)}"
        except TypeError:
            return name
    if is_container(value):
        try:
            return f"{name}[{len(value)}]"
        except TypeError:
            return name
    return name


def fmt_value(value, max_str: int = MAX_STR) -> str:
    """Format a value as one short line, never raising on a hostile ``__repr__``.

    Parameters
    ----------
    value : object
        Anything.
    max_str : int
        Longest string rendered verbatim before truncation.

    Examples
    --------
    >>> from imgui_debugger.format import fmt_value
    >>> fmt_value(None), fmt_value(True), fmt_value(b"ab")
    ('None', 'True', '<2 bytes>')
    >>> fmt_value([1, 2, 3])
    '[1, 2, 3]'
    """
    if value is None or isinstance(value, bool):
        return repr(value)
    if isinstance(value, str):
        return repr(value if len(value) <= max_str else value[: max_str - 3] + "...")
    if isinstance(value, (int, float, complex)):
        return repr(value)
    if isinstance(value, (bytes, bytearray)):
        return f"<{len(value)} bytes>"
    if hasattr(value, "shape") and hasattr(value, "dtype"):
        return _fmt_array(value)
    if isinstance(value, (tuple, list, set, frozenset)):
        try:
            if len(value) <= MAX_INLINE and all(
                isinstance(v, (int, float, bool, str, type(None))) for v in value
            ):
                return repr(value)
            return f"<{type_label(value)}>"
        except TypeError:
            return f"<{type(value).__name__}>"
    if isinstance(value, Mapping):
        return f"<{type_label(value)}>"
    if callable(value):
        return f"<{type(value).__name__} {getattr(value, '__name__', '')}>".replace(" >", ">")
    return f"<{type(value).__name__}>"


def _fmt_array(value) -> str:
    """Summarize a numpy-like array, inlining only tiny scalar-dtype ones.

    Examples
    --------
    >>> import numpy as np                         # doctest: +SKIP
    >>> _fmt_array(np.zeros((4, 4)))               # doctest: +SKIP
    '<shape=(4, 4), dtype=float64>'
    """
    try:
        if value.size <= MAX_INLINE and getattr(value.dtype, "kind", "") in "biufcSU":
            return repr(value.tolist())
        return f"<shape={tuple(value.shape)}, dtype={value.dtype}>"
    except Exception:
        return f"<{type(value).__name__}>"


def fmt_error(exc: BaseException) -> str:
    """Format an exception raised while reading a value.

    Examples
    --------
    >>> from imgui_debugger.format import fmt_error
    >>> fmt_error(ValueError("bad shape"))
    '<ValueError: bad shape>'
    """
    return f"<{type(exc).__name__}: {exc}>"
