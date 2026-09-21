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
from .tree import TreeStyle, draw_child, draw_children, draw_scope

__version__ = "0.1.0"

__all__ = [
    # panels
    "Panel",
    "PanelConfig",
    "Hotkey",
    "DebugTools",
    # widget + harness
    "Debugger",
    "DebuggerConfig",
    "attach",
    "watch_all",
    "run_debugger",
    "run_panel",
    "ensure_assets",
    "data_dir",
    "default_ini_path",
    # scopes
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
    # rendering
    "TreeStyle",
    "draw_scope",
    "draw_child",
    "draw_children",
    "can_edit",
    "edit_value",
    "fmt_value",
    "type_label",
    # search
    "matches",
    "clear_cache",
    # style editor
    "StyleEditor",
    "StyleEditorConfig",
    "style_to_dict",
    "apply_style_dict",
    "save_style",
    "load_style",
    "default_style_path",
    # imgui's own debug windows
    "MetricsPanel",
    "DebugLogPanel",
    "IdStackPanel",
    "AboutPanel",
    "DemoPanel",
    "UserGuidePanel",
    "NativeWindowPanel",
    "NativePanelConfig",
    # theme
    "Theme",
    "to_vec4",
    # meta
    "__version__",
]
