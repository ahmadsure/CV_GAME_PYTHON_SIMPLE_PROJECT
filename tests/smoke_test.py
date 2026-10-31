"""Headless smoke test: a bot "swipes" at fruit through the real SwipeDetector -> Game pipeline
and writes preview PNGs. No camera or display needed.

    python tests/smoke_test.py [output_dir]
"""
import math
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import cv2
import numpy as np

from game.assets import SpriteSet, blit_rgba, cut_sprite, PAD
from game.engine import Game
from game.swipe import SwipeDetector

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "tests", "out")
os.makedirs(OUT, exist_ok=True)
W, H, FPS = 1280, 720, 30


def background():
    y = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    top, bottom = np.array((95, 120, 80), np.float32), np.array((40, 55, 35), np.float32)
    img = (top * (1 - y) + bottom * y).repeat(W, axis=1)
    img += np.random.RandomState(0).normal(0, 4, img.shape)
    return np.clip(img, 0, 255).astype(np.uint8)


def sprite_sheet():
    sp = SpriteSet()
    items = list(sp.fruits.values()) + [sp.bomb]
    sheet = np.full((2 * 190, 190 * len(items), 3), 70, np.uint8)
    for i, s in enumerate(items):
        blit_rgba(sheet, s.img, 95 + i * 190, 95, 0, 0.75)
        if not s.bomb:
            if s.cut_img is not None:
                a, b = cut_sprite(s.cut_img, 35)
            else:
                a, b = cut_sprite(s.img, 35, s.flesh, s.band)
            blit_rgba(sheet, a, 85 + i * 190, 285, 0, 0.75)
            blit_rgba(sheet, b, 105 + i * 190, 295, 0, 0.75)
    cv2.imwrite(os.path.join(OUT, "sprites.png"), sheet)


def render(game, swipe, bg, t):
    frame = cv2.convertScaleAbs(bg, alpha=0.7)
    game.draw(frame)
    for b in swipe.blades:
        b.draw(frame, t, game.k)
    return frame


def run_bot(seconds=40):
    game, swipe, bg = Game(W, H, seed=7), SwipeDetector(W, H), background()
    rng = random.Random(1)
    dt, t, plan = 1.0 / FPS, 0.0, []
    seen_states, saved_play, saved_after = set(), False, None
    cut_frames = 0
    for step in range(int(seconds * FPS)):
        t += dt
        seen_states.add(game.state)
        if not plan:
            targets = [f for f in game.fruits if f.button or (not f.bomb and 0.12 * H < f.y < 0.85 * H)]
            if targets:
                f = min(targets, key=lambda q: abs(q.y - 0.4 * H))
                cx, cy = f.x + f.vx * 0.1, f.y + f.vy * 0.1
                s = rng.choice((-1, 1))
                plan = [(cx - s * 250 + s * 100 * i, cy + 40 - 16 * i) for i in range(6)]
        pts = [plan.pop(0)] if plan else []
        segs = swipe.update(pts, t)
        cut_frames += bool(segs)
        game.update(dt, segs)
        if step == 10:
            cv2.imwrite(os.path.join(OUT, "menu.png"), render(game, swipe, bg, t))
        if not saved_play and game.slices >= 5 and game.state == "playing":
            saved_play, saved_after = True, step + 2
        if saved_after == step:
            cv2.imwrite(os.path.join(OUT, "playing.png"), render(game, swipe, bg, t))
    cv2.imwrite(os.path.join(OUT, "final.png"), render(game, swipe, bg, t))
    return game, seen_states, cut_frames


if __name__ == "__main__":
    sprite_sheet()
    game, states, cut_frames = run_bot()
    print(f"states seen: {sorted(states)}  slices: {game.slices}  score: {game.score}  best: {game.best}  lives: {game.lives}")
    print(f"frames with a cutting segment: {cut_frames}")
    assert "menu" in states and "playing" in states, "game never left the menu"
    assert game.slices >= 10, "bot barely sliced anything"
    print(f"OK - previews written to {OUT}")
