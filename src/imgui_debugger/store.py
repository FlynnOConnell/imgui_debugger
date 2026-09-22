"""Where a host app keeps this package's state on disk.

One directory holds everything: the style as it was left, named presets, each
panel's state, and hello_imgui's layout ``.ini``. A host app points the store at
its own settings directory, the way ``mbo_utilities`` keeps everything under
``~/.mbo``.

Examples
--------
>>> from imgui_debugger import ConfigStore
>>> store = ConfigStore("build/cfg")
>>> store.write_preset("night", {"sizes": {"frame_rounding": 8.0}})   # doctest: +SKIP
>>> store.presets()                                                   # doctest: +SKIP
['night']
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Union

from ._assets import data_dir

STATE_FILE = "state.json"
STYLES_DIR = "styles"
LAYOUT_INI = "layout.ini"


def _slug(name: str) -> str:
    """Turn a preset name into a safe file stem.

    Parameters
    ----------
    name : str
        The name as typed.

    Examples
    --------
    >>> from imgui_debugger.store import _slug
    >>> _slug("Night / High contrast")
    'Night _ High contrast'
    """
    bad = '<>:"/\\|?*'
    return "".join("_" if c in bad else c for c in name).strip() or "unnamed"


class ConfigStore:
    """A directory holding the style, named presets, panel state and layout.

    Parameters
    ----------
    root : str | Path | None
        The directory to use; ``~/.imgui_debugger`` when omitted. Created on
        first write, never on construction.

    Examples
    --------
    >>> from imgui_debugger import ConfigStore
    >>> store = ConfigStore("build/cfg")
    >>> store.state_path.name
    'state.json'
    >>> store.styles_dir.name
    'styles'
    """

    def __init__(self, root: Optional[Union[str, Path]] = None):
        self.root = Path(root) if root is not None else data_dir()

    @property
    def state_path(self) -> Path:
        """The JSON file holding the last style, panel state and active preset.

        Examples
        --------
        >>> from imgui_debugger import ConfigStore
        >>> ConfigStore("build/cfg").state_path.name
        'state.json'
        """
        return self.root / STATE_FILE

    @property
    def styles_dir(self) -> Path:
        """The directory holding one JSON file per named preset.

        Examples
        --------
        >>> from imgui_debugger import ConfigStore
        >>> ConfigStore("build/cfg").styles_dir.name
        'styles'
        """
        return self.root / STYLES_DIR

    @property
    def layout_ini(self) -> str:
        """Absolute path for hello_imgui's ``.ini``, which holds window geometry.

        Window size and position are imgui's own to persist; point
        ``RunnerParams.ini_filename`` here and every panel reopens where it was.

        Examples
        --------
        >>> from imgui_debugger import ConfigStore
        >>> ConfigStore("build/cfg").layout_ini.endswith("layout.ini")
        True
        """
        return str(self.root / LAYOUT_INI)

    def read_state(self) -> Dict:
        """The whole state file, or an empty dict when there is none or it is bad.

        Examples
        --------
        >>> from imgui_debugger import ConfigStore
        >>> ConfigStore("build/does-not-exist").read_state()
        {}
        """
        try:
            return json.loads(self.state_path.read_text())
        except Exception:
            return {}

    def write_state(self, state: Dict) -> bool:
        """Write the whole state file, returning whether it landed.

        Parameters
        ----------
        state : dict
            The state to write.

        Examples
        --------
        >>> from imgui_debugger import ConfigStore
        >>> ConfigStore("build/cfg").write_state({"panels": {}})   # doctest: +SKIP
        True
        """
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            self.state_path.write_text(json.dumps(state, indent=2))
            return True
        except Exception:
            return False

    def update_state(self, **changes) -> bool:
        """Merge top-level keys into the state file.

        Examples
        --------
        >>> from imgui_debugger import ConfigStore
        >>> ConfigStore("build/cfg").update_state(active_preset="night")  # doctest: +SKIP
        True
        """
        state = self.read_state()
        state.update(changes)
        return self.write_state(state)

    def style(self) -> Optional[Dict]:
        """The style as it was last left, or None when nothing was saved.

        Examples
        --------
        >>> from imgui_debugger import ConfigStore
        >>> ConfigStore("build/does-not-exist").style() is None
        True
        """
        return self.read_state().get("style")

    def set_style(self, data: Dict) -> bool:
        """Record the style as it is now, for the next launch to pick up.

        Parameters
        ----------
        data : dict
            As produced by :func:`~imgui_debugger.style_to_dict`.

        Examples
        --------
        >>> from imgui_debugger import ConfigStore
        >>> ConfigStore("build/cfg").set_style({"sizes": {}})   # doctest: +SKIP
        True
        """
        return self.update_state(style=data)

    def presets(self) -> List[str]:
        """Every named preset in the store, sorted.

        Examples
        --------
        >>> from imgui_debugger import ConfigStore
        >>> ConfigStore("build/does-not-exist").presets()
        []
        """
        try:
            return sorted(p.stem for p in self.styles_dir.glob("*.json"))
        except Exception:
            return []

    def preset_path(self, name: str) -> Path:
        """Where a named preset lives.

        Parameters
        ----------
        name : str
            The preset name as typed.

        Examples
        --------
        >>> from imgui_debugger import ConfigStore
        >>> ConfigStore("build/cfg").preset_path("night").name
        'night.json'
        """
        return self.styles_dir / f"{_slug(name)}.json"

    def read_preset(self, name: str) -> Optional[Dict]:
        """A named preset, or None when it is missing or unreadable.

        Examples
        --------
        >>> from imgui_debugger import ConfigStore
        >>> ConfigStore("build/cfg").read_preset("nope") is None
        True
        """
        try:
            return json.loads(self.preset_path(name).read_text())
        except Exception:
            return None

    def write_preset(self, name: str, data: Dict) -> Optional[Path]:
        """Save a named preset, returning its path or None when it failed.

        Parameters
        ----------
        name : str
            The preset name as typed.
        data : dict
            As produced by :func:`~imgui_debugger.style_to_dict`.

        Examples
        --------
        >>> from imgui_debugger import ConfigStore
        >>> ConfigStore("build/cfg").write_preset("night", {"sizes": {}})  # doctest: +SKIP
        PosixPath('build/cfg/styles/night.json')
        """
        try:
            self.styles_dir.mkdir(parents=True, exist_ok=True)
            path = self.preset_path(name)
            path.write_text(json.dumps(data, indent=2))
            return path
        except Exception:
            return None

    def delete_preset(self, name: str) -> bool:
        """Remove a named preset, returning whether it was there.

        Examples
        --------
        >>> from imgui_debugger import ConfigStore
        >>> ConfigStore("build/cfg").delete_preset("nope")
        False
        """
        try:
            self.preset_path(name).unlink()
            return True
        except Exception:
            return False

    def active_preset(self) -> Optional[str]:
        """The preset name last loaded, or None.

        Examples
        --------
        >>> from imgui_debugger import ConfigStore
        >>> ConfigStore("build/does-not-exist").active_preset() is None
        True
        """
        return self.read_state().get("active_preset")

    def set_active_preset(self, name: Optional[str]) -> bool:
        """Record which preset is the current one.

        Examples
        --------
        >>> from imgui_debugger import ConfigStore
        >>> ConfigStore("build/cfg").set_active_preset(None)    # doctest: +SKIP
        True
        """
        return self.update_state(active_preset=name)

    def panel_state(self, key: str) -> Dict:
        """One panel's saved state, or an empty dict.

        Parameters
        ----------
        key : str
            The panel's ``window_id``.

        Examples
        --------
        >>> from imgui_debugger import ConfigStore
        >>> ConfigStore("build/does-not-exist").panel_state("StyleEditor")
        {}
        """
        return self.read_state().get("panels", {}).get(key, {})

    def set_panel_state(self, key: str, data: Dict) -> bool:
        """Record one panel's state.

        Examples
        --------
        >>> from imgui_debugger import ConfigStore
        >>> ConfigStore("build/cfg").set_panel_state("StyleEditor", {})  # doctest: +SKIP
        True
        """
        state = self.read_state()
        panels = state.setdefault("panels", {})
        panels[key] = data
        return self.write_state(state)

    def apply_style(self, style=None) -> int:
        """Apply the saved style to the live imgui style, at startup.

        Call it once after the imgui context exists and before the first frame
        is drawn.

        Parameters
        ----------
        style : imgui.Style | None
            The style to write; the active one when omitted.

        Returns
        -------
        int
            How many fields were applied; ``0`` when nothing was saved.

        Examples
        --------
        >>> from imgui_debugger import ConfigStore
        >>> ConfigStore("build/does-not-exist").apply_style()
        0
        """
        from .style import apply_style_dict

        data = self.style()
        if not data:
            return 0
        return apply_style_dict(data, style)
