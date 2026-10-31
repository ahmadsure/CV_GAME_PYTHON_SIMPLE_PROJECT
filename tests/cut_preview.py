"""Render the slice animation as a contact sheet: one row per fruit, one column per moment in time.

    python tests/cut_preview.py [output.png]
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import cv2
import numpy as np

from game.assets import SpriteSet
from game.engine import Fruit, Game

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "tests", "out", "cut_animation.png")
W, H, FPS = 640, 480, 60
TIMES = [0.0, 0.08, 0.18, 0.32, 0.5, 0.75]          # seconds after the cut
NAMES = ["watermelon", "orange", "kiwi", "strawberry"]


def background():
    y = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    bg = (np.array((100, 125, 85), np.float32) * (1 - y) + np.array((45, 60, 40), np.float32) * y).repeat(W, axis=1)
    return bg.astype(np.uint8)


def row(sprites, name, bg):
    g = Game(W, H, sprites=sprites, seed=3)
    g.state, g.fruits, g.spawn_timer = "playing", [], 999
    g.fruits.append(Fruit(sprites.fruits[name], 320, 290, 0, -120 * g.k, angle=25, scale=g.k * 1.6))
    tiles, step = [], 0
    seg = [((170, 350), (470, 240))]                 # the finger swipe
    g.update(1 / FPS, seg)                           # the cut happens here
    for t in TIMES:
        while step / FPS < t:
            g.update(1 / FPS)
            step += 1
        frame = cv2.convertScaleAbs(bg, alpha=0.8)
        g.draw(frame)
        cv2.putText(frame, f"{name}  t={t:.2f}s", (10, 24), cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
        tiles.append(cv2.resize(frame, (W // 2, H // 2), interpolation=cv2.INTER_AREA))
    return np.hstack(tiles)


if __name__ == "__main__":
    sprites, bg = SpriteSet(), background()
    sheet = np.vstack([row(sprites, n, bg) for n in NAMES])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    cv2.imwrite(OUT, sheet)
    print("wrote", OUT, sheet.shape)
