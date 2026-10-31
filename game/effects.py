"""Visual effects: juice particles, splats, score popups, screen flash, blade trail, text helpers."""
import math
from collections import deque

import cv2
import numpy as np

FONT = cv2.FONT_HERSHEY_DUPLEX


def put_text(img, text, x, y, scale=1.0, color=(255, 255, 255), thick=2, center=True):
    """Outlined text; (x, y) is the vertical centre of the text."""
    (tw, th), _ = cv2.getTextSize(text, FONT, scale, thick)
    org = (int(x - tw / 2) if center else int(x), int(y + th / 2))
    cv2.putText(img, text, org, FONT, scale, (0, 0, 0), thick + 4, cv2.LINE_AA)
    cv2.putText(img, text, org, FONT, scale, color, thick, cv2.LINE_AA)


def draw_heart(img, cx, cy, s, color, filled=True):
    t = np.linspace(0, 2 * math.pi, 48)
    xs = 16 * np.sin(t) ** 3
    ys = -(13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t))
    pts = np.stack([cx + xs * s / 17.0, cy + ys * s / 17.0], axis=1).astype(np.int32)
    if filled:
        cv2.fillPoly(img, [pts], color, cv2.LINE_AA)
    cv2.polylines(img, [pts], True, (0, 0, 0) if filled else color, 2, cv2.LINE_AA)


def _blend_blobs(frame, x, y, blobs, color, alpha):
    ext = int(max(max(abs(dx), abs(dy)) + r for dx, dy, r in blobs)) + 3
    fh, fw = frame.shape[:2]
    x0, x1 = max(0, int(x) - ext), min(fw, int(x) + ext)
    y0, y1 = max(0, int(y) - ext), min(fh, int(y) + ext)
    if x1 <= x0 or y1 <= y0:
        return
    roi = frame[y0:y1, x0:x1]
    over = roi.copy()
    for dx, dy, r in blobs:
        cv2.circle(over, (int(x + dx) - x0, int(y + dy) - y0), int(r), color, -1, cv2.LINE_AA)
    cv2.addWeighted(over, alpha, roi, 1.0 - alpha, 0, roi)


class Effects:
    def __init__(self, W, H, rng, k=1.0):
        self.W, self.H, self.rng, self.k = W, H, rng, k
        self.particles = []   # [x, y, vx, vy, life, max_life, radius, colour]
        self.splats = []      # dict(x, y, blobs, colour, life, max)
        self.popups = []      # dict(text, x, y, colour, life, max, scale)
        self.slashes = []     # dict(x, y, angle, length, life, max)
        self.flash_a = 0.0
        self.flash_c = (255, 255, 255)

    # -- spawning -----------------------------------------------------------
    def slash(self, x, y, angle_deg, length):
        """Bright streak along the cut line, fading in ~0.18s - the 'knife' moment."""
        self.slashes.append(dict(x=x, y=y, angle=math.radians(angle_deg), length=length, life=0.18, max=0.18))

    def juice(self, x, y, color, angle_deg, n=34):
        a = math.radians(angle_deg)
        for _ in range(n):
            base = a + self.rng.choice((math.pi / 2, -math.pi / 2))     # spray out of the cut
            ang = base + self.rng.gauss(0, 0.85)
            sp = self.rng.uniform(150, 720) * self.k
            life = self.rng.uniform(0.35, 0.8)
            c = tuple(int(min(255, max(0, v * self.rng.uniform(0.8, 1.2)))) for v in color)
            self.particles.append([x, y, math.cos(ang) * sp, math.sin(ang) * sp,
                                   life, life, self.rng.uniform(2.5, 7.0), c])

    def splat(self, x, y, color):
        k = self.k
        blobs = [(0, 0, self.rng.uniform(26, 38) * k)]
        for _ in range(7):
            ang = self.rng.uniform(0, 2 * math.pi)
            dist = self.rng.uniform(25, 60) * k
            blobs.append((math.cos(ang) * dist, math.sin(ang) * dist, self.rng.uniform(6, 17) * k))
        self.splats.append(dict(x=x, y=y, blobs=blobs, colour=color, life=1.6, max=1.6))
        del self.splats[:-14]

    def popup(self, text, x, y, color=(255, 255, 255), scale=1.0, life=0.9):
        self.popups.append(dict(text=text, x=x, y=y, colour=color, life=life, max=life, scale=scale))

    def flash(self, color=(255, 255, 255), strength=1.0):
        self.flash_a, self.flash_c = strength, color

    # -- simulation ---------------------------------------------------------
    def update(self, dt):
        g = 1400.0 * self.k
        for p in self.particles:
            p[3] += g * dt
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[4] -= dt
        self.particles = [p for p in self.particles if p[4] > 0 and p[1] < self.H + 50]
        for s in self.splats:
            s["life"] -= dt
        self.splats = [s for s in self.splats if s["life"] > 0]
        for s in self.slashes:
            s["life"] -= dt
        self.slashes = [s for s in self.slashes if s["life"] > 0]
        for p in self.popups:
            p["life"] -= dt
            p["y"] -= 70 * self.k * dt
        self.popups = [p for p in self.popups if p["life"] > 0]
        self.flash_a = max(0.0, self.flash_a - dt * 1.8)

    # -- drawing ------------------------------------------------------------
    def draw_under(self, frame):
        for s in self.splats:
            _blend_blobs(frame, s["x"], s["y"], s["blobs"], s["colour"], 0.5 * min(1.0, s["life"] / s["max"]))

    def draw_over(self, frame):
        for s in self.slashes:
            f = s["life"] / s["max"]
            dx, dy = math.cos(s["angle"]) * s["length"] * (1.3 - 0.3 * f), math.sin(s["angle"]) * s["length"] * (1.3 - 0.3 * f)
            p0, p1 = (int(s["x"] - dx), int(s["y"] - dy)), (int(s["x"] + dx), int(s["y"] + dy))
            glow = frame.copy()
            cv2.line(glow, p0, p1, (255, 240, 200), max(2, int(24 * f * self.k)), cv2.LINE_AA)
            cv2.addWeighted(glow, 0.55 * f, frame, 1.0 - 0.55 * f, 0, frame)
            cv2.line(frame, p0, p1, (255, 255, 255), max(1, int(7 * f * self.k)), cv2.LINE_AA)
        for x, y, _, _, life, mx, r, col in self.particles:
            cv2.circle(frame, (int(x), int(y)), max(1, int(r * (0.35 + 0.65 * life / mx) * self.k)), col, -1, cv2.LINE_AA)
        for p in self.popups:
            put_text(frame, p["text"], p["x"], p["y"], p["scale"] * self.k, p["colour"], 2)
        if self.flash_a > 0.01:
            solid = np.full_like(frame, self.flash_c)
            cv2.addWeighted(frame, 1.0 - self.flash_a, solid, self.flash_a, 0, frame)


class Blade:
    """Fading glowing trail behind one fingertip."""

    def __init__(self, life=0.25):
        self.life = life
        self.pts = deque()

    def add(self, x, y, t):
        self.pts.append((x, y, t))

    def prune(self, t):
        while self.pts and t - self.pts[0][2] > self.life:
            self.pts.popleft()

    def alive(self, t):
        return bool(self.pts) and t - self.pts[-1][2] <= self.life

    def draw(self, frame, t, k=1.0):
        self.prune(t)
        pts = list(self.pts)
        if len(pts) < 2:
            if pts:
                cv2.circle(frame, (int(pts[0][0]), int(pts[0][1])), int(6 * k), (255, 255, 255), -1, cv2.LINE_AA)
            return
        glow = frame.copy()
        for (x0, y0, t0), (x1, y1, _) in zip(pts[:-1], pts[1:]):
            f = max(0.0, 1.0 - (t - t0) / self.life)
            cv2.line(glow, (int(x0), int(y0)), (int(x1), int(y1)), (255, 210, 120), max(2, int(26 * f * k)), cv2.LINE_AA)
        cv2.addWeighted(glow, 0.5, frame, 0.5, 0, frame)
        for (x0, y0, t0), (x1, y1, _) in zip(pts[:-1], pts[1:]):
            f = max(0.0, 1.0 - (t - t0) / self.life)
            cv2.line(frame, (int(x0), int(y0)), (int(x1), int(y1)), (255, 255, 255), max(1, int(11 * f * k)), cv2.LINE_AA)
        cv2.circle(frame, (int(pts[-1][0]), int(pts[-1][1])), int(7 * k), (255, 255, 255), -1, cv2.LINE_AA)
