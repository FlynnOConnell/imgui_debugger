"""Attach to a fastplotlib EdgeWindow, the widget shape pml_utilities and
masknmf-toolbox both use.

Their widgets draw from ``update()``, so everything goes there: the ported ROI
table and trace plot for the body, one ``render_window()`` for the debugger.
Run it with ``python examples/debug_edge_window.py`` (needs fastplotlib).
"""

import numpy as np
from imgui_bundle import imgui

import fastplotlib as fpl
from fastplotlib.ui import EdgeWindow

from imgui_debugger import (
    Hotkey,
    RoiOrder,
    TracePlot,
    attach,
    draw_filter_row,
    draw_table,
    section,
)

N_ROIS, N_FRAMES = 25, 1000


class RoiEdgeWindow(EdgeWindow):
    """An EdgeWindow whose body is the ported table and trace plot."""

    def __init__(self, figure, size=380, location="right", title="ROIs"):
        super().__init__(figure=figure, size=size, location=location, title=title)
        rng = np.random.default_rng(0)
        self.area = rng.integers(30, 400, N_ROIS).astype(float)
        self.traces = rng.normal(size=(N_ROIS, N_FRAMES)).cumsum(axis=1).astype(np.float32)
        self.scroll_to_current = True

        self.order = RoiOrder({"area": self.area}, N_ROIS)
        self.order.set_range_column("area")
        self.plot = TracePlot(["raw"], N_FRAMES)
        self.debugger = attach(self, title="ROIs widget", hotkey=Hotkey(imgui.Key.f12))
        self.select(0)

    def select(self, roi: int) -> None:
        """Put one ROI's trace in the plot."""
        self.plot.set("raw", [(f"roi {roi}", self.traces[roi], None)])

    def update(self):
        """The widget body, then the debugger window over the same frame."""
        section("ROIs")
        draw_filter_row(self.order)
        imgui.begin_child("table", imgui.ImVec2(0, imgui.get_font_size() * 10))
        self.scroll_to_current = draw_table(
            self.order,
            ["id", "area"],
            {"area": lambda i: f"{self.area[i]:.0f}"},
            self.scroll_to_current,
            on_select=self.select,
        )
        imgui.end_child()
        section("Trace")
        self.plot.draw()
        # capture here so the locals scope follows this method
        self.debugger.capture()
        self.debugger.render_window()


if __name__ == "__main__":
    figure = fpl.Figure(size=(1200, 700))
    figure[0, 0].add_image(np.random.rand(128, 128).astype(np.float32))
    figure.add_gui(RoiEdgeWindow(figure))
    figure.show()
    fpl.loop.run()
