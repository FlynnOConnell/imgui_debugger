"""The merged RoiOrder: both repos' filtering, sorting and cursor behaviour."""

import numpy as np
import pytest

from imgui_debugger import FILTER_ALL, UNLABELED, RoiOrder, RowAction

AREAS = np.array([10.0, 30.0, 20.0, 40.0])
LABELS = np.array([0, 1, -1, 0])


def make_order(**kwargs):
    """A four-item order over the module's fixtures."""
    return RoiOrder({"area": AREAS, "keep": np.array([0, 1, 0, 1])}, 4, **kwargs)


def test_starts_in_natural_order():
    assert make_order().order.tolist() == [0, 1, 2, 3]


def test_sort_by_name_ascending_and_descending():
    order = make_order()
    order.sort_by = "area"
    order.rebuild()
    assert order.order.tolist() == [0, 2, 1, 3]
    order.ascending = False
    order.rebuild()
    assert order.order.tolist() == [3, 1, 2, 0]


def test_no_sort_column_reverses_on_descending():
    order = make_order()
    order.ascending = False
    order.rebuild()
    assert order.order.tolist() == [3, 2, 1, 0]


def test_range_filter_spans_the_column():
    order = make_order()
    order.set_range_column("area")
    assert order.range_span == (10.0, 40.0)
    order.range_limits = (15.0, 35.0)
    order.rebuild()
    assert order.order.tolist() == [1, 2]


def test_range_column_ignores_non_finite():
    order = RoiOrder({"a": np.array([1.0, np.nan, 5.0])}, 3)
    order.set_range_column("a")
    assert order.range_span == (1.0, 5.0)


def test_pinned_column_sorts_first():
    order = make_order(pinned="keep")
    order.sort_by = "area"
    order.rebuild()
    assert order.order.tolist()[:2] == [1, 3]


def test_label_filter_needs_labels():
    order = make_order()
    order.filter_label = 0
    order.rebuild()
    assert len(order.order) == 4


def test_label_filter_applies_when_labels_are_given():
    order = make_order(labels=LABELS)
    order.filter_label = 0
    order.rebuild()
    assert order.order.tolist() == [0, 3]
    order.filter_label = UNLABELED
    order.rebuild()
    assert order.order.tolist() == [2]
    order.filter_label = FILTER_ALL
    order.rebuild()
    assert len(order.order) == 4


def test_cursor_follows_its_item_across_a_resort():
    order = make_order()
    order.goto(3)
    order.sort_by = "area"
    order.ascending = False
    order.rebuild()
    assert order.current == 3


def test_step_is_clamped():
    order = make_order()
    order.step(99)
    assert order.pos == 3
    order.step(-99)
    assert order.pos == 0


def test_goto_fails_for_a_filtered_item():
    order = make_order()
    order.set_range_column("area")
    order.range_limits = (0.0, 15.0)
    order.rebuild()
    assert order.goto(3) is False


def test_hidden_by_names_every_filter():
    order = make_order(labels=LABELS)
    order.set_range_column("area")
    order.range_limits = (0.0, 15.0)
    order.filter_label = 1
    assert set(order.hidden_by(3)) == {"label", "area"}
    assert order.hidden(3) is True
    assert order.hidden(0) is True


def test_reveal_clears_the_filters_that_hid_it():
    order = make_order(labels=LABELS)
    order.set_range_column("area")
    order.range_limits = (0.0, 15.0)
    order.rebuild()
    cleared = order.reveal(3)
    assert cleared == ["area"]
    assert order.current == 3


def test_reveal_is_a_noop_for_a_visible_item():
    order = make_order()
    assert order.reveal(2) == []


def test_next_unlabeled_wraps():
    order = make_order(labels=LABELS)
    assert order.next_unlabeled() is True
    assert order.current == 2
    assert order.next_unlabeled() is True
    assert order.current == 2


def test_next_unlabeled_without_labels():
    assert make_order().next_unlabeled() is False


def test_next_unlabeled_when_everything_is_labeled():
    order = make_order(labels=np.zeros(4, dtype=int))
    assert order.next_unlabeled() is False


def test_step_group_moves_to_the_next_class():
    order = make_order(labels=LABELS)
    order.goto(0)
    assert order.step_group(1) is True
    assert int(LABELS[order.current]) == 1


def test_step_group_needs_two_classes():
    order = make_order(labels=np.zeros(4, dtype=int))
    assert order.step_group(1) is False


def test_empty_view_has_no_current():
    order = make_order()
    order.set_range_column("area")
    order.range_limits = (100.0, 200.0)
    order.rebuild()
    assert order.current is None
    assert order.step(1) is False


def test_row_action_disabled_defaults_to_none():
    calls = []
    action = RowAction("x", "delete", calls.append)
    action.on_click(3)
    assert calls == [3]
    assert action.disabled is None


def test_clear_filter_ignores_an_unknown_name():
    order = make_order()
    order.clear_filter("nope")
    assert order.range_column is None


@pytest.mark.parametrize("n", [0, 1])
def test_small_orders_do_not_raise(n):
    order = RoiOrder({"a": np.arange(n, dtype=float)}, n)
    order.rebuild()
    assert len(order.order) == n
