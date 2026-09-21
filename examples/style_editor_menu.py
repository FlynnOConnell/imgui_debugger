"""The style editor behind a menu item, with the host app's own Save and Load.

Everything a consuming repo needs is in ``App``: build one ``StyleEditor`` with
``on_save`` / ``on_load`` pointing at wherever that app already keeps settings,
draw ``menu_item()`` in a menu, and call ``render_window()`` once per frame.
Run it with ``python examples/style_editor_menu.py``.
"""

import json
from pathlib import Path

from imgui_bundle import hello_imgui, imgui, immapp

from imgui_debugger import StyleEditor, StyleEditorConfig

SETTINGS = Path.home() / ".my_app" / "settings.json"


class App:
    """A host app that keeps the style inside its own settings file."""

    def __init__(self):
        self.style_editor = StyleEditor(
            StyleEditorConfig(
                title="Style",
                save_label="Save to settings",
                load_label="Load from settings",
                on_save=self.save_style,
                on_load=self.load_style,
            )
        )
        self.style_editor.visible = False

    def save_style(self, data: dict) -> None:
        """Write the serialized style into the app's own settings file."""
        SETTINGS.parent.mkdir(parents=True, exist_ok=True)
        settings = json.loads(SETTINGS.read_text()) if SETTINGS.exists() else {}
        settings["style"] = data
        SETTINGS.write_text(json.dumps(settings, indent=2))

    def load_style(self):
        """Return the style stored in the settings file, or None to cancel."""
        if not SETTINGS.exists():
            return None
        return json.loads(SETTINGS.read_text()).get("style")

    def draw_menu(self) -> None:
        """Draw the app menu bar with the style editor entry in it."""
        if imgui.begin_menu("View"):
            self.style_editor.menu_item("Style Editor", "Ctrl+,")
            imgui.end_menu()

    def draw(self) -> None:
        """Draw the app body, then the style editor window when it is open."""
        imgui.text("app content")
        imgui.button("a themed button")
        self.style_editor.render_window()


APP = App()

if __name__ == "__main__":
    params = hello_imgui.RunnerParams()
    params.app_window_params.window_title = "style_editor_menu"
    params.app_window_params.window_geometry.size = (900, 700)
    params.imgui_window_params.show_menu_bar = True
    params.callbacks.show_menus = APP.draw_menu
    params.callbacks.show_gui = APP.draw
    immapp.run(runner_params=params)
