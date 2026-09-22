"""The ported player, trace plot and popups, away from a live frame."""

import numpy as np
import pytest

from imgui_debugger import (
    KeybindsConfig,
    KeybindsPanel,
    MoviePlayer,
    Panel,
    TracePlot,
    crop_slices,
    draw_keybinds_popup,
    draw_path_popup,
)

MOVIE = np.arange(5 * 4 * 6, dtype=np.float32).reshape(5, 4, 6)


def test_crop_inside_the_fov():
    dst, src = crop_slices(1, 2, (2, 2), (4, 6))
    assert (src[0].start, src[0].stop) == (1, 3)
    assert (dst[0].start, dst[0].stop) == (0, 2)


def test_crop_clipped_at_the_top_left():
    dst, src = crop_slices(-1, -2, (3, 4), (4, 6))
    assert (src[0].start, src[1].start) == (0, 0)
    assert (dst[0].start, dst[1].start) == (1, 2)


def test_crop_entirely_outside_is_none():
    assert crop_slices(99, 0, (2, 2), (4, 6)) is None
    assert crop_slices(0, -99, (2, 2), (4, 6)) is None


def test_player_without_a_movie():
    player = MoviePlayer()
    assert player.n_frames == 0
    assert player.frame() is None
    assert player.draw() is False


def test_player_frame_is_two_dimensional():
    player = MoviePlayer(MOVIE)
    assert player.frame().shape == (4, 6)


def test_player_crop_is_zero_padded():
    player = MoviePlayer(MOVIE)
    out = player.frame((-1, -1, 3, 3))
    assert out.shape == (3, 3)
    assert out[0].tolist() == [0.0, 0.0, 0.0]
    assert out[1, 1] == MOVIE[0, 0, 0]


def test_player_seek_is_clamped():
    player = MoviePlayer(MOVIE)
    player.jump_to(99)
    assert player.t == 4
    player.jump_to(-4)
    assert player.t == 0


def test_player_swap_clamps_the_playhead():
    player = MoviePlayer(MOVIE)
    player.jump_to(4)
    player.set_movie(MOVIE[:2])
    assert player.t == 1


def test_player_swap_to_the_same_movie_keeps_the_frame():
    player = MoviePlayer(MOVIE)
    player.jump_to(3)
    player.set_movie(MOVIE)
    assert player.t == 3


def test_trace_plot_panels_and_frame():
    plot = TracePlot(["raw", "dff"], 20)
    assert plot.panels == ("raw", "dff")
    plot.frame = 99
    assert plot.frame == 19
    plot.frame = -5
    assert plot.frame == 0


def test_trace_plot_rejects_a_wrong_length_trace():
    plot = TracePlot(["raw"], 10)
    with pytest.raises(ValueError):
        plot.set("raw", [("a", np.zeros(9), None)])


def test_trace_plot_rejects_mismatched_timings():
    with pytest.raises(ValueError):
        TracePlot(["raw"], 10, frame_timings=np.arange(5))


def test_trace_plot_x_switches_to_time():
    plot = TracePlot(["raw"], 4, frame_timings=np.array([0.0, 0.5, 1.0, 1.5]))
    assert plot.x.tolist() == [0.0, 1.0, 2.0, 3.0]
    plot._use_time = True
    assert plot.x.tolist() == [0.0, 0.5, 1.0, 1.5]


def test_trace_plot_timings_equal_to_frames_are_dropped():
    plot = TracePlot(["raw"], 4, frame_timings=np.arange(4))
    plot._use_time = True
    assert plot.x.tolist() == [0.0, 1.0, 2.0, 3.0]


def test_trace_plot_set_and_clear():
    plot = TracePlot(["raw"], 5)
    plot.set("raw", [("a", np.zeros(5), None), ("b", np.ones(5), (1.0, 0.0, 0.0))])
    assert len(plot.lines("raw")) == 2
    plot.clear()
    assert plot.lines("raw") == []


def test_trace_plot_y_limits_are_padded():
    plot = TracePlot(["raw"], 4)
    plot.set("raw", [("a", np.array([0.0, 1.0, 2.0, 4.0]), None)])
    lo, hi = plot._y_limits(("raw",))
    assert lo < 0.0 and hi > 4.0


def test_trace_plot_y_limits_without_lines():
    assert TracePlot(["raw"], 4)._y_limits(("raw",)) is None


def test_trace_plot_marks_and_spans_are_clamped():
    plot = TracePlot(["raw"], 5)
    plot.mark("onset", [-2, 99])
    plot.span("stim", [-1], [99])
    assert plot._marks[0][1].tolist() == [0, 4]
    assert plot._spans[0][1].tolist() == [0]
    assert plot._spans[0][2].tolist() == [4]
    plot.clear_events()
    assert plot._marks == [] and plot._spans == []


def test_trace_plot_follow_maps_a_time_to_a_frame():
    plot = TracePlot(["raw"], 4, frame_timings=np.array([0.0, 0.5, 1.0, 1.5]))
    plot._follow(np.array([0.0, 0.5, 1.0, 1.5]), 1.0)
    assert plot.frame == 2


def test_trace_plot_fit_is_one_shot():
    plot = TracePlot(["raw"], 5)
    plot.set("raw", [("a", np.zeros(5), None)])
    assert plot._resolve_fit() is True
    assert plot._resolve_fit() is False


def test_trace_plot_without_autofit_keeps_the_zoom():
    plot = TracePlot(["raw"], 5, autofit=False)
    plot.set("raw", [("a", np.zeros(5), None)])
    assert plot._resolve_fit() is True  # first data always fits
    plot.set("raw", [("a", np.ones(5), None)])
    assert plot._resolve_fit() is False


def test_keybinds_panel_is_a_panel():
    panel = KeybindsPanel(bindings=[("t", "trace")])
    assert isinstance(panel, Panel)
    assert panel.visible is False
    assert panel.config.bindings == [("t", "trace")]


def test_keybinds_panel_config_wins_over_the_shorthand():
    panel = KeybindsPanel(KeybindsConfig(title="Keys", bindings=[("a", "b")]))
    assert panel.title == "Keys"


def test_closed_popups_draw_nothing():
    assert draw_keybinds_popup([("t", "trace")], False) is False
    assert draw_path_popup("Open", False, "p", "hint", "Open") == (False, "p", False)
