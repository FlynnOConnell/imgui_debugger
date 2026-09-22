"""A transport bar over any lazy ``(T, H, W)`` array.

Ported from the copies in ``masknmf.visualization.imgui.movie_player`` and
``mbo_utilities.gui.imgui.movie_player``, keeping the latter's clamped crop.

Examples
--------
>>> import numpy as np
>>> from imgui_debugger import MoviePlayer
>>> player = MoviePlayer(np.zeros((10, 4, 4)))
>>> player.n_frames, player.t
(10, 0)
>>> player.jump_to(99)
>>> player.t
9
"""

from __future__ import annotations

import time
from typing import Optional, Tuple

import numpy as np
from imgui_bundle import imgui


def crop_slices(top: int, left: int, size, fov) -> Optional[Tuple[tuple, tuple]]:
    """Destination and source slices for a crop clipped to the FOV.

    Parameters
    ----------
    top, left : int
        Top-left corner of the crop, which may sit outside the FOV.
    size : tuple[int, int]
        Crop height and width.
    fov : tuple[int, int]
        Source height and width.

    Returns
    -------
    tuple | None
        ``(dst_slices, src_slices)``, or None when the crop misses the FOV.

    Examples
    --------
    >>> from imgui_debugger.player import crop_slices
    >>> dst, src = crop_slices(-1, 0, (3, 3), (4, 4))
    >>> src[0].start, src[0].stop
    (0, 2)
    >>> crop_slices(99, 99, (2, 2), (4, 4)) is None
    True
    """
    h, w = size
    fov_h, fov_w = fov
    y0, y1 = max(top, 0), min(top + h, fov_h)
    x0, x1 = max(left, 0), min(left + w, fov_w)
    if y1 <= y0 or x1 <= x0:
        return None
    dst = (slice(y0 - top, y1 - top), slice(x0 - left, x1 - left))
    return dst, (slice(y0, y1), slice(x0, x1))


class MoviePlayer:
    """Play / pause, a frame slider and an fps box over a lazy movie.

    Any object with ``.shape`` and ``[t]`` / ``[t, rows, cols]`` indexing works,
    and only the frame on screen is read. It owns no window: :meth:`draw` goes
    inline in a panel the host already has. Playback advances off the wall
    clock inside :meth:`draw`, so fps is independent of the render rate.

    Parameters
    ----------
    movie : object | None
        A ``(T, H, W)`` indexable.
    fps : float
        Playback rate.

    Examples
    --------
    >>> import numpy as np
    >>> from imgui_debugger import MoviePlayer
    >>> player = MoviePlayer(np.arange(3 * 4 * 4).reshape(3, 4, 4))
    >>> player.jump_to(2)
    >>> player.frame().shape
    (4, 4)
    >>> player.draw()            # doctest: +SKIP
    False
    """

    def __init__(self, movie=None, fps: float = 30.0):
        self._movie = movie
        self._t = 0
        self._playing = False
        self._fps = fps
        self._clock: Optional[tuple] = None  # (wall time, frame) at play/seek

    @property
    def movie(self):
        """The movie being played.

        Examples
        --------
        >>> from imgui_debugger import MoviePlayer
        >>> MoviePlayer().movie is None
        True
        """
        return self._movie

    @property
    def n_frames(self) -> int:
        """How many frames the movie has, or 0 without one.

        Examples
        --------
        >>> import numpy as np
        >>> from imgui_debugger import MoviePlayer
        >>> MoviePlayer(np.zeros((7, 2, 2))).n_frames
        7
        """
        return 0 if self._movie is None else int(self._movie.shape[0])

    @property
    def t(self) -> int:
        """The frame currently shown.

        Examples
        --------
        >>> from imgui_debugger import MoviePlayer
        >>> MoviePlayer().t
        0
        """
        return self._t

    @property
    def playing(self) -> bool:
        """Whether playback is running.

        Examples
        --------
        >>> from imgui_debugger import MoviePlayer
        >>> MoviePlayer().playing
        False
        """
        return self._playing

    def set_movie(self, movie) -> None:
        """Swap the source, clamping the playhead into the new range.

        Parameters
        ----------
        movie : object
            The new ``(T, H, W)`` indexable.

        Examples
        --------
        >>> import numpy as np
        >>> from imgui_debugger import MoviePlayer
        >>> player = MoviePlayer(np.zeros((10, 2, 2)))
        >>> player.jump_to(9)
        >>> player.set_movie(np.zeros((3, 2, 2)))
        >>> player.t
        2
        """
        if movie is not self._movie:
            self._movie = movie
            self._t = min(self._t, max(self.n_frames - 1, 0))

    def jump_to(self, t: int) -> None:
        """Seek to a frame, clamped to the movie.

        Parameters
        ----------
        t : int
            Target frame, e.g. an ROI's peak.

        Examples
        --------
        >>> import numpy as np
        >>> from imgui_debugger import MoviePlayer
        >>> player = MoviePlayer(np.zeros((5, 2, 2)))
        >>> player.jump_to(-3)
        >>> player.t
        0
        """
        self._t = int(np.clip(t, 0, max(self.n_frames - 1, 0)))
        self._clock = (time.perf_counter(), float(self._t))

    def frame(self, region: Optional[tuple] = None) -> Optional[np.ndarray]:
        """The current frame as a 2D array, optionally cropped.

        Parameters
        ----------
        region : tuple | None
            ``(top, left, h, w)``; crops lazily, zero-padded where it runs past
            the FOV.

        Examples
        --------
        >>> import numpy as np
        >>> from imgui_debugger import MoviePlayer
        >>> player = MoviePlayer(np.ones((2, 4, 4)))
        >>> player.frame().shape
        (4, 4)
        >>> float(player.frame((-1, -1, 3, 3))[0, 0])
        0.0
        """
        if self._movie is None:
            return None
        if region is None:
            img = np.asarray(self._movie[self._t])
            return img.reshape(img.shape[-2:])
        top, left, h, w = region
        out = np.zeros((h, w), dtype=np.float32)
        slices = crop_slices(top, left, (h, w), self._movie.shape[1:3])
        if slices is not None:
            dst, (ys, xs) = slices
            img = np.asarray(self._movie[self._t, ys, xs])
            out[dst] = img.reshape(ys.stop - ys.start, xs.stop - xs.start)
        return out

    def draw(self, slider_width: float = 260.0, id_suffix: str = "") -> bool:
        """The transport controls; True on the frames where ``t`` moved.

        Pull :meth:`frame` on those frames and assign it to your image. Set
        vmin/vmax once when the movie changes rather than per frame, or the
        contrast chases each frame's range and playback flickers.

        Parameters
        ----------
        slider_width : float
            Width of the frame slider.
        id_suffix : str
            Appended to the imgui ids, for two players in one window.

        Examples
        --------
        >>> import numpy as np
        >>> from imgui_debugger import MoviePlayer
        >>> MoviePlayer(np.zeros((4, 2, 2))).draw()    # doctest: +SKIP
        False
        """
        if self._movie is None:
            return False
        changed = False
        label = "pause" if self._playing else "play"
        if imgui.button(f"{label}##movie{id_suffix}"):
            self._playing = not self._playing
            self._clock = (time.perf_counter(), float(self._t))
        imgui.same_line(0, 8)
        imgui.set_next_item_width(slider_width)
        slid, t = imgui.slider_int(
            f"##movie-frame{id_suffix}", self._t, 0, max(self.n_frames - 1, 0)
        )
        if slid:
            self._t = t
            self._clock = (time.perf_counter(), float(t))
            changed = True
        imgui.same_line(0, 4)
        imgui.text(f"{self._t}")
        imgui.same_line(0, 12)
        imgui.set_next_item_width(60)
        _, self._fps = imgui.drag_float(
            f"fps##movie{id_suffix}", self._fps, 1.0, 1.0, 240.0, "%.0f"
        )
        if self._playing and self._clock is not None:
            t0, f0 = self._clock
            new_t = int(f0 + (time.perf_counter() - t0) * self._fps) % max(
                self.n_frames, 1
            )
            if new_t != self._t:
                self._t = new_t
                changed = True
        return changed
