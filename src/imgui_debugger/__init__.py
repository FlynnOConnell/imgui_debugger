"""imgui_debugger — a live variable inspector for any imgui-bundle widget.

Examples
--------
Drop a debug window into an app you already have:

>>> from imgui_debugger import attach
>>> dbg = attach(my_widget, title="ROI tab")          # doctest: +SKIP
>>> # each frame, inside your show_gui:
>>> dbg.render_window()                                # doctest: +SKIP

Inspect an object with no host app at all:

>>> from imgui_debugger import run_debugger
>>> run_debugger({"fs": 9.6, "dz": 5.0})               # doctest: +SKIP

Follow a function's own locals while it draws:

>>> def draw(self):                                    # doctest: +SKIP
...     rows = self.build_rows()
...     self.dbg.capture()
...     self.dbg.render_window()
"""

from __future__ import annotations

from ._assets import data_dir, default_ini_path, ensure_assets
from .debugger import Debugger, DebuggerConfig, attach, watch_all
from .edit import can_edit, edit_value
from .format import fmt_value, type_label
from .native import (
    AboutPanel,
    DebugLogPanel,
    DemoPanel,
    IdStackPanel,
    MetricsPanel,
    NativePanelConfig,
    NativeWindowPanel,
    UserGuidePanel,
)
from .panel import Hotkey, Panel, PanelConfig
from .player import MoviePlayer, crop_slices
from .popups import (
    KeybindsConfig,
    KeybindsPanel,
    draw_keybinds_popup,
    draw_path_popup,
)
from .runner import run_debugger, run_panel
from .scopes import (
    Child,
    Scope,
    Watch,
    children_of,
    class_children,
    frame_scopes,
    instance_children,
    object_scopes,
    property_children,
    runtime_scope,
)
from .search import clear_cache, matches
from .store import ConfigStore
from .table import (
    FILTER_ALL,
    UNLABELED,
    RoiOrder,
    RowAction,
    draw_filter_row,
    draw_label_filter,
    draw_range_filter,
    draw_table,
)
from .style import (
    StyleEditor,
    StyleEditorConfig,
    apply_style_dict,
    default_style_path,
    load_style,
    save_style,
    style_to_dict,
)
from .theme import Theme, to_vec4
from .tools import DebugTools
from .trace_plot import TracePlot
from .tree import TreeStyle, draw_child, draw_children, draw_scope
from .widgets import (
    Grid,
    button_colors,
    card,
    close_button,
    em,
    grid,
    help_mark,
    popup,
    right_aligned_text,
    section,
)

__version__ = "0.2.0"

__all__ = [
    "Panel",
    "PanelConfig",
    "Hotkey",
    "DebugTools",
    "ConfigStore",
    "Debugger",
    "DebuggerConfig",
    "attach",
    "watch_all",
    "run_debugger",
    "run_panel",
    "ensure_assets",
    "data_dir",
    "default_ini_path",
    "Scope",
    "Child",
    "Watch",
    "children_of",
    "instance_children",
    "property_children",
    "class_children",
    "object_scopes",
    "frame_scopes",
    "runtime_scope",
    "TreeStyle",
    "draw_scope",
    "draw_child",
    "draw_children",
    "can_edit",
    "edit_value",
    "fmt_value",
    "type_label",
    "matches",
    "clear_cache",
    "StyleEditor",
    "StyleEditorConfig",
    "style_to_dict",
    "apply_style_dict",
    "save_style",
    "load_style",
    "default_style_path",
    "MetricsPanel",
    "DebugLogPanel",
    "IdStackPanel",
    "AboutPanel",
    "DemoPanel",
    "UserGuidePanel",
    "NativeWindowPanel",
    "NativePanelConfig",
    "RoiOrder",
    "RowAction",
    "draw_table",
    "draw_range_filter",
    "draw_label_filter",
    "draw_filter_row",
    "FILTER_ALL",
    "UNLABELED",
    "TracePlot",
    "MoviePlayer",
    "crop_slices",
    "KeybindsPanel",
    "KeybindsConfig",
    "draw_keybinds_popup",
    "draw_path_popup",
    "em",
    "card",
    "section",
    "popup",
    "close_button",
    "help_mark",
    "right_aligned_text",
    "button_colors",
    "Grid",
    "grid",
    "Theme",
    "to_vec4",
    "__version__",
]
