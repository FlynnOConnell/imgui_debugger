# Architecture

Internal notes for contributors to `imgui_debugger`.

## What this is

`imgui_debugger` renders a **live variable inspector** for
[imgui-bundle](https://github.com/pthom/imgui_bundle): a collapsible tree of
everything an object can see, grouped by scope, re-read every frame, with
inline editors on the leaves that can be written back. The only runtime
dependency is `imgui-bundle`. It knows nothing about any host app; a target is
any Python object.

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

**3. Controller — owns state, drives the view.**

- `debugger.py` — `DebuggerConfig` (pure data) and `Debugger`. `scopes()`
  assembles the frame's roots in display order: target scopes, watches, frame
  scopes, runtime. `render()` draws the toolbar and the tree; `render_window()`
  wraps it in its own imgui window and honors `visible`. `expand_all` /
  `collapse_all` set `_force_open` for exactly one frame, cleared at the end of
  `render`.
- `runner.py` — the one-shot harness only. Note the `.ini` handling:
  hello_imgui otherwise drops the window-layout `.ini` in the cwd, so
  `run_debugger` pins it to an absolute path (`config.ini_path` or
  `default_ini_path()`) and creates the parent dir. It only fills `ini_filename`
  when unset, so an embedding app's choice wins.
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

Two entry points, and which one a host uses is the host's choice:

- `dbg.render()` draws at the current cursor (a panel, a tab, a dock window).
- `dbg.render_window()` opens its own imgui window and flips `visible` when the
  user closes it, so a menu item or a hotkey can call `toggle()`.

`run_debugger` is for poking at an object with no host app at all. It owns the
immapp loop and blocks.

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
