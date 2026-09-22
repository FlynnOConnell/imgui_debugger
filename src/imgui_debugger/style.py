"""A standalone imgui style editor whose Save and Load buttons are yours.

The demo's editor hardcodes Save Ref / Revert Ref and an export-to-clipboard
button. This one draws the same sizes, colors and rendering controls but routes
its two buttons through callbacks, so a host app can persist the style wherever
it already keeps settings.

Examples
--------
>>> from imgui_debugger import StyleEditor, StyleEditorConfig
>>> editor = StyleEditor(StyleEditorConfig(path="my_style.json"))
>>> editor.visible = False
>>> editor.menu_item()          # doctest: +SKIP
>>> editor.render_window()      # doctest: +SKIP
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple, Union

from imgui_bundle import imgui

from ._assets import data_dir
from .panel import Panel, PanelConfig
from .store import ConfigStore
from .theme import to_vec4

# dpi-derived; another machine's values resize every font for the wrong screen
SKIP_KEYS = ("font_scale_dpi", "font_size_base")

DIR_ITEMS = ("none", "left", "right", "up", "down")

SIZE_GROUPS = (
    (
        "Main",
        (
            ("window_padding", 0.0, 20.0),
            ("frame_padding", 0.0, 20.0),
            ("item_spacing", 0.0, 20.0),
            ("item_inner_spacing", 0.0, 20.0),
            ("touch_extra_padding", 0.0, 10.0),
            ("indent_spacing", 0.0, 30.0),
            ("scrollbar_size", 1.0, 20.0),
            ("grab_min_size", 1.0, 20.0),
        ),
    ),
    (
        "Borders",
        (
            ("window_border_size", 0.0, 1.0),
            ("child_border_size", 0.0, 1.0),
            ("popup_border_size", 0.0, 1.0),
            ("frame_border_size", 0.0, 1.0),
            ("tab_border_size", 0.0, 1.0),
            ("tab_bar_border_size", 0.0, 2.0),
            ("tab_bar_overline_size", 0.0, 3.0),
            ("image_border_size", 0.0, 1.0),
            ("separator_size", 0.0, 4.0),
        ),
    ),
    (
        "Rounding",
        (
            ("window_rounding", 0.0, 12.0),
            ("child_rounding", 0.0, 12.0),
            ("frame_rounding", 0.0, 12.0),
            ("popup_rounding", 0.0, 12.0),
            ("scrollbar_rounding", 0.0, 12.0),
            ("grab_rounding", 0.0, 12.0),
            ("tab_rounding", 0.0, 12.0),
            ("image_rounding", 0.0, 12.0),
            ("selectable_rounding", 0.0, 12.0),
            ("menu_item_rounding", 0.0, 12.0),
        ),
    ),
    (
        "Tables",
        (
            ("cell_padding", 0.0, 20.0),
            ("table_angled_headers_angle", -50.0, 50.0),
            ("table_angled_headers_text_align", 0.0, 1.0),
        ),
    ),
    (
        "Widgets",
        (
            ("window_title_align", 0.0, 1.0),
            ("window_menu_button_position", 0.0, 0.0),
            ("color_button_position", 0.0, 0.0),
            ("button_text_align", 0.0, 1.0),
            ("selectable_text_align", 0.0, 1.0),
            ("separator_text_border_size", 0.0, 10.0),
            ("separator_text_align", 0.0, 1.0),
            ("separator_text_padding", 0.0, 40.0),
            ("log_slider_deadzone", 0.0, 12.0),
        ),
    ),
    (
        "Misc",
        (
            ("display_window_padding", 0.0, 30.0),
            ("display_safe_area_padding", 0.0, 30.0),
            ("docking_separator_size", 0.0, 12.0),
            ("layout_align", 0.0, 1.0),
        ),
    ),
)

RENDER_FIELDS = (
    ("anti_aliased_lines", None, None),
    ("anti_aliased_lines_use_tex", None, None),
    ("anti_aliased_fill", None, None),
    ("curve_tessellation_tol", 0.1, 10.0),
    ("circle_tessellation_max_error", 0.1, 5.0),
    ("alpha", 0.2, 1.0),
    ("disabled_alpha", 0.0, 1.0),
)

PRESETS = {
    "dark": imgui.style_colors_dark,
    "light": imgui.style_colors_light,
    "classic": imgui.style_colors_classic,
}


def style_fields() -> tuple:
    """Every writable scalar or vector field name on ``imgui.Style``.

    Examples
    --------
    >>> from imgui_debugger.style import style_fields
    >>> "frame_rounding" in style_fields()
    True
    >>> "font_scale_dpi" in style_fields()
    False
    """
    names = []
    for name, attr in vars(imgui.Style).items():
        if name.startswith("_") or name in SKIP_KEYS or not isinstance(attr, property):
            continue
        names.append(name)
    return tuple(sorted(names))


def style_to_dict(style=None) -> Dict[str, dict]:
    """Serialize a style to ``{"sizes": {...}, "colors": {name: [r,g,b,a]}}``.

    Parameters
    ----------
    style : imgui.Style | None
        The style to read; the active one when omitted.

    Examples
    --------
    >>> from imgui_bundle import imgui
    >>> from imgui_debugger.style import style_to_dict
    >>> data = style_to_dict(imgui.Style())
    >>> data["sizes"]["frame_rounding"]
    0.0
    >>> data["colors"]["Text"]
    [1.0, 1.0, 1.0, 1.0]
    """
    style = style if style is not None else imgui.get_style()
    sizes: Dict[str, object] = {}
    for name in style_fields():
        value = getattr(style, name)
        if isinstance(value, imgui.ImVec2):
            sizes[name] = [value.x, value.y]
        elif isinstance(value, (bool, int, float)):
            sizes[name] = value
    colors = {}
    for i in range(int(imgui.Col_.count)):
        c = style.color_(i)
        colors[imgui.get_style_color_name(i)] = [c.x, c.y, c.z, c.w]
    return {"sizes": sizes, "colors": colors}


def apply_style_dict(data: Dict[str, dict], style=None) -> int:
    """Write a serialized style back, returning how many fields were applied.

    Unknown keys are ignored, so a file from an older imgui still loads.

    Parameters
    ----------
    data : dict
        As produced by :func:`style_to_dict`.
    style : imgui.Style | None
        The style to write; the active one when omitted.

    Examples
    --------
    >>> from imgui_bundle import imgui
    >>> from imgui_debugger.style import apply_style_dict, style_to_dict
    >>> s = imgui.Style()
    >>> apply_style_dict({"sizes": {"frame_rounding": 6.0}}, s)
    1
    >>> s.frame_rounding
    6.0
    """
    style = style if style is not None else imgui.get_style()
    applied = 0
    names = set(style_fields())
    for name, value in (data.get("sizes") or {}).items():
        if name not in names:
            continue
        current = getattr(style, name)
        if isinstance(current, imgui.ImVec2):
            setattr(style, name, imgui.ImVec2(float(value[0]), float(value[1])))
        elif isinstance(current, bool):
            setattr(style, name, bool(value))
        elif isinstance(current, int):
            setattr(style, name, int(value))
        else:
            setattr(style, name, float(value))
        applied += 1
    by_name = {
        imgui.get_style_color_name(i): i for i in range(int(imgui.Col_.count))
    }
    for name, rgba in (data.get("colors") or {}).items():
        idx = by_name.get(name)
        if idx is None:
            continue
        style.set_color_(idx, imgui.ImVec4(*[float(v) for v in rgba]))
        applied += 1
    return applied


def default_style_path() -> Path:
    """``~/.imgui_debugger/style.json`` — where Save writes with no path given.

    Examples
    --------
    >>> from imgui_debugger.style import default_style_path
    >>> default_style_path().name
    'style.json'
    """
    return data_dir() / "style.json"


def save_style(path: Union[str, Path, None] = None, style=None) -> Path:
    """Write a style to JSON and return the path it landed at.

    Parameters
    ----------
    path : str | Path | None
        Destination; :func:`default_style_path` when omitted.
    style : imgui.Style | None
        The style to read; the active one when omitted.

    Examples
    --------
    >>> from imgui_bundle import imgui
    >>> from imgui_debugger.style import save_style
    >>> save_style("build/style.json", imgui.Style())     # doctest: +SKIP
    PosixPath('build/style.json')
    """
    dest = Path(path) if path else default_style_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(style_to_dict(style), indent=2))
    return dest


def load_style(path: Union[str, Path, None] = None, style=None) -> int:
    """Read a style from JSON and apply it, returning how many fields changed.

    Parameters
    ----------
    path : str | Path | None
        Source; :func:`default_style_path` when omitted.
    style : imgui.Style | None
        The style to write; the active one when omitted.

    Examples
    --------
    >>> from imgui_bundle import imgui
    >>> from imgui_debugger.style import load_style
    >>> load_style("build/style.json", imgui.Style())     # doctest: +SKIP
    118
    """
    src = Path(path) if path else default_style_path()
    return apply_style_dict(json.loads(src.read_text()), style)


@dataclass
class StyleEditorConfig(PanelConfig):
    """What the style editor shows and where its two buttons go.

    Parameters
    ----------
    on_save : callable | None
        ``on_save(data)`` with the serialized style; falls back to writing
        ``path`` as JSON.
    on_load : callable | None
        ``on_load()`` returning a serialized style, or None to do nothing;
        falls back to reading ``path``.
    path : str | Path | None
        File used by the fallback Save / Load.
    save_label, load_label : str
        Button text.
    show_presets : bool
        Show the dark / light / classic buttons.
    show_revert : bool
        Show a Revert button restoring the style as it was when the editor was
        constructed.
    show_sizes, show_colors, show_rendering : bool
        Which tabs to draw; a single tab is drawn without the tab bar.
    show_font_selector, show_style_selector : bool
        Draw imgui's font and built-in-style pickers above the tabs.
    store : ConfigStore | None
        Where Save, Load, the presets and the autosave go when no hook is
        given.
    autosave : bool
        With a store, write the style back a moment after it stops changing, so
        the next launch opens on it.
    autosave_delay : float
        Seconds of quiet before an autosave is written.
    show_preset_bar : bool
        Draw the named-preset row; needs a store.
    size_groups : tuple
        ``((group name, ((field, lo, hi), ...)), ...)`` driving the Sizes tab;
        :data:`SIZE_GROUPS` when None.
    extra_draw : callable | None
        ``extra_draw(editor)`` drawn under the toolbar, for your own controls.

    Every :class:`~imgui_debugger.panel.PanelConfig` field is also accepted.

    Examples
    --------
    >>> from imgui_debugger import StyleEditorConfig
    >>> cfg = StyleEditorConfig(title="Theme", save_label="Save to project")
    >>> cfg.title, cfg.save_label
    ('Theme', 'Save to project')
    """

    title: str = "Style Editor"
    window_size: Tuple[int, int] = (560, 640)
    on_save: Optional[Callable[[dict], None]] = None
    on_load: Optional[Callable[[], Optional[dict]]] = None
    path: Optional[Union[str, Path]] = None
    save_label: str = "Save"
    load_label: str = "Load"
    show_presets: bool = True
    show_revert: bool = True
    show_sizes: bool = True
    show_colors: bool = True
    show_rendering: bool = True
    show_font_selector: bool = False
    show_style_selector: bool = False
    store: Optional[ConfigStore] = None
    autosave: bool = True
    autosave_delay: float = 1.0
    show_preset_bar: bool = True
    size_groups: Optional[tuple] = None
    extra_draw: Optional[Callable[["StyleEditor"], None]] = None


class StyleEditor(Panel):
    """The imgui style editor with Save and Load wired to your own callbacks.

    Parameters
    ----------
    config : StyleEditorConfig | None
        Buttons, labels and what is shown.

    Examples
    --------
    >>> from imgui_debugger import StyleEditor, StyleEditorConfig
    >>> saved = {}
    >>> editor = StyleEditor(StyleEditorConfig(
    ...     on_save=saved.update,
    ...     on_load=lambda: saved or None,
    ... ))
    >>> editor.visible
    True
    >>> editor.save()                    # doctest: +SKIP
    >>> editor.render_window()           # doctest: +SKIP
    """

    config_class = StyleEditorConfig
    state_fields = ("show_sizes", "show_colors", "show_rendering")

    def __init__(self, config: Optional[StyleEditorConfig] = None):
        super().__init__(config or StyleEditorConfig())
        self.filter = ""
        self.status = ""
        self.preset_name = ""
        self._ref: Optional[dict] = None
        self._presets: Optional[list] = None
        self._dirty_at: Optional[float] = None

    def capture_ref(self) -> None:
        """Snapshot the current style as the one Revert goes back to.

        Called automatically on the first frame, so the reference is the style
        the host app had before the editor touched anything.

        Examples
        --------
        >>> from imgui_debugger import StyleEditor
        >>> StyleEditor().capture_ref()   # doctest: +SKIP
        """
        self._ref = style_to_dict()

    def save(self) -> None:
        """Run the Save action and put the outcome on the status line.

        Examples
        --------
        >>> from imgui_debugger import StyleEditor, StyleEditorConfig
        >>> seen = []
        >>> editor = StyleEditor(StyleEditorConfig(on_save=seen.append))
        >>> editor.save()                 # doctest: +SKIP
        """
        data = style_to_dict()
        try:
            if self.config.on_save is not None:
                self.config.on_save(data)
                self.status = "saved"
            elif self.config.store is not None:
                self.config.store.set_style(data)
                self.status = f"saved to {self.config.store.state_path}"
            else:
                self.status = f"saved to {save_style(self.config.path)}"
            self._dirty_at = None
        except Exception as exc:
            self.status = f"save failed: {exc}"

    def load(self) -> None:
        """Run the Load action and put the outcome on the status line.

        Examples
        --------
        >>> from imgui_debugger import StyleEditor, StyleEditorConfig
        >>> editor = StyleEditor(StyleEditorConfig(on_load=lambda: None))
        >>> editor.load()                 # doctest: +SKIP
        """
        try:
            if self.config.on_load is not None:
                data = self.config.on_load()
                if data is None:
                    self.status = "load cancelled"
                    return
                self.status = f"loaded {apply_style_dict(data)} fields"
            elif self.config.store is not None:
                data = self.config.store.style()
                if data is None:
                    self.status = "nothing saved yet"
                    return
                self.status = f"loaded {apply_style_dict(data)} fields"
            else:
                self.status = f"loaded {load_style(self.config.path)} fields"
            self._dirty_at = None
        except Exception as exc:
            self.status = f"load failed: {exc}"

    def revert(self) -> None:
        """Restore the style captured by :meth:`capture_ref`.

        Examples
        --------
        >>> from imgui_debugger import StyleEditor
        >>> StyleEditor().revert()        # doctest: +SKIP
        """
        if self._ref is not None:
            apply_style_dict(self._ref)
            self.status = "reverted"

    def presets(self) -> list:
        """The store's named presets, read once and cached until they change.

        Examples
        --------
        >>> from imgui_debugger import StyleEditor
        >>> StyleEditor().presets()
        []
        """
        if self._presets is None:
            store = self.config.store
            self._presets = store.presets() if store is not None else []
        return self._presets

    def refresh_presets(self) -> None:
        """Re-read the preset list from the store on the next draw.

        Examples
        --------
        >>> from imgui_debugger import StyleEditor
        >>> StyleEditor().refresh_presets()
        """
        self._presets = None

    def save_preset(self, name: str) -> None:
        """Save the current style as a named preset in the store.

        Parameters
        ----------
        name : str
            The preset name; an empty name is ignored.

        Examples
        --------
        >>> from imgui_debugger import ConfigStore, StyleEditor, StyleEditorConfig
        >>> editor = StyleEditor(StyleEditorConfig(store=ConfigStore("build/cfg")))
        >>> editor.save_preset("night")           # doctest: +SKIP
        """
        store = self.config.store
        if store is None or not name.strip():
            return
        path = store.write_preset(name, style_to_dict())
        if path is None:
            self.status = f"could not save preset {name!r}"
            return
        store.set_active_preset(name)
        self.refresh_presets()
        self.status = f"saved preset {name!r}"

    def load_preset(self, name: str) -> None:
        """Apply a named preset from the store and make it the active one.

        Parameters
        ----------
        name : str
            The preset name.

        Examples
        --------
        >>> from imgui_debugger import ConfigStore, StyleEditor, StyleEditorConfig
        >>> editor = StyleEditor(StyleEditorConfig(store=ConfigStore("build/cfg")))
        >>> editor.load_preset("night")           # doctest: +SKIP
        """
        store = self.config.store
        if store is None:
            return
        data = store.read_preset(name)
        if data is None:
            self.status = f"no preset {name!r}"
            return
        store.set_active_preset(name)
        self.status = f"loaded preset {name!r} ({apply_style_dict(data)} fields)"
        self.mark_dirty()

    def delete_preset(self, name: str) -> None:
        """Remove a named preset from the store.

        Parameters
        ----------
        name : str
            The preset name.

        Examples
        --------
        >>> from imgui_debugger import ConfigStore, StyleEditor, StyleEditorConfig
        >>> editor = StyleEditor(StyleEditorConfig(store=ConfigStore("build/cfg")))
        >>> editor.delete_preset("night")         # doctest: +SKIP
        """
        store = self.config.store
        if store is None:
            return
        self.status = f"deleted {name!r}" if store.delete_preset(name) else f"no preset {name!r}"
        if store.active_preset() == name:
            store.set_active_preset(None)
        self.refresh_presets()

    def mark_dirty(self) -> None:
        """Note that the style changed, starting the autosave countdown.

        Examples
        --------
        >>> from imgui_debugger import StyleEditor
        >>> editor = StyleEditor()
        >>> editor.mark_dirty()
        >>> editor.dirty
        True
        """
        self._dirty_at = time.monotonic()

    @property
    def dirty(self) -> bool:
        """Whether the style changed since the last save.

        Examples
        --------
        >>> from imgui_debugger import StyleEditor
        >>> StyleEditor().dirty
        False
        """
        return self._dirty_at is not None

    def flush_autosave(self, force: bool = False) -> bool:
        """Write the style to the store once it has been quiet long enough.

        Parameters
        ----------
        force : bool
            Write now, whatever the countdown says.

        Returns
        -------
        bool
            True when something was written.

        Examples
        --------
        >>> from imgui_debugger import StyleEditor
        >>> StyleEditor().flush_autosave()
        False
        """
        cfg = self.config
        if cfg.store is None or not cfg.autosave or self._dirty_at is None:
            return False
        if not force and time.monotonic() - self._dirty_at < cfg.autosave_delay:
            return False
        self._dirty_at = None
        return cfg.store.set_style(style_to_dict())

    def render(self) -> None:
        """Draw the toolbar and the Sizes / Colors / Rendering tabs inline.

        Examples
        --------
        >>> from imgui_debugger import StyleEditor
        >>> StyleEditor().render()            # doctest: +SKIP
        """
        cfg = self.config
        if self._ref is None:
            self.capture_ref()
        self.draw_toolbar()
        if cfg.show_font_selector:
            imgui.show_font_selector("Font")
        if cfg.show_style_selector and imgui.show_style_selector("Built-in style"):
            self.status = "applied a built-in style"
        if cfg.extra_draw is not None:
            cfg.extra_draw(self)
        tabs = [
            ("Sizes", cfg.show_sizes, self.draw_sizes),
            ("Colors", cfg.show_colors, self.draw_colors),
            ("Rendering", cfg.show_rendering, self.draw_rendering),
        ]
        shown = [(name, draw) for name, on, draw in tabs if on]
        changed = False
        if len(shown) == 1:
            changed = shown[0][1]()
        elif shown and imgui.begin_tab_bar("##style_tabs"):
            for name, draw in shown:
                if imgui.begin_tab_item(name)[0]:
                    changed = draw() or changed
                    imgui.end_tab_item()
            imgui.end_tab_bar()
        if changed:
            self.mark_dirty()
        self.flush_autosave()

    def draw_toolbar(self) -> None:
        """Draw Save, Load, optional Revert, the presets and the status line.

        Examples
        --------
        >>> from imgui_debugger import StyleEditor
        >>> StyleEditor().draw_toolbar()      # doctest: +SKIP
        """
        cfg = self.config
        if imgui.button(cfg.save_label):
            self.save()
        imgui.same_line()
        if imgui.button(cfg.load_label):
            self.load()
        if cfg.show_revert:
            imgui.same_line()
            if imgui.button("Revert"):
                self.revert()
        if cfg.show_presets:
            imgui.same_line()
            imgui.text_disabled("|")
            for name, apply in PRESETS.items():
                imgui.same_line()
                if imgui.small_button(name):
                    apply(imgui.get_style())
                    self.status = f"applied {name} preset"
                    self.mark_dirty()
        if cfg.store is not None and cfg.show_preset_bar:
            self.draw_preset_bar()
        if self.status:
            imgui.text_colored(to_vec4(cfg.theme.text_dim), self.status)
        imgui.separator()

    def draw_preset_bar(self) -> None:
        """Draw the named-preset row: pick one, save the current style, delete.

        Examples
        --------
        >>> from imgui_debugger import StyleEditor
        >>> StyleEditor().draw_preset_bar()   # doctest: +SKIP
        """
        names = self.presets()
        width = imgui.get_content_region_avail().x
        items = ["(none)"] + names
        active = self.config.store.active_preset()
        current = items.index(active) if active in items else 0
        imgui.set_next_item_width(width * 0.4)
        changed, picked = imgui.combo("##preset", current, items)
        if changed and picked > 0:
            self.load_preset(items[picked])
        imgui.same_line()
        imgui.set_next_item_width(width * 0.25)
        _, self.preset_name = imgui.input_text_with_hint(
            "##preset_name", "preset name...", self.preset_name
        )
        imgui.same_line()
        if imgui.button("Save as") and self.preset_name.strip():
            self.save_preset(self.preset_name.strip())
        imgui.same_line()
        if imgui.button("Delete") and active:
            self.delete_preset(active)

    def draw_sizes(self) -> bool:
        """Draw the grouped size sliders, returning whether one moved.

        Examples
        --------
        >>> from imgui_debugger import StyleEditor
        >>> StyleEditor().draw_sizes()        # doctest: +SKIP
        False
        """
        style = imgui.get_style()
        changed = False
        for group, fields in self.config.size_groups or SIZE_GROUPS:
            imgui.text_colored(to_vec4(self.theme.node), group)
            imgui.separator()
            for name, lo, hi in fields:
                changed = _draw_size_field(style, name, lo, hi) or changed
            imgui.spacing()
        return changed

    def draw_colors(self) -> bool:
        """Draw every style color with a filter box; True when one changed.

        Examples
        --------
        >>> from imgui_debugger import StyleEditor
        >>> StyleEditor().draw_colors()       # doctest: +SKIP
        False
        """
        style = imgui.get_style()
        imgui.set_next_item_width(-1)
        _, self.filter = imgui.input_text_with_hint(
            "##color_filter", "filter colors...", self.filter
        )
        low = self.filter.lower()
        flags = imgui.ColorEditFlags_.alpha_bar | imgui.ColorEditFlags_.alpha_preview_half
        any_changed = False
        for i in range(int(imgui.Col_.count)):
            name = imgui.get_style_color_name(i)
            if low and low not in name.lower():
                continue
            c = style.color_(i)
            changed, rgba = imgui.color_edit4(f"{name}##col{i}", [c.x, c.y, c.z, c.w], flags)
            if changed:
                style.set_color_(i, imgui.ImVec4(*rgba))
                any_changed = True
        return any_changed

    def draw_rendering(self) -> bool:
        """Draw the anti-aliasing, tessellation and alpha controls.

        Examples
        --------
        >>> from imgui_debugger import StyleEditor
        >>> StyleEditor().draw_rendering()    # doctest: +SKIP
        False
        """
        style = imgui.get_style()
        changed = False
        for name, lo, hi in RENDER_FIELDS:
            changed = _draw_size_field(style, name, lo, hi) or changed
        return changed


def _draw_size_field(style, name: str, lo, hi) -> bool:
    """Draw one style field with the widget its type calls for; True when it moved.

    Examples
    --------
    >>> from imgui_bundle import imgui
    >>> from imgui_debugger.style import _draw_size_field
    >>> _draw_size_field(imgui.get_style(), "frame_rounding", 0.0, 12.0)  # doctest: +SKIP
    False
    """
    # the field lists target the newest imgui; an older one lacks some
    if not hasattr(style, name):
        return False
    value = getattr(style, name)
    if name in ("window_menu_button_position", "color_button_position"):
        current = int(value) + 1 if int(value) >= 0 else 0
        changed, picked = imgui.combo(name, current, list(DIR_ITEMS))
        if changed:
            setattr(style, name, picked - 1)
        return changed
    if name == "table_angled_headers_angle":
        changed, out = imgui.slider_angle(name, float(value), lo, hi)
        if changed:
            setattr(style, name, out)
        return changed
    if isinstance(value, imgui.ImVec2):
        fmt = "%.0f" if hi > 2.0 else "%.2f"
        changed, out = imgui.slider_float2(name, [value.x, value.y], lo, hi, fmt)
        if changed:
            setattr(style, name, imgui.ImVec2(*out))
        return changed
    if isinstance(value, bool):
        changed, out = imgui.checkbox(name, value)
        if changed:
            setattr(style, name, out)
        return changed
    changed, out = imgui.slider_float(name, float(value), lo, hi, "%.2f")
    if changed:
        setattr(style, name, out)
    return changed
