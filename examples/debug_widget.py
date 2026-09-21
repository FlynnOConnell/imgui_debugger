"""Embed the debugger in an app that draws its own widget.

The widget owns the debugger, calls ``capture()`` so the tree follows its draw
method's locals, and toggles the window with F12. Run it with
``python examples/debug_widget.py``.
"""

from imgui_bundle import hello_imgui, imgui, immapp

from imgui_debugger import Theme, attach


class RoiWidget:
    """A stand-in for a real imgui widget, with the state one usually has."""

    name = "ROIs"
    engines = ("mean", "suite2p", "masknmf")

    def __init__(self):
        self.visible = True
        self.engine = 0
        self.threshold = 0.4
        self.accent = (0.2, 0.5, 0.85, 1.0)
        self.selected = []
        self.metadata = {"fs": 9.6, "planes": [1, 2, 3], "si": {"version": 2023}}
        self._frames = 0
        self.debugger = attach(self, title="ROIs widget", value_col=200.0)

    @property
    def engine_name(self) -> str:
        """The engine the combo currently points at."""
        return self.engines[self.engine]

    def draw(self) -> None:
        """Draw the widget, then the debugger window over the same frame."""
        self._frames += 1
        rows_this_frame = len(self.selected)

        imgui.text(f"{self.name} — engine {self.engine_name}")
        _, self.visible = imgui.checkbox("visible", self.visible)
        _, self.threshold = imgui.slider_float("threshold", self.threshold, 0.0, 1.0)
        _, self.engine = imgui.combo("engine", self.engine, list(self.engines))
        if imgui.button("add roi"):
            self.selected.append({"uid": len(self.selected), "area": 120})
        imgui.same_line()
        if imgui.button("clear"):
            self.selected.clear()
        imgui.text_disabled(f"{rows_this_frame} selected, frame {self._frames}")

        if imgui.is_key_pressed(imgui.Key.f12):
            self.debugger.toggle()
        # capture here so the tree's locals scope follows this method
        self.debugger.capture()
        self.debugger.render_window()


WIDGET = RoiWidget()
CONFIG = dict(window_title="debug_widget", theme=Theme.dark())

if __name__ == "__main__":
    params = hello_imgui.RunnerParams()
    params.app_window_params.window_title = CONFIG["window_title"]
    params.app_window_params.window_geometry.size = (900, 700)
    params.callbacks.show_gui = WIDGET.draw
    immapp.run(runner_params=params)
