"""Turns per-frame fingertip positions into blade segments (only fast motion cuts)."""
import math

from .effects import Blade


class _Track:
    def __init__(self, tid, pos, t):
        self.id, self.pos, self.t = tid, pos, t
        self.blade = Blade()
        self.blade.add(pos[0], pos[1], t)


class SwipeDetector:
    def __init__(self, W, H, smooth=0.65, min_speed=0.4, match_dist=0.75, drop_after=0.3):
        """
        smooth     - 0..1, visual smoothing parameter
        min_speed  - minimum fingertip speed in screen-widths per second for a motion to count as a cut (default 0.4)
        match_dist - max jump (fraction of width) to still treat a point as the same hand (default 0.75)
        drop_after - seconds to keep a track alive if no point is detected (handles momentary blurs)
        """
        self.W, self.H = W, H
        self.smooth = smooth
        self.min_speed_px = min_speed * W
        self.match_dist = match_dist
        self.drop_after = drop_after
        self.tracks = []
        self.dying = []
        self._next_id = 0

    @property
    def blades(self):
        return [tr.blade for tr in self.tracks] + self.dying

    def update(self, points, t):
        """points: list of (x, y) pixels. Returns list of ((x0,y0),(x1,y1)) cutting segments."""
        segments = []
        free = list(self.tracks)
        matched = []
        match_px = self.match_dist * self.W

        for (px, py) in points:
            best, best_d = None, match_px
            for tr in free:
                d = math.hypot(px - tr.pos[0], py - tr.pos[1])
                if d < best_d:
                    best, best_d = tr, d
            if best is None:
                tr = _Track(self._next_id, (px, py), t)
                self._next_id += 1
                matched.append(tr)
                continue

            free.remove(best)
            old = best.pos
            dt = max(t - best.t, 1e-3)
            dist = math.hypot(px - old[0], py - old[1])
            speed = dist / dt

            # Fast motion counts as a cut - use full physical segment from previous to current position
            if speed >= self.min_speed_px:
                segments.append((old, (px, py)))

            # If frames were dropped during a fast swipe, interpolate midpoint so blade trail remains smooth
            if dt > 0.05:
                best.blade.add((old[0] + px) * 0.5, (old[1] + py) * 0.5, t - dt * 0.5)

            best.blade.add(px, py, t)
            best.pos, best.t = (px, py), t
            matched.append(best)

        for tr in free:                                  # hands that vanished this frame
            if t - tr.t <= self.drop_after:
                matched.append(tr)
            else:
                self.dying.append(tr.blade)
        self.tracks = matched
        self.dying = [b for b in self.dying if b.alive(t)]
        return segments
