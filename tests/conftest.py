"""Shared fixtures."""

import pytest
from imgui_bundle import imgui


@pytest.fixture
def imgui_context():
    """A bare imgui context, for code that reads or writes the active style.

    No backend and no frame: enough for ``imgui.get_style()``, not for drawing.
    """
    ctx = imgui.create_context()
    try:
        yield ctx
    finally:
        imgui.destroy_context(ctx)
