"""Themes are plain data and need no imgui context."""

import pytest
from imgui_bundle import imgui

from imgui_debugger import Theme, to_vec4


def test_dark_is_the_default():
    assert Theme.dark() == Theme()


def test_light_differs_on_every_background_role():
    dark, light = Theme.dark(), Theme.light()
    assert dark.bg != light.bg
    assert dark.node != light.node


def test_replace_returns_a_copy():
    base = Theme.dark()
    tweaked = base.replace(name=(1.0, 0.0, 0.0, 1.0))
    assert tweaked.name == (1.0, 0.0, 0.0, 1.0)
    assert base.name != tweaked.name


def test_to_vec4_fills_in_alpha():
    v = to_vec4((0.1, 0.2, 0.3))
    assert (v.x, v.y, v.z, v.w) == pytest.approx((0.1, 0.2, 0.3, 1.0))


def test_to_vec4_passes_through_a_vec4():
    v = imgui.ImVec4(1.0, 1.0, 1.0, 0.5)
    assert to_vec4(v) is v
