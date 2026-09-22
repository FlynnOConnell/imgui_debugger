"""Every debug tool behind one menu, with its config saved and auto-loaded.

Three calls wire the whole set into a host app: ``tools.draw_menu()`` in the
menu bar, ``tools.render()`` once per frame, and the store calls that make it
come back the way it was left. Run it with
``python examples/debug_tools_menu.py``.
"""

from pathlib import Path

from imgui_bundle import hello_imgui, imgui, immapp

from imgui_debugger import (
    ConfigStore,
    DebugTools,
    Hotkey,
    StyleEditor,
    StyleEditorConfig,
    UserGuidePanel,
)

# a host app points this at its own settings dir
STORE = ConfigStore(Path.home() / ".my_app" / "imgui")


class App:
    """A host app that owns one DebugTools set backed by a ConfigStore."""

    def __init__(self):
        self.threshold = 0.4
        self.tags = ["roi", "plane"]
        self.metadata = {"fs": 9.6, "si": {"version": 2023}}

        self.tools = DebugTools.default(
            self, menu_label="Debug", store=STORE, value_col=200.0
        )
        self.tools["Debugger"].config.hotkey = Hotkey(imgui.Key.f12)
        self.tools["Metrics / Debugger"].config.hotkey = Hotkey(imgui.Key.f11)
        # the style editor on its own menu item
        self.tools.remove("Style Editor")
        self.tools.add(
            StyleEditor(
                StyleEditorConfig(
                    title="Style",
                    visible=False,
                    store=STORE,
                    hotkey=Hotkey(imgui.Key.t, ctrl=True),
                )
            )
        )
        self.tools.add(UserGuidePanel())
        # restore which panels were open and how they were configured
        self.tools.load_state()

    def post_init(self) -> None:
        """Apply the saved style once the imgui context exists."""
        self.tools.apply_style()

    def before_exit(self) -> None:
        """Write the panel state back so the next launch matches this one."""
        self.tools.save_state()

    def draw_menu(self) -> None:
        """Draw the app's menus, including the whole debug set."""
        if imgui.begin_menu("View"):
            self.tools["Style"].menu_item()
            imgui.end_menu()
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
    # window geometry is imgui's to persist
    params.ini_filename = STORE.layout_ini
    params.ini_folder_type = hello_imgui.IniFolderType.absolute_path
    params.callbacks.post_init = APP.post_init
    params.callbacks.before_exit = APP.before_exit
    params.callbacks.show_menus = APP.draw_menu
    params.callbacks.show_gui = APP.draw
    immapp.run(runner_params=params)
