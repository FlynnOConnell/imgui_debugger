"""Inspect one object in its own window, with no host app.

Run it with ``python examples/debug_minimal.py``.
"""

from dataclasses import dataclass, field

from imgui_debugger import run_debugger


@dataclass
class Settings:
    """A settings object of the shape a pipeline usually carries."""

    name: str = "voltage"
    threshold: float = 0.4
    planes: list = field(default_factory=lambda: [1, 2, 3])
    accent: tuple = (0.2, 0.5, 0.85, 1.0)
    metadata: dict = field(
        default_factory=lambda: {"fs": 9.6, "dz": 5.0, "si": {"version": 2023}}
    )


CONFIG = dict(title="Settings", value_col=220.0)

if __name__ == "__main__":
    run_debugger(Settings(), **CONFIG)
