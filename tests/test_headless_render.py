"""Render the debugger for a few frames on hello_imgui's null backend.

This walks the real draw path — toolbar, scope headers, nested nodes, inline
editors, the imgui runtime scope — with no window or GPU. If the null backend
cannot initialize here the test skips rather than fails.
"""

import pytest

from imgui_debugger import Debugger, DebuggerConfig, Theme, attach, ensure_assets

STATE = {"frames": 0, "debugger": None}


class Nested:
    def __init__(self):
        self.depth = 2
        self.tags = ["roi", "plane"]


class Widget:
    name = "ROIs"

    def __init__(self):
        self.visible = True
        self.threshold = 0.4
        self.accent = (0.2, 0.5, 0.85, 1.0)
        self.label = "trace"
        self.metadata = {"fs": 9.6, "planes": [1, 2, 3], "si": {"version": 2023}}
        self.child = Nested()
        self._private = "hidden"

    @property
    def doubled(self):
        return self.threshold * 2

    @property
    def broken(self):
        raise RuntimeError("not ready")


def _enable_textures():
    """Tell imgui the null renderer has textures so NewFrame does not assert."""
    from imgui_bundle import imgui

    imgui.get_io().backend_flags |= imgui.BackendFlags_.renderer_has_textures


def _null_runner_params():
    """Runner params on the null platform and renderer backends."""
    from imgui_bundle import hello_imgui

    p = hello_imgui.RunnerParams()
    p.platform_backend_type = hello_imgui.PlatformBackendType.null
    p.renderer_backend_type = hello_imgui.RendererBackendType.null
    p.app_window_params.window_geometry.size = (520, 780)
    p.ini_folder_type = hello_imgui.IniFolderType.temp_folder
    p.ini_filename = "imgui_debugger_test.ini"
    p.callbacks.post_init = _enable_textures
    return p


def _gui():
    """Drive the debugger through filter, expand and collapse over five frames."""
    from imgui_bundle import hello_imgui

    dbg = STATE["debugger"]
    STATE["frames"] += 1
    if STATE["frames"] == 2:
        dbg.set_filter("fs")
    if STATE["frames"] == 3:
        dbg.set_filter("")
        dbg.expand_all()
    if STATE["frames"] == 4:
        dbg.collapse_all()
        dbg.config.private = True
    dbg.render()
    dbg.render_window()
    if STATE["frames"] >= 5:
        hello_imgui.get_runner_params().app_shall_exit = True


def _run(dbg):
    """Run five frames with ``dbg`` as the debugger, skipping if the backend is absent."""
    from imgui_bundle import hello_imgui

    STATE["frames"] = 0
    STATE["debugger"] = dbg
    params = _null_runner_params()
    params.callbacks.show_gui = _gui
    try:
        hello_imgui.run(params)
    except Exception as exc:
        pytest.skip(f"null backend unavailable: {exc}")
    return STATE["frames"]


def test_headless_render_smoke():
    ensure_assets()
    dbg = attach(Widget(), title="Widget", value_col=220.0)
    assert _run(dbg) >= 5
    assert dbg.config.private is True


def test_headless_render_with_watches_and_light_theme():
    ensure_assets()
    dbg = Debugger(
        DebuggerConfig(
            target=Widget(),
            theme=Theme.light(),
            editable=False,
            show_frame=False,
            max_depth=2,
        )
    )
    dbg.watch("counters", lambda: {"frames": STATE["frames"]})
    assert _run(dbg) >= 5


def test_headless_render_with_no_target():
    ensure_assets()
    dbg = Debugger(DebuggerConfig(show_toolbar=False))
    assert _run(dbg) >= 5


STYLE_STATE = {"frames": 0, "editor": None, "saved": None}


def _style_gui():
    """Draw the style editor's menu entry, window and every tab body."""
    from imgui_bundle import hello_imgui, imgui

    editor = STYLE_STATE["editor"]
    STYLE_STATE["frames"] += 1
    if imgui.begin_main_menu_bar():
        if imgui.begin_menu("View"):
            editor.menu_item("Style Editor", "Ctrl+,")
            imgui.end_menu()
        imgui.end_main_menu_bar()
    editor.render_window()
    editor.draw_toolbar()
    editor.draw_sizes()
    editor.draw_colors()
    editor.draw_rendering()
    if STYLE_STATE["frames"] == 2:
        editor.filter = "text"
        editor.save()
    if STYLE_STATE["frames"] == 3:
        editor.load()
    if STYLE_STATE["frames"] == 4:
        editor.revert()
    if STYLE_STATE["frames"] >= 5:
        hello_imgui.get_runner_params().app_shall_exit = True


def test_headless_style_editor_render():
    from imgui_bundle import hello_imgui

    from imgui_debugger import StyleEditor, StyleEditorConfig

    ensure_assets()
    editor = StyleEditor(StyleEditorConfig(on_save=_remember_save, on_load=_replay_save))
    STYLE_STATE["frames"] = 0
    STYLE_STATE["editor"] = editor
    STYLE_STATE["saved"] = None
    params = _null_runner_params()
    params.callbacks.show_gui = _style_gui
    try:
        hello_imgui.run(params)
    except Exception as exc:
        pytest.skip(f"null backend unavailable: {exc}")
    assert STYLE_STATE["frames"] >= 5
    assert STYLE_STATE["saved"] is not None
    assert editor.status == "reverted"


def _remember_save(data):
    """Save hook: keep the serialized style in module state."""
    STYLE_STATE["saved"] = data


def _replay_save():
    """Load hook: hand back whatever the save hook kept."""
    return STYLE_STATE["saved"]
