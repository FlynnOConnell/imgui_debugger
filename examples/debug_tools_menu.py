"""Every debug tool behind one menu, with no demo window involved.

Two calls wire the whole set into a host app: ``tools.draw_menu()`` in the menu
bar and ``tools.render()`` once per frame. Panels can be configured, dropped or
replaced individually. Run it with ``python examples/debug_tools_menu.py``.
"""

from imgui_bundle import hello_imgui, imgui, immapp

from imgui_debugger import (
    DebugTools,
    Hotkey,
    StyleEditor,
    StyleEditorConfig,
    UserGuidePanel,
)


class App:
    """A host app that owns one DebugTools set."""

    def __init__(self):
        self.threshold = 0.4
        self.tags = ["roi", "plane"]
        self.metadata = {"fs": 9.6, "si": {"version": 2023}}

        self.tools = DebugTools.default(self, menu_label="Debug", value_col=200.0)
        # a hotkey on the inspector, and one on the metrics window
        self.tools["Debugger"].config.hotkey = Hotkey(imgui.Key.f12)
        self.tools["Metrics / Debugger"].config.hotkey = Hotkey(imgui.Key.f11)
        # replace the default style editor with one that saves where we want,
        # shows only the Colors tab, and calls itself Theme
        self.tools.remove("Style Editor")
        self.tools.add(
            StyleEditor(
                StyleEditorConfig(
                    title="Theme",
                    visible=False,
                    save_label="Save to project",
                    load_label="Load from project",
                    on_save=self.save_style,
                    on_load=self.load_style,
                    show_sizes=False,
                    show_rendering=False,
                    hotkey=Hotkey(imgui.Key.t, ctrl=True),
                )
            )
        )
        self.tools.add(UserGuidePanel())
        self.style = None

    def save_style(self, data: dict) -> None:
        """Keep the style on the app instead of writing a file."""
        self.style = data

    def load_style(self):
        """Hand back the style the app is holding, or None to cancel."""
        return self.style

    def draw_menu(self) -> None:
        """Draw the app's menus, including the whole debug set."""
        self.tools.draw_menu()

    def draw(self) -> None:
        """Draw the app body, then every open debug panel."""
        imgui.text("app content")
        _, self.threshold = imgui.slider_float("threshold", self.threshold, 0.0, 1.0)
        self.tools.debugger().capture()
        self.tools.render()


APP = App()

if __name__ == "__main__":
    params = hello_imgui.RunnerParams()
    params.app_window_params.window_title = "debug_tools_menu"
    params.app_window_params.window_geometry.size = (1100, 760)
    params.imgui_window_params.show_menu_bar = True
    params.callbacks.show_menus = APP.draw_menu
    params.callbacks.show_gui = APP.draw
    immapp.run(runner_params=params)
