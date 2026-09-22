<h1 align="center">imgui_debugger</h1>

<p align="center">
<a href="https://pypi.org/project/imgui_debugger/"><img src="https://img.shields.io/pypi/v/imgui_debugger.svg" alt="PyPI version"></a>
<a href="https://pypi.org/project/imgui_debugger/"><img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python 3.10+"></a>
<a href="LICENSE"><img src="https://img.shields.io/pypi/l/imgui_debugger.svg" alt="License: MIT"></a>
</p>

<samp>
<p align="center">
Standalone, configurable <b>debug panels</b> for imgui-bundle apps
<br>
<br>
<a href="#install">install</a> ·
<a href="#the-panels">panels</a> ·
<a href="#the-widgets">widgets</a> ·
<a href="#one-menu-for-everything">one menu</a> ·
<a href="#variable-inspector">inspector</a> ·
<a href="#style-editor">style editor</a> ·
<a href="#saving-and-auto-loading">saving</a> ·
<a href="#examples">examples</a> ·
<a href="#configuration-reference">configuration</a> ·
<a href="https://github.com/FlynnOConnell/imgui_debugger/issues">issues</a>
</p>
</samp>

## About

Every debugging tool imgui offers normally hangs off the demo window's Tools
menu. This package unbundles them: each tool is an independent, configurable
panel you can drop into your own app, on your own menu, with your own
shortcuts — plus a live variable inspector and a style editor whose Save and
Load are yours.

Nothing here needs the demo window, and nothing here depends on anything else
here: import one panel, or take the whole set.

| panel | what it shows | comes from |
|-------|---------------|------------|
| `Debugger` | every variable your widget can see, by scope, live | this package |
| `StyleEditor` | sizes, colors, rendering, with pluggable Save / Load | this package |
| `MetricsPanel` | windows, draw lists, viewports, internal state | imgui |
| `DebugLogPanel` | focus, nav, docking and IO events as they happen | imgui |
| `IdStackPanel` | what an item's id is built from, for id collisions | imgui |
| `AboutPanel` | version and the build's enabled features | imgui |
| `UserGuidePanel` | imgui's built-in control reference | imgui |
| `DemoPanel` | the demo window, if you ever want it — opt-in only | imgui |

Built for widgets like the ones in
[mbo_utilities](https://github.com/MillerBrainObservatory/mbo_utilities) and
[masknmf-toolbox](https://github.com/apasarkar/masknmf-toolbox), but it knows
nothing about them — a target is any Python object.

## Install

```bash
pip install imgui_debugger
```

Dependencies are `imgui-bundle` (imgui, implot, hello_imgui, immapp and the
FontAwesome icon font) and `numpy`.

## The panels

Every panel — including ones you write — has the same four-part surface:

```python
panel.visible                  # bool you can set, bind, or persist
panel.menu_item()              # a checked menu entry bound to visible
panel.render()                 # the body, at the current cursor, no window
panel.render_window()          # the body in its own window; polls the hotkey
```

so wiring one into a host app is two lines:

```python
def draw_menu(self):
    if imgui.begin_menu("View"):
        self.editor.menu_item()       # or menu_item("Theme", "Ctrl+T")
        imgui.end_menu()

def draw(self):
    ...
    self.editor.render_window()
```

`render()` is there for when you would rather host the body yourself — in a tab,
a dock node, or a sidebar you already own. imgui's own windows (`MetricsPanel`
and friends) are window-only and say so by raising from `render()`.

Configuration is a dataclass per panel, all sharing `PanelConfig`:

```python
from imgui_bundle import imgui
from imgui_debugger import Hotkey, StyleEditor, StyleEditorConfig

editor = StyleEditor(StyleEditorConfig(
    title="Theme",                          # window title + menu label
    visible=False,                          # starts closed
    hotkey=Hotkey(imgui.Key.t, ctrl=True),  # Ctrl+T toggles it; the menu says so
    window_size=(520, 700),
    show_sizes=False,                       # StyleEditor's own knobs
    on_save=my_app.save_style,
))
```

To show one on its own, with no host app at all:

```python
from imgui_debugger import run_panel
run_panel(StyleEditor())
run_panel(MetricsPanel())
```

Writing your own panel is a subclass and a `render`:

```python
from imgui_debugger import Panel, PanelConfig

class Timings(Panel):
    config_class = PanelConfig

    def render(self):
        imgui.text(f"{imgui.get_io().framerate:.0f} fps")
```

## The widgets

Beside the panels, the package ships the imgui widgets that had been copied
between repos. Each one is the merge of the copies, not a new invention:

| widget | what it is | came from |
|--------|------------|-----------|
| `RoiOrder` + `draw_table` | filter, stable sort, clipped table with row actions | both repos' `table.py`, which had diverged |
| `TracePlot` | stacked implot panels, linked x, draggable playhead, min/max decimation | `masknmf…imgui.trace_plot` |
| `MoviePlayer` | play/pause, frame slider, fps, lazy cropped reads | both repos' `movie_player.py` |
| `KeybindsPanel`, `draw_path_popup` | the key reference and the path prompt | both repos' `panels.py` |
| `em`, `card`, `section`, `grid`, `help_mark`, `right_aligned_text`, `button_colors`, `popup` | the layout and styling helpers the panels are built from | `masknmf…imgui.theme` and `mbo_utilities.gui._theme` |

```python
from imgui_debugger import RoiOrder, draw_table, draw_filter_row

order = RoiOrder({"area": areas, "snr": snr}, n_rois, labels=labels)
order.set_range_column("snr")

draw_filter_row(order)
scroll = draw_table(
    order, ["id", "area", "snr"],
    {"area": lambda i: f"{areas[i]:.0f}", "snr": lambda i: f"{snr[i]:.2f}"},
    scroll, on_select=viewer.select,
    actions=(RowAction("x", "delete", viewer.delete),),
)
```

`RoiOrder` is the union of the two copies: masknmf's name-based sort, pinned
column, float ranges, `prefix_rows` and row colours, plus mbo's label filtering,
row action buttons, `next_unlabeled` and `step_group`. A feature you do not use
costs nothing — `labels=None` hides the label filter, no `actions` means no
extra column.

`TracePlot` keeps its fastplotlib hooks (`dock`, `link`) but imports
fastplotlib inside those two methods, so the plot works in an app that does not
have it.

## One menu for everything

`DebugTools` is an ordered set of panels with one menu and one per-frame call:

```python
from imgui_debugger import DebugTools, Hotkey

self.tools = DebugTools.default(self, menu_label="Debug")
self.tools["Debugger"].config.hotkey = Hotkey(imgui.Key.f12)

def draw_menu(self):
    self.tools.draw_menu()        # or draw_menu_items() inside your own menu

def draw(self):
    ...
    self.tools.render()           # every open panel, every hotkey
```

`DebugTools.default()` gives the inspector, the style editor, metrics, the debug
log and the ID stack tool, all starting closed. The demo window is deliberately
left out. The set is editable — `add`, `remove`, `tools["title"]`, `show_all`,
`hide_all`, `visible()` — so you can swap the style editor for one configured
your way, or register a panel of your own beside them.

## Variable inspector

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
writes straight back onto the object.

```python
from imgui_debugger import attach

class RoiWidget:
    def __init__(self):
        self.threshold = 0.4
        self.debugger = attach(self, title="ROIs widget")

    def update(self):          # your per-frame draw
        ...
        self.debugger.capture()        # follow this method's locals
        self.debugger.render_window()
```

Or inspect one object with no host app:

```python
from imgui_debugger import run_debugger
run_debugger({"fs": 9.6, "dz": 5.0, "planes": [1, 2, 3]})
```

### Scopes

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
frame, so it survives the attribute being reassigned:

```python
dbg.watch("metadata", lambda: self.metadata, role="prop")
dbg.watch("fps", lambda: {"now": imgui.get_io().framerate}, role="runtime")
```

`watch_all(obj, ["metadata", "indices"])` does the same for several attributes
in one call.

### Toolbar

| control | what it does |
|---------|--------------|
| filter | case-insensitive match over names and leaf values, recursing into children (bounded to 6 levels and 64 items per container, memoized per filter string) |
| expand / collapse | force every node open or shut for one frame |
| private | include `_name` attributes |
| edit | turn the inline editors off and read only |

## Style editor

`StyleEditor` is the imgui demo's style editor with its Save Ref / Revert Ref /
Export buttons replaced by two of yours. `imgui.show_style_editor()` cannot be
drawn without those buttons, and they only manage an in-memory reference style —
nothing they do touches disk — so this draws the tabs itself.

```python
from imgui_debugger import StyleEditor, StyleEditorConfig

editor = StyleEditor(StyleEditorConfig(
    title="Theme",
    visible=False,
    save_label="Save to settings",
    load_label="Load from settings",
    on_save=my_app.save_style,   # on_save(data: dict)
    on_load=my_app.load_style,   # on_load() -> dict | None
))
```

With no `on_save` / `on_load`, the buttons fall back to reading and writing
`config.path` as JSON (`~/.imgui_debugger/style.json` when that is unset too).
`on_load` returning `None` is a cancel — that is how a native file dialog the
user dismissed reports back. Errors from either hook land on the editor's status
line instead of raising inside a frame.

The body is configurable: `show_sizes`, `show_colors` and `show_rendering` pick
the tabs (one tab alone is drawn without a tab bar), `show_font_selector` and
`show_style_selector` add imgui's own pickers, `size_groups` replaces the Sizes
tab's fields entirely, and `extra_draw(editor)` slots your own controls under the
toolbar. Presets apply `style_colors_dark` / `_light` / `_classic`; Revert
restores the style as it was when the editor was constructed.

The serialization is usable on its own:

| function | does |
|----------|------|
| `style_to_dict(style=None)` | `{"sizes": {...}, "colors": {name: [r,g,b,a]}}` |
| `apply_style_dict(data, style=None)` | writes it back, returns how many fields landed |
| `save_style(path=None, style=None)` | `style_to_dict` to JSON |
| `load_style(path=None, style=None)` | JSON to `apply_style_dict` |

Colors are keyed by imgui's own names (`Text`, `FrameBg`, ...), and unknown keys
are ignored, so a file written against an older imgui still loads. Two fields are
deliberately not serialized: `font_scale_dpi` and `font_size_base` are derived
from the screen at runtime, and restoring another machine's values resizes every
font for the wrong display.

## Saving and auto-loading

`ConfigStore` is one directory holding everything this package remembers. Point
it at wherever your app already keeps settings:

```python
from imgui_debugger import ConfigStore, DebugTools

STORE = ConfigStore(get_mbo_dirs()["imgui"])       # or Path.home() / ".my_app/imgui"
tools = DebugTools.default(self, store=STORE)
tools.load_state()                                  # which panels were open, how
```

then three calls at the app's edges:

```python
params.ini_filename = STORE.layout_ini              # window size/position
params.ini_folder_type = hello_imgui.IniFolderType.absolute_path
params.callbacks.post_init = tools.apply_style      # the style, at startup
params.callbacks.before_exit = tools.save_state     # panel state, at exit
```

| path under the store root | holds |
|---------------------------|-------|
| `state.json` | the style as it was left, each panel's state, the active preset |
| `styles/<name>.json` | one named preset per file |
| `layout.ini` | hello_imgui's window geometry |

**The style saves itself.** With a store, the editor marks itself dirty the
moment a slider or a color moves and writes `state.json` once the changes stop
(`autosave_delay`, one second by default). `tools.apply_style()` puts it back at
the next launch. Set `autosave=False` to keep it on the Save button only.

**Named presets** are the row under the toolbar: a dropdown of what is in
`styles/`, a name field, Save as, and Delete. Loading one applies it and records
it as active, so the dropdown opens on it next time. Save as writes the *current*
style, which is whatever the sliders say — the autosave and the presets do not
fight over the same file.

**Panel state** is `visible` plus each panel's own config fields
(`Panel.state_fields`): the inspector's `private`, `editable`, `max_depth`,
`value_col`, …; the style editor's tab switches. Window size and position are
deliberately *not* in there — those are imgui's to persist, which is what
`layout_ini` is for.

Every store call is guarded: a missing directory, a half-written file or a
read-only disk gives an empty dict or `False`, never an exception inside a
frame. The directory is created on the first write, not on construction.

`ConfigStore` is also usable directly — `read_state`, `write_state`,
`update_state`, `style`, `set_style`, `presets`, `read_preset`, `write_preset`,
`delete_preset`, `active_preset`, `set_active_preset`, `panel_state`,
`set_panel_state`, `apply_style`.

## Examples

See all examples in [`examples/`](examples/).

| name | file | what it shows |
|------|------|---------------|
| debug_minimal | [`debug_minimal.py`](examples/debug_minimal.py) | one-shot window over a settings dataclass |
| roi_viewer | [`roi_viewer.py`](examples/roi_viewer.py) | a whole ROI viewer built only from the ported widgets, with the inspector attached |
| debug_edge_window | [`debug_edge_window.py`](examples/debug_edge_window.py) | the same table and trace plot inside a fastplotlib `EdgeWindow`, the shape pml_utilities and masknmf-toolbox use |
| style_editor_menu | [`style_editor_menu.py`](examples/style_editor_menu.py) | the style editor alone, on a menu, saving into the app's own settings file |
| debug_tools_menu | [`debug_tools_menu.py`](examples/debug_tools_menu.py) | the whole set behind one menu, with hotkeys, a `ConfigStore` and auto-loaded style |

## Configuration reference

### `PanelConfig` — every panel takes these

| field | default | purpose |
|-------|---------|---------|
| `title` | per panel | window title and default menu label |
| `visible` | `True` | whether it starts open |
| `window_id` | `""` | stable imgui id suffix; the class name when empty, so renaming the title keeps the saved layout |
| `window_size` | `(0, 0)` | first-use size; `(0, 0)` sizes to content |
| `window_pos` | `None` | first-use position |
| `window_flags` | `0` | `imgui.WindowFlags_` bits |
| `closable` | `True` | draw the close button and clear `visible` with it |
| `shortcut` | `""` | menu shortcut text; the hotkey's text when empty |
| `hotkey` | `None` | `Hotkey(key, ctrl=, shift=, alt=)` that toggles the panel |
| `theme` | `Theme.dark()` | palette for what the panel draws itself |

### `DebuggerConfig` — plus the above

| field | default | purpose |
|-------|---------|---------|
| `target` | `None` | the object whose scopes come first |
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
| `show_title` | `True` | draw the title line inside the body |
| `os_window_title`, `resizable`, `ini_path`, `assets_folder` | — | one-shot `run_debugger` only |

### `StyleEditorConfig` — plus `PanelConfig`

| field | default | purpose |
|-------|---------|---------|
| `on_save` | `None` | `on_save(data)`; falls back to writing `path` |
| `on_load` | `None` | `on_load() -> dict \| None`; falls back to reading `path` |
| `path` | `None` | file used by the fallback Save / Load |
| `save_label`, `load_label` | `"Save"`, `"Load"` | button text |
| `show_presets`, `show_revert` | `True` | the preset buttons and Revert |
| `show_sizes`, `show_colors`, `show_rendering` | `True` | which tabs to draw |
| `show_font_selector`, `show_style_selector` | `False` | imgui's own pickers above the tabs |
| `store` | `None` | a `ConfigStore` backing Save, Load, presets and autosave |
| `autosave`, `autosave_delay` | `True`, `1.0` | write the style back once it stops changing |
| `show_preset_bar` | `True` | the named-preset row; needs a store |
| `size_groups` | `None` | replace the Sizes tab's field groups |
| `extra_draw` | `None` | `extra_draw(editor)` under the toolbar |

`attach(target, **kwargs)` and `run_debugger(target, **kwargs)` take any
`DebuggerConfig` field as a keyword argument.

## Files on disk

Everything the library writes lives under `~/.imgui_debugger/` (override with
the `IMGUI_DEBUGGER_HOME` env var):

| path | written by | purpose |
|------|-----------|---------|
| `~/.imgui_debugger/debugger.ini`, `panel.ini` | `run_debugger`, `run_panel` | hello_imgui window layout. Override per call; an embedding app's own `ini_filename` always wins. |
| `~/.imgui_debugger/style.json` | `save_style` with no path | the fallback style file |
| `<store root>/state.json`, `styles/`, `layout.ini` | `ConfigStore` | style, presets, panel state, window geometry |
| `~/.imgui_debugger/assets/` | you (optional) | user assets folder, added to hello_imgui's search path when the icon font cannot be resolved |

Embedded use writes nothing: `render()` and `render_window()` only draw.

## Notes

- Reads are guarded. A property that raises, a `__repr__` that raises, and a
  container that changes size mid-frame all render as a row rather than crashing
  the frame.
- Big containers are capped, not truncated silently: a "+N more" line says how
  many rows were left out.
- Editing writes through the same setter the row was built from — `setattr` for
  an attribute, `__setitem__` for a dict or list entry, the property's `fset` for
  a property.

## Acknowledgements

The tree rendering, the bounded memoized filter and the value formatting come
from the metadata inspector in
[mbo_utilities](https://github.com/MillerBrainObservatory/mbo_utilities) at the
[Miller Brain Observatory](https://github.com/MillerBrainObservatory). The
packaging, theming and one-shot harness follow
[imgui_data_loader](https://github.com/FlynnOConnell/imgui_data_loader).

## License

MIT
