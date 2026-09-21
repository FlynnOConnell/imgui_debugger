"""Attach to a fastplotlib EdgeWindow, the widget shape pml_utilities and
masknmf-toolbox both use.

Their widgets draw from ``update()``, so the debugger goes there: one
``render_window()`` call and the whole widget is inspectable, plus any extra
scope you promote with ``watch``. Run it with
``python examples/debug_edge_window.py`` (needs fastplotlib).
"""

import numpy as np
from imgui_bundle import imgui

import fastplotlib as fpl
from fastplotlib.ui import EdgeWindow

from imgui_debugger import attach


class PreviewWidget(EdgeWindow):
    """A minimal EdgeWindow with the state a real preview widget carries."""

    def __init__(self, figure, size=250, location="right", title="Preview"):
        super().__init__(figure=figure, size=size, location=location, title=title)
        self.indices = {"t": 0, "z": 0, "c": 0}
        self.vmin, self.vmax = 0.0, 1.0
        self.metadata = {"fs": 9.6, "dz": 5.0, "planes": [1, 2, 3]}
        self.debugger = attach(self, title="Preview widget", value_col=190.0)
        # promote one attribute to its own top-level scope
        self.debugger.watch("metadata", lambda: self.metadata, role="prop")

    def update(self):
        """Draw the widget's own controls, then the debugger window."""
        _, self.indices["t"] = imgui.slider_int("t", self.indices["t"], 0, 99)
        _, self.vmax = imgui.slider_float("vmax", self.vmax, 0.0, 1.0)
        if imgui.button("debug"):
            self.debugger.toggle()
        self.debugger.capture()
        self.debugger.render_window()


if __name__ == "__main__":
    figure = fpl.Figure(size=(900, 600))
    figure[0, 0].add_image(np.random.rand(128, 128).astype(np.float32))
    figure.add_gui(PreviewWidget(figure))
    figure.show()
    fpl.loop.run()
