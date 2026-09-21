"""Per-user paths and icon-font resolution for the debugger.

Examples
--------
>>> from imgui_debugger._assets import data_dir, default_ini_path
>>> str(data_dir()).endswith(".imgui_debugger")
True
>>> default_ini_path().endswith("debugger.ini")
True
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

_ICON_FONT = "fonts/Font_Awesome_6_Free-Solid-900.otf"


def imgui_bundle_assets_dir() -> Optional[str]:
    """Path to imgui-bundle's bundled ``assets`` folder, or None.

    Examples
    --------
    >>> from imgui_debugger._assets import imgui_bundle_assets_dir
    >>> folder = imgui_bundle_assets_dir()
    >>> folder is None or folder.endswith("assets")
    True
    """
    try:
        import imgui_bundle

        p = Path(imgui_bundle.__file__).parent / "assets"
        return str(p) if p.is_dir() else None
    except Exception:
        return None


def data_dir() -> Path:
    """The per-user dir for everything this library writes, created on first use.

    Defaults to ``~/.imgui_debugger``; override with ``IMGUI_DEBUGGER_HOME``.

    Examples
    --------
    >>> import os
    >>> os.environ["IMGUI_DEBUGGER_HOME"] = os.path.join(os.getcwd(), "dbg")
    >>> from imgui_debugger._assets import data_dir
    >>> data_dir().is_dir()
    True
    """
    base = os.environ.get("IMGUI_DEBUGGER_HOME")
    d = Path(base) if base else (Path.home() / ".imgui_debugger")
    d.mkdir(parents=True, exist_ok=True)
    return d


def user_assets_dir() -> Path:
    """``<data dir>/assets`` — an optional user assets folder, never created here.

    Examples
    --------
    >>> from imgui_debugger._assets import user_assets_dir
    >>> user_assets_dir().name
    'assets'
    """
    return data_dir() / "assets"


def default_ini_path(name: str = "debugger") -> str:
    """Absolute path for hello_imgui's window-layout ``.ini``.

    Parameters
    ----------
    name : str
        File stem, so several debugger windows can keep separate layouts.

    Examples
    --------
    >>> from imgui_debugger._assets import default_ini_path
    >>> default_ini_path("panel").endswith("panel.ini")
    True
    """
    return str(data_dir() / f"{name}.ini")


def ensure_assets(assets_folder: Optional[str] = None) -> None:
    """Make sure hello_imgui can resolve the FontAwesome icon font.

    Passing ``assets_folder`` sets it as *the* assets folder; with no argument a
    host app's already-working configuration is left untouched.

    Parameters
    ----------
    assets_folder : str | None
        Folder containing ``fonts/Font_Awesome_6_Free-Solid-900.otf``.

    Examples
    --------
    >>> from imgui_debugger import ensure_assets
    >>> ensure_assets()                      # doctest: +SKIP
    >>> ensure_assets("/opt/myapp/assets")   # doctest: +SKIP
    """
    from imgui_bundle import hello_imgui

    if assets_folder:
        hello_imgui.set_assets_folder(str(assets_folder))
        return
    try:
        if hello_imgui.asset_exists(_ICON_FONT):
            return
    except Exception:
        pass
    user = user_assets_dir()
    if user.is_dir():
        hello_imgui.add_assets_search_path(str(user))
        try:
            if hello_imgui.asset_exists(_ICON_FONT):
                return
        except Exception:
            pass
    folder = imgui_bundle_assets_dir()
    if folder:
        hello_imgui.add_assets_search_path(folder)
