<h1 align="center">imgui_debugger</h1>

<p align="center">
<a href="https://pypi.org/project/imgui_debugger/"><img src="https://img.shields.io/pypi/v/imgui_debugger.svg" alt="PyPI version"></a>
<a href="https://pypi.org/project/imgui_debugger/"><img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python 3.10+"></a>
<a href="LICENSE"><img src="https://img.shields.io/pypi/l/imgui_debugger.svg" alt="License: MIT"></a>
</p>

<samp>
<p align="center">
A live <b>variable inspector</b> for any imgui-bundle widget
<br>
<br>
<a href="#install">install</a> ·
<a href="#quick-start">quick start</a> ·
<a href="#scopes">scopes</a> ·
<a href="#examples">examples</a> ·
<a href="#configuration-reference">configuration</a> ·
<a href="https://github.com/FlynnOConnell/imgui_debugger/issues">issues</a>
</p>
</samp>

## About

Point it at a widget and it draws every variable that widget can see, grouped by
scope, in a collapsible tree that re-reads its values every frame:

- **instance** — the object's own `__dict__` and `__slots__`
- **properties** — `property` descriptors, evaluated live; one that raises shows
  the exception instead of blanking the panel
- **class** — class attributes from the whole MRO
- **locals / globals** — the call frame you captured, so you can follow a draw
  method's own variables
- **imgui** — io, mouse, keyboard, the window rect and the style metrics that
  explain most layout bugs
- **watches** — anything else you promote to a top-level scope

Leaves that are a bool, number, string or color tuple get an inline editor that
writes straight back onto the object, so you can find the value that fixes the
layout without restarting the app.

It is built for widgets like the ones in
[mbo_utilities](https://github.com/MillerBrainObservatory/mbo_utilities) and
[masknmf-toolbox](https://github.com/apasarkar/masknmf-toolbox), but it knows
nothing about them — it works on any Python object.

## Install

```bash
pip install imgui_debugger
```

The only dependency is `imgui-bundle` (which provides imgui, hello_imgui,
immapp and the FontAwesome icon font).

## Quick start

Inspect one object in its own window, no host app needed:

```python
from imgui_debugger import run_debugger

run_debugger({"fs": 9.6, "dz": 5.0, "planes": [1, 2, 3]})
```

Add a debug window to a widget you already have:

```python
from imgui_debugger import attach

class RoiWidget:
    def __init__(self):
        self.threshold = 0.4
        self.debugger = attach(self, title="ROIs widget")

    def update(self):          # your per-frame draw
        ...
        self.debugger.capture()        # follow this method's locals
        self.debugger.render_window()  # draw the debug window
```

Or draw the tree inline, in a panel you already own:

```python
self.debugger.render()     # toolbar + tree at the current cursor
self.debugger.draw_tree()  # tree only, no toolbar
```

## Scopes

`Debugger.scopes()` returns them in display order: the target's
`instance` / `properties` / `class`, then your watches, then `locals` /
`globals`, then `imgui`.

| scope | source | writable |
|-------|--------|----------|
| `instance` | `vars(obj)` + `__slots__` | yes |
| `properties` | `property` / `cached_property` on the MRO | only with an `fset` |
| `class` | class attributes, no methods or descriptors | yes |
| `locals` | the captured frame's `f_locals` | no (writes do not stick) |
| `globals` | the captured frame's `f_globals` | yes |
| `imgui` | `io`, `mouse`, `keyboard`, `window`, `style` | no |
| watches | `watch(name, value_or_callable)` | depends on the value |

A watch takes a value or a zero-argument callable; the callable is re-read every
frame, so `watch("metadata", lambda: self.metadata)` survives the attribute
being reassigned:

```python
dbg.watch("metadata", lambda: self.metadata, role="prop")
dbg.watch("fps", lambda: {"now": imgui.get_io().framerate}, role="runtime")
```

`watch_all(obj, ["metadata", "indices"])` does the same for several attributes
in one call.

## Toolbar

| control | what it does |
|---------|--------------|
| filter | case-insensitive match over names and leaf values, recursing into children (bounded to 6 levels and 64 items per container, memoized per filter string) |
| expand / collapse | force every node open or shut for one frame |
| private | include `_name` attributes |
| edit | turn the inline editors off and read only |

## Examples

See all examples in [`examples/`](examples/).

| name | file | what it shows |
|------|------|---------------|
| debug_minimal | [`debug_minimal.py`](examples/debug_minimal.py) | one-shot window over a settings dataclass |
| debug_widget | [`debug_widget.py`](examples/debug_widget.py) | a widget that owns its debugger, captures its own locals, and toggles it with F12 |
| debug_edge_window | [`debug_edge_window.py`](examples/debug_edge_window.py) | a fastplotlib `EdgeWindow`, the widget shape pml_utilities and masknmf-toolbox use |

## Configuration reference

`DebuggerConfig` fields:

| field | default | purpose |
|-------|---------|---------|
| `target` | `None` | the object whose scopes come first |
| `title` | `"Debugger"` | header text and default window title |
| `theme` | `Theme.dark()` | colors |
| `private` | `False` | show `_name` attributes |
| `properties` | `True` | show the `properties` scope and expand nested properties |
| `class_attrs` | `True` | show the `class` scope |
| `editable` | `True` | inline editors for writable leaves |
| `show_frame` | `True` | show `locals` / `globals` |
| `show_runtime` | `True` | show the live `imgui` scope |
| `max_depth` | `8` | deepest level the tree expands |
| `max_items` | `200` | rows per container before "+N more" |
| `value_col` | `0.0` | pixel column values align at; `0` packs them after the name |
| `show_toolbar` | `True` | draw the filter box and toggles |
| `window_title`, `window_size`, `resizable` | — | OS window (one-shot mode) |
| `ini_path` | `~/.imgui_debugger/debugger.ini` | where the layout `.ini` is saved |
| `assets_folder` | `None` | folder providing the icon font; unset never overrides a host app's |

`attach(target, **kwargs)` and `run_debugger(target, **kwargs)` take any of
these as keyword arguments.

## Files on disk

Everything the library writes lives under `~/.imgui_debugger/` (override with
the `IMGUI_DEBUGGER_HOME` env var):

| path | written by | purpose |
|------|-----------|---------|
| `~/.imgui_debugger/debugger.ini` | `run_debugger` | hello_imgui window layout. Override with `config.ini_path`; an embedding app's own `ini_filename` always wins. |
| `~/.imgui_debugger/assets/` | you (optional) | user assets folder. Never created automatically; added to hello_imgui's search path when the icon font cannot be resolved. |

Embedded use writes nothing: `render()` and `render_window()` only draw.

## Notes

- Reads are guarded. A property that raises, a `__repr__` that raises, and a
  container that changes size mid-frame all render as a row rather than
  crashing the frame.
- Values are read fresh every frame, so the tree shows the state of the frame
  you are looking at.
- Big containers are capped, not truncated silently: a "+N more" line says how
  many rows were left out.
- Editing writes through the same setter the row was built from — `setattr` for
  an attribute, `__setitem__` for a dict or list entry, the property's `fset`
  for a property.

## Acknowledgements

The tree rendering, the bounded memoized filter and the value formatting come
from the metadata inspector in
[mbo_utilities](https://github.com/MillerBrainObservatory/mbo_utilities) at the
[Miller Brain Observatory](https://github.com/MillerBrainObservatory). The
packaging, theming and one-shot harness follow
[imgui_data_loader](https://github.com/FlynnOConnell/imgui_data_loader).

## License

MIT
