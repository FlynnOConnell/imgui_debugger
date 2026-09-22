# Architecture

Internal notes for contributors to `imgui_debugger`.

## What this is

`imgui_debugger` is a set of **standalone debug panels** for
[imgui-bundle](https://github.com/pthom/imgui_bundle). Two are ours — a live
variable inspector and a style editor with pluggable Save / Load — and the rest
wrap imgui's own debug windows so none of them require the demo window. Every
panel shares one surface (`visible`, `menu_item`, `render`, `render_window`) and
one config base, so a host app wires them in the same way and can configure,
replace or ignore any of them. The only runtime dependency is `imgui-bundle`.

## Commands

```bash
uv venv && uv pip install -e '.[dev]'
pytest                              # the full suite (testpaths=tests)
pytest tests/test_scopes.py         # one file
pytest tests/test_headless_render.py -q
python -m doctest src/imgui_debugger/scopes.py -v   # docstring examples
```

There is no configured linter/formatter. The package ships `py.typed`, so keep
type hints intact.

## Architecture

Three layers, in dependency order. Nothing below imports anything above it.

**1. Model — GUI-free, no imgui context needed.**

- `scopes.py` — the whole data model. A `Child` is one row: name, the value as
  read this frame, a `kind` (`attr` / `prop` / `class` / `item` / `index` /
  `local` / `global` / `error`), and a `setter` that writes it back or `None`.
  A `Scope` is a named root holding a `children()` callable, called once per
  frame. `children_of` is the one dispatch point: mappings and sequences expand
  into items, everything else into instance attributes plus properties. Setters
  are `functools.partial`, never closures, so the module has no nested
  functions. Every read of a user value goes through `_read`, which turns a
  raising getter into an `error` row — a property that blows up must not blank
  the panel.
- `format.py` — one short line per value, total over every input. A hostile
  `__repr__`, an object array, a 4 MB string: all render. Nothing here raises.
- `search.py` — the filter. The walk is capped at `MAX_DEPTH` levels and
  `MAX_ITEMS` children per container and memoized per filter string, because an
  unbounded walk over a multi-megabyte attribute dict cost hundreds of
  milliseconds *per frame* in the viewer this came from. The cache key is
  `(name, id(value), depth)` and each entry also holds the value: the reference
  keeps live ids from being recycled, and the `is` check rejects an entry whose
  object died and whose id was reused. `depth` is in the key because the walk is
  depth-bounded, so a `False` cached at max depth must not answer a near-root
  query for the same object.

**2. View — draws, holds no state.**

- `theme.py` — `Theme`, a frozen dataclass of `(r,g,b,a)` tuples plus rounding.
  Colors become `imgui.ImVec4` lazily at draw time, so a theme is context-free.
  A `Child.kind` maps to a theme field through `tree.ROLE_COLORS`.
- `tree.py` — `TreeStyle` (theme + filter + limits + `force_open`) and the three
  draw functions: `draw_scope`, `draw_children`, `draw_child`. `draw_child`
  decides expandable-or-leaf by asking `has_children`, and recurses by calling
  `children_of` again — the tree never materializes more than the rows it draws.
  imgui ids come from the dotted path, so two rows with the same name in
  different branches do not collide.
- `edit.py` — the inline editors. `can_edit` gates on type: bool, int, float,
  short str, and an `(r,g,b[,a])` float tuple. A failing setter is swallowed and
  reported as "not changed" rather than raising inside a frame.
- `style.py` — the standalone style editor. Independent of the debugger: it
  imports `theme` and `_assets` and nothing else in the package, so a host can
  use it without ever building a `Debugger`. `imgui.show_style_editor()` cannot
  be had without its Save Ref / Revert Ref / Export buttons, so this draws the
  same three tabs itself and routes its two buttons through `on_save` /
  `on_load` callbacks. `style_to_dict` reflects over `imgui.Style`'s
  `property` descriptors rather than a hand-kept field list, so a new imgui
  field serializes without an edit here; `SKIP_KEYS` holds the two that must
  not travel between machines (`font_scale_dpi`, `font_size_base` are derived
  from the screen at runtime). `apply_style_dict` ignores unknown keys, which
  is what makes an older file still load.

**3. Controller — owns state, drives the view.**

- `panel.py` — `Panel`, `PanelConfig` and `Hotkey`. The base every tool
  subclasses: it owns `visible`, draws the menu entry, polls the hotkey and
  begins/ends the window, leaving subclasses only `render()`. `window_id` is
  `title##imgui_debugger_<window_id or class name>` so renaming a title keeps
  the layout imgui saved under that id. `render_window` polls the hotkey
  *before* the visibility check, which is what lets a hotkey reopen a closed
  panel. `Panel.render` raises, so a window-only panel is honest about it
  rather than silently drawing nothing.
- `native.py` — imgui's own debug windows as panels. `NativeWindowPanel`
  overrides `render_window` to call `imgui.show_*_window(True)` and feed the
  returned open state back into `visible`; imgui owns the window and its title,
  so the config's title is only the menu label. `UserGuidePanel` is the one
  that can be inlined, because `show_user_guide()` draws no window of its own.
  `DemoPanel` exists but is not in `DebugTools.default()`.
- `store.py` — `ConfigStore`, one directory holding `state.json` (the style as
  last left, per-panel state, the active preset), `styles/<name>.json` (named
  presets) and `layout.ini`. Every method is guarded and returns an empty
  value or `False` rather than raising, because callers are inside a frame. The
  root is created on the first write, never on construction, so building a
  store costs nothing. Window geometry is deliberately not stored here: imgui
  already persists it through the `.ini`, and a second mechanism would fight
  it. The import of `style` is function-local, to keep `store` free of the
  imgui-context-dependent code path.
- `tools.py` — `DebugTools`, an ordered list of panels with `draw_menu`,
  `render`, and add/remove/lookup by title. It holds no drawing of its own; it
  is the one place a host app touches to get everything at once.
- `debugger.py` — `DebuggerConfig` (pure data) and `Debugger`. `scopes()`
  assembles the frame's roots in display order: target scopes, watches, frame
  scopes, runtime. `render()` draws the toolbar and the tree; `render_window()`
  wraps it in its own imgui window and honors `visible`. `expand_all` /
  `collapse_all` set `_force_open` for exactly one frame, cleared at the end of
  `render`.
- `runner.py` — the one-shot harnesses: `run_debugger` for the inspector and
  `run_panel` for any panel. Note the `.ini` handling: hello_imgui otherwise
  drops the window-layout `.ini` in the cwd, so both pin it to an absolute path
  (`config.ini_path` or `default_ini_path()`) and create the parent dir. They
  only fill `ini_filename` when unset, so an embedding app's choice wins.
  `run_panel` picks `render` or `render_window` by asking whether the subclass
  overrode `render`, so a native window-only panel still works.
- `_assets.py` — per-user paths and font resolution. Everything the library
  writes lives under `data_dir()` = `~/.imgui_debugger` (env override
  `IMGUI_DEBUGGER_HOME`). `ensure_assets()` is deliberately non-clobbering: it
  no-ops when the icon font already resolves and otherwise *adds* search paths,
  so a host app's own `set_assets_folder` survives. Only an explicit
  `assets_folder` replaces the folder. The library ships no fonts of its own.

## Frame capture

`Debugger.capture(depth)` stores `sys._getframe(depth)`. The constructor
captures the caller; `attach` passes `frame_depth=2` so it captures the caller
of `attach`, not `attach` itself. Calling `capture()` again from inside a draw
method re-points the `locals` scope at that method, which is the useful case —
a frame's `f_locals` is a live view while the frame is alive.

Locals are read-only on purpose: writing `f_locals` does not stick in CPython
before PEP 667, so offering an editor there would lie. Globals are writable.

## Embedding

Three entry points, and which one a host uses is the host's choice:

- `panel.render()` draws at the current cursor (a tab, a dock node, a sidebar).
- `panel.render_window()` opens its own imgui window, polls the hotkey and
  flips `visible` when the user closes it.
- `tools.draw_menu()` + `tools.render()` does all of the above for a whole set.

`run_debugger` and `run_panel` are for poking at something with no host app at
all. They own the immapp loop and block.

A host app should never need to edit this package to add a tool: subclass
`Panel`, implement `render`, and `DebugTools.add` it.

## Testing notes

Rendering is exercised headlessly on hello_imgui's **null backend** (no window
or GPU) — see `_null_runner_params()` in `tests/test_headless_render.py`. Two
gotchas that pattern encodes: the null renderer needs
`BackendFlags_.renderer_has_textures` set in `post_init` (imgui 1.92 asserts
otherwise), and tests must route the `.ini` to a temp folder. If the backend
cannot init in the environment, those tests **skip** rather than fail, so a
green run may mean "skipped" — check the output. Everything in the model layer
is pure and always runs.

The headless tests drive the real toolbar path across five frames — filter set,
filter cleared, expand, collapse, `private` flipped — because those are the
branches that only exist inside a live frame.

Every public docstring carries a runnable `Examples` block; the ones that need
a live imgui context are marked `# doctest: +SKIP`. `python -m doctest` over the
`src` modules is a cheap second suite.
