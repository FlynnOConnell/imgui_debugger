"""Which leaves get an inline editor, and which are left read-only."""

from imgui_debugger.edit import MAX_EDIT_STR, can_edit, is_color


def test_scalars_are_editable():
    assert can_edit(True)
    assert can_edit(3)
    assert can_edit(1.5)
    assert can_edit("path/to/file")


def test_huge_strings_are_not_editable():
    assert not can_edit("x" * (MAX_EDIT_STR + 1))


def test_containers_and_objects_are_not_editable():
    assert not can_edit([1, 2])
    assert not can_edit({"a": 1})
    assert not can_edit(object())


def test_color_tuples_are_recognized():
    assert is_color((0.1, 0.2, 0.3))
    assert is_color([0.1, 0.2, 0.3, 1.0])
    assert can_edit((0.1, 0.2, 0.3))


def test_non_colors_are_rejected():
    assert not is_color((1, 2, 3))
    assert not is_color((0.1, 0.2))
    assert not is_color((0.1, 0.2, 2.0))
    assert not is_color("red")
