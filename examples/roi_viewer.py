"""A small ROI viewer built only from the ported widgets, with the debugger on it.

This is the shape the real viewers in mbo_utilities and masknmf-toolbox have: a
filterable ROI table driving a trace plot and a movie transport, laid out with
the card / section / grid helpers. Run it with
``python examples/roi_viewer.py``.
"""

import numpy as np
from imgui_bundle import hello_imgui, imgui, immapp

from imgui_debugger import (
    Hotkey,
    KeybindsPanel,
    MoviePlayer,
    RoiOrder,
    RowAction,
    attach,
    card,
    draw_filter_row,
    draw_table,
    grid,
    help_mark,
    right_aligned_text,
    section,
    TracePlot,
)

N_ROIS, N_FRAMES = 40, 2000
KEYBINDS = [
    ("up / down", "move the ROI cursor"),
    ("space", "play or pause the movie"),
    ("d", "delete the ROI under the cursor"),
    ("F12", "open the variable inspector"),
]


def synthetic_rois(rng):
    """Per-ROI columns and traces standing in for a real detection's output."""
    area = rng.integers(30, 400, N_ROIS).astype(float)
    snr = rng.gamma(2.0, 2.0, N_ROIS)
    traces = rng.normal(size=(N_ROIS, N_FRAMES)).cumsum(axis=1).astype(np.float32)
    return area, snr, traces


class RoiViewer:
    """The viewer: an ROI table, its trace, and the movie it was read from."""

    def __init__(self):
        rng = np.random.default_rng(0)
        self.area, self.snr, self.traces = synthetic_rois(rng)
        self.labels = np.full(N_ROIS, -1)
        self.deleted = set()
        self.scroll_to_current = True
        self.threshold = 0.4

        self.order = RoiOrder(
            {"area": self.area, "snr": self.snr},
            N_ROIS,
            labels=self.labels,
        )
        self.order.set_range_column("snr")

        self.plot = TracePlot(["raw", "dff"], N_FRAMES)
        self.player = MoviePlayer(rng.normal(size=(200, 64, 64)).astype(np.float32))
        self.keybinds = KeybindsPanel(bindings=KEYBINDS)
        self.debugger = attach(self, title="ROI viewer", hotkey=Hotkey(imgui.Key.f12))
        self.actions = (RowAction("x", "delete this ROI", self.delete, self.why_not),)
        self.select(0)

    def why_not(self, roi: int):
        """Why an ROI cannot be deleted, or None when it can."""
        return "already deleted" if roi in self.deleted else None

    def delete(self, roi: int) -> None:
        """Mark an ROI deleted; the row stays, greyed, like a real curation pass."""
        self.deleted.add(roi)

    def select(self, roi: int) -> None:
        """Show an ROI's traces and seek the movie to its peak."""
        trace = self.traces[roi]
        self.plot.set("raw", [(f"roi {roi}", trace, None)])
        self.plot.set("dff", [(f"roi {roi}", np.gradient(trace), (1.0, 0.45, 0.2))])
        self.player.jump_to(int(np.argmax(trace)) % self.player.n_frames)

    def draw_controls(self) -> None:
        """The card of run settings, laid out on the shared grid."""
        with card("controls", "Run", height=imgui.get_font_size() * 4.5):
            g = grid(["threshold"])
            g.row("threshold")
            imgui.set_next_item_width(g.w)
            _, self.threshold = imgui.slider_float(
                "##threshold", self.threshold, 0.0, 1.0
            )
            help_mark("components under this are dropped before the table is built")

    def draw(self) -> None:
        """One frame: controls, the ROI table, the traces and the transport."""
        section("ROIs")
        self.draw_controls()
        draw_filter_row(self.order)
        right_aligned_text(f"{len(self.deleted)} deleted")

        imgui.begin_child("table", imgui.ImVec2(0, imgui.get_font_size() * 12))
        current = self.order.current
        self.scroll_to_current = draw_table(
            self.order,
            ["id", "area", "snr"],
            {"area": lambda i: f"{self.area[i]:.0f}", "snr": lambda i: f"{self.snr[i]:.2f}"},
            self.scroll_to_current,
            on_select=self.select,
            actions=self.actions,
            row_color=lambda i: (0.5, 0.5, 0.5) if i in self.deleted else None,
        )
        imgui.end_child()
        if self.order.current != current and self.order.current is not None:
            self.select(self.order.current)

        section("Movie")
        if self.player.draw():
            pass  # a real viewer would push self.player.frame() into its image

        section("Traces")
        moved = self.plot.draw()
        if moved is not None:
            self.player.jump_to(moved % self.player.n_frames)

        self.keybinds.render_window()
        self.debugger.capture()
        self.debugger.render_window()

    def draw_menu(self) -> None:
        """The View menu: the keybinds panel and the inspector."""
        if imgui.begin_menu("View"):
            self.keybinds.menu_item()
            self.debugger.menu_item()
            imgui.end_menu()


VIEWER = RoiViewer()

if __name__ == "__main__":
    params = hello_imgui.RunnerParams()
    params.app_window_params.window_title = "roi_viewer"
    params.app_window_params.window_geometry.size = (1200, 900)
    params.imgui_window_params.show_menu_bar = True
    params.callbacks.show_menus = VIEWER.draw_menu
    params.callbacks.show_gui = VIEWER.draw
    immapp.run(runner_params=params, add_ons_params=immapp.AddOnsParams(with_implot=True))
