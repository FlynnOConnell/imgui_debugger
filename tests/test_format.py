"""Value formatting is total: every input yields one short line."""

from imgui_debugger.format import fmt_error, fmt_value, is_container, type_label


class Hostile:
    def __repr__(self):
        raise RuntimeError("no repr for you")


def test_scalars_render_as_repr():
    assert fmt_value(None) == "None"
    assert fmt_value(True) == "True"
    assert fmt_value(3) == "3"
    assert fmt_value(2.5) == "2.5"


def test_long_strings_are_truncated():
    out = fmt_value("x" * 400)
    assert out.endswith("...'")
    assert len(out) < 300


def test_bytes_and_big_lists_are_summarized():
    assert fmt_value(b"abcd") == "<4 bytes>"
    assert fmt_value(list(range(50))) == "<list[50]>"
    assert fmt_value([1, 2, 3]) == "[1, 2, 3]"


def test_hostile_repr_does_not_raise():
    assert fmt_value(Hostile()) == "<Hostile>"


def test_type_label_reports_length():
    assert type_label({"a": 1, "b": 2}) == "dict[2]"
    assert type_label(1.0) == "float"


def test_is_container_excludes_strings():
    assert is_container([1]) and is_container({"a": 1})
    assert not is_container("abc")


def test_fmt_error_names_the_exception():
    assert fmt_error(KeyError("fs")) == "<KeyError: 'fs'>"
