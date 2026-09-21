"""The filter matches nested values, stays bounded, and caches per filter string."""

from imgui_debugger import search
from imgui_debugger.scopes import Child
from imgui_debugger.search import clear_cache, filter_children, matches, matches_shallow


def test_empty_filter_matches_everything():
    assert matches("anything", object(), "")


def test_name_and_value_both_match():
    assert matches_shallow("frame_rate", 30, "rate")
    assert matches_shallow("frame_rate", 30, "30")


def test_nested_mapping_matches():
    assert matches("arr", {"meta": {"dz": 5}}, "dz")
    assert not matches("arr", {"meta": {"dz": 5}}, "fs")


def test_nested_sequence_matches():
    assert matches("planes", [{"z": 3}], "z")


def test_depth_is_bounded():
    deep = {"a": {"b": {"c": {"d": {"e": {"f": {"g": {"h": "needle"}}}}}}}}
    clear_cache()
    assert not matches("root", deep, "needle")


def test_width_is_bounded():
    wide = {f"k{i}": i for i in range(200)}
    wide["k199"] = "needle"
    clear_cache()
    assert not matches("root", wide, "needle")


def test_cache_resets_on_a_new_filter():
    clear_cache()
    assert matches("fs", 1, "fs")
    assert search._cache_filter == "fs"
    matches("dz", 1, "dz")
    assert search._cache_filter == "dz"


def test_cache_rejects_a_recycled_id():
    clear_cache()
    assert matches("row", {"a": 1}, "a")
    assert len(search._cache) >= 1


def test_filter_children_keeps_matching_rows():
    rows = [Child("fs", 9.6), Child("dz", 5)]
    assert [c.name for c in filter_children(rows, "dz")] == ["dz"]
    assert len(filter_children(rows, "")) == 2
