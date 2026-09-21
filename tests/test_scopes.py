"""Scopes collect the right rows and hand back working setters."""

import sys

import pytest

from imgui_debugger.scopes import (
    Watch,
    children_of,
    class_children,
    frame_children,
    frame_scopes,
    has_children,
    instance_children,
    object_scopes,
    property_children,
    runtime_scope,
)


class Widget:
    name = "ROIs"
    limit = 10

    def __init__(self):
        self.visible = True
        self.threshold = 0.4
        self._cache = {}

    @property
    def doubled(self):
        return self.threshold * 2

    @property
    def broken(self):
        raise RuntimeError("not ready")

    @property
    def editable_prop(self):
        return self.limit

    @editable_prop.setter
    def editable_prop(self, value):
        self.limit = value

    def draw(self):
        pass


class Slotted:
    __slots__ = ("a", "b")

    def __init__(self):
        self.a = 1
        self.b = 2


def test_instance_children_skip_private_by_default():
    names = [c.name for c in instance_children(Widget())]
    assert names == ["visible", "threshold"]
    assert "_cache" in [c.name for c in instance_children(Widget(), private=True)]


def test_instance_children_include_slots():
    assert [c.name for c in instance_children(Slotted())] == ["a", "b"]


def test_instance_setter_writes_the_attribute():
    w = Widget()
    row = next(c for c in instance_children(w) if c.name == "threshold")
    row.setter(0.9)
    assert w.threshold == 0.9


def test_property_rows_are_evaluated_live():
    w = Widget()
    rows = {c.name: c for c in property_children(w)}
    assert rows["doubled"].value == pytest.approx(0.8)
    w.threshold = 1.0
    assert property_children(w)[0].value is not None


def test_property_without_setter_is_read_only():
    rows = {c.name: c for c in property_children(Widget())}
    assert not rows["doubled"].editable
    assert rows["editable_prop"].editable


def test_raising_property_becomes_an_error_row():
    rows = {c.name: c for c in property_children(Widget())}
    assert rows["broken"].kind == "error"
    assert isinstance(rows["broken"].value, RuntimeError)


def test_class_children_skip_methods_and_properties():
    names = {c.name for c in class_children(Widget())}
    assert names == {"name", "limit"}


def test_mapping_and_sequence_rows():
    assert [c.name for c in children_of({"fs": 1})] == ["fs"]
    assert [c.name for c in children_of([4, 5])] == ["[0]", "[1]"]
    assert not children_of((1, 2))[0].editable


def test_mapping_setter_writes_through():
    md = {"fs": 1.0}
    children_of(md)[0].setter(9.0)
    assert md["fs"] == 9.0


def test_max_items_caps_rows():
    assert len(children_of(list(range(500)), max_items=10)) == 10


def test_has_children_is_false_for_scalars():
    assert not has_children(3)
    assert has_children(Widget())


def test_object_scopes_order_and_names():
    assert [s.name for s in object_scopes(Widget())] == ["instance", "properties", "class"]
    assert [s.name for s in object_scopes(Widget(), class_attrs=False)] == [
        "instance",
        "properties",
    ]


def test_frame_children_read_locals_and_skip_modules():
    marker = 7
    rows = {c.name: c for c in frame_children(sys._getframe())}
    assert rows["marker"].value == 7
    assert "sys" not in rows
    assert rows["marker"].setter is None


def test_frame_globals_are_writable():
    rows = {c.name: c for c in frame_children(sys._getframe(), "global")}
    assert rows["Widget"].setter is not None


def test_frame_scopes_names():
    assert [s.name for s in frame_scopes(sys._getframe())] == ["locals", "globals"]


def test_watch_reads_callables_every_time():
    counter = {"n": 0}
    watch = Watch("counter", lambda: dict(counter))
    counter["n"] = 5
    assert watch.read() == {"n": 5}
    assert [c.name for c in watch.children()] == ["n"]


def test_watch_error_becomes_a_row():
    watch = Watch("boom", lambda: 1 / 0)
    rows = watch.children()
    assert rows[0].kind == "error"


def test_runtime_scope_is_lazy():
    scope = runtime_scope()
    assert scope.name == "imgui"
    assert callable(scope.children)
