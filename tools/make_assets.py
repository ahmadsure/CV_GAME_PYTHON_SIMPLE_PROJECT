#!/usr/bin/env python3
"""Generate the asset pack into assets/ (PNG sprites + WAV sounds). Safe to re-run.

    python tools/make_assets.py
"""
import os
import sys
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import cv2
import numpy as np

from game import assets

SR = 22050


def save_sprites():
    fruits = os.path.join(ROOT, "assets", "fruits")
    cut = os.path.join(ROOT, "assets", "cut")
    os.makedirs(fruits, exist_ok=True)
    os.makedirs(cut, exist_ok=True)
    for name, build in assets.BUILDERS.items():
        cv2.imwrite(os.path.join(fruits, f"{name}.png"), build())
        cv2.imwrite(os.path.join(cut, f"{name}.png"), assets.INTERIORS[name]())
    cv2.imwrite(os.path.join(fruits, "bomb.png"), assets._bomb())
    print(f"sprites: {len(assets.BUILDERS)} fruits + {len(assets.BUILDERS)} cut faces + bomb")


# ---- sounds ----------------------------------------------------------------------
def _write(name, x):
    folder = os.path.join(ROOT, "assets", "sounds")
    os.makedirs(folder, exist_ok=True)
    x = np.clip(x / max(1e-6, np.abs(x).max()) * 0.8, -1, 1)
    with wave.open(os.path.join(folder, name + ".wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())


def _t(sec):
    return np.arange(int(SR * sec)) / SR


def save_sounds():
    rng = np.random.RandomState(0)
    # slice: bright noise swoosh + wet squish
    t = _t(0.22)
    swoosh = np.diff(rng.normal(0, 1, t.size), prepend=0) * np.exp(-t * 16) * np.clip(t * 250, 0, 1)
    squish = np.sin(2 * np.pi * (320 * t - 900 * t * t)) * np.exp(-t * 26)
    _write("slice", 0.6 * swoosh / np.abs(swoosh).max() + 0.4 * squish)
    # bomb: low rumble + noise burst
    t = _t(0.8)
    noise = np.convolve(rng.normal(0, 1, t.size), np.ones(40) / 40, "same")
    _write("bomb", noise * np.exp(-t * 5) + 0.9 * np.sin(2 * np.pi * 55 * t) * np.exp(-t * 4))
    # combo: rising arpeggio
    x = np.zeros(int(SR * 0.4))
    for i, f in enumerate((660, 880, 1100)):
        t = _t(0.16)
        n0 = int(SR * 0.09 * i)
        x[n0:n0 + t.size] += np.sin(2 * np.pi * f * t) * np.exp(-t * 18)
    _write("combo", x)
    # miss: short falling tone
    t = _t(0.3)
    _write("miss", np.sin(2 * np.pi * (300 * t - 400 * t * t)) * np.exp(-t * 7))
    # game over: four falling notes
    x = np.zeros(int(SR * 1.0))
    for i, f in enumerate((440, 392, 330, 262)):
        t = _t(0.3)
        n0 = int(SR * 0.22 * i)
        x[n0:n0 + t.size] += np.sin(2 * np.pi * f * t) * np.exp(-t * 6)
    _write("over", x)
    print("sounds: slice, bomb, combo, miss, over")


if __name__ == "__main__":
    save_sprites()
    save_sounds()
    print("assets written to", os.path.join(ROOT, "assets"))
