"""One-shot harness: open the debugger in its own window and block until closed.

Examples
--------
>>> from imgui_debugger import run_debugger
>>> run_debugger({"fs": 9.6, "dz": 5.0})        # doctest: +SKIP
"""

from __future__ import annotations

import os
from typing import Optional

from ._assets import default_ini_path, ensure_assets
from .debugger import Debugger, DebuggerConfig
from .theme import to_vec4


def run_debugger(
    target=None,
    config: Optional[DebuggerConfig] = None,
    runner_params=None,
    **kwargs,
) -> Debugger:
    """Show the debugger in its own OS window, blocking until it is closed.

    Parameters
    ----------
    target : object | None
        The object to inspect.
    config : DebuggerConfig | None
        A prebuilt config; ``target`` and ``kwargs`` override its fields.
    runner_params : hello_imgui.RunnerParams | None
        Supply your own params, e.g. a null backend for headless tests. Window
        title, size and ``.ini`` are filled in from the config only when unset.
    **kwargs
        Any :class:`~imgui_debugger.DebuggerConfig` field.

    Returns
    -------
    Debugger
        The widget that was rendered, so its final state can be read back.

    Examples
    --------
    >>> from imgui_debugger import run_debugger
    >>> class Settings:
    ...     def __init__(self):
    ...         self.threshold = 0.4
    >>> run_debugger(Settings(), title="Settings")          # doctest: +SKIP
    >>> run_debugger({"a": 1}, private=True, editable=False)  # doctest: +SKIP
    """
    from imgui_bundle import hello_imgui, immapp

    cfg = config or DebuggerConfig()
    if target is not None:
        cfg.target = target
    for key, value in kwargs.items():
        if not hasattr(cfg, key):
            raise TypeError(f"DebuggerConfig has no field {key!r}")
        setattr(cfg, key, value)

    ensure_assets(cfg.assets_folder)
    dbg = Debugger(cfg, frame_depth=2)

    params = runner_params if runner_params is not None else hello_imgui.RunnerParams()
    params.app_window_params.window_title = cfg.window_title or cfg.title or "Debugger"
    if cfg.window_size:
        params.app_window_params.window_geometry.size = tuple(cfg.window_size)
        params.app_window_params.window_geometry.size_auto = False
    params.app_window_params.resizable = cfg.resizable
    # hello_imgui resolves ini_filename against the cwd by default, which drops
    # a layout file wherever the app was launched; pin it to an absolute path.
    if not params.ini_filename:
        ini = cfg.ini_path or default_ini_path()
        params.ini_filename = ini
        if os.path.isabs(ini):
            params.ini_folder_type = hello_imgui.IniFolderType.absolute_path
            parent = os.path.dirname(ini)
            if parent:
                os.makedirs(parent, exist_ok=True)
    bg = to_vec4(cfg.theme.bg)
    params.imgui_window_params.background_color = bg
    params.callbacks.show_gui = dbg.render

    addons = immapp.AddOnsParams()
    addons.with_markdown = False
    addons.with_implot = False
    addons.with_implot3d = False
    immapp.run(runner_params=params, add_ons_params=addons)
    return dbg
