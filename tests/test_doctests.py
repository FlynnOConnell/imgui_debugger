"""Every docstring example runs; the ones needing a live frame are +SKIP."""

import doctest
import importlib

import pytest

MODULES = [
    "imgui_debugger",
    "imgui_debugger._assets",
    "imgui_debugger.debugger",
    "imgui_debugger.edit",
    "imgui_debugger.format",
    "imgui_debugger.runner",
    "imgui_debugger.scopes",
    "imgui_debugger.search",
    "imgui_debugger.style",
    "imgui_debugger.theme",
    "imgui_debugger.tree",
]


@pytest.mark.parametrize("name", MODULES)
def test_module_doctests(name):
    module = importlib.import_module(name)
    result = doctest.testmod(module, verbose=False)
    assert result.failed == 0, f"{name}: {result.failed} failing examples"
    assert result.attempted > 0, f"{name}: no runnable examples"
