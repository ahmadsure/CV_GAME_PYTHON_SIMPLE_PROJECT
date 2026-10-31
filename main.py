#!/usr/bin/env python3
"""Fruit Slash - slice fruit in mid-air with your finger.

    python main.py                 # webcam + hand tracking
    python main.py --mouse         # no camera needed, mouse is the blade
    python main.py --camera 1      # pick another camera

Keys:  q / Esc quit   h toggle hand skeleton   r restart   f fullscreen
"""
import argparse
import time

import cv2
import numpy as np

from game.engine import Game
from game.swipe import SwipeDetector

WIN = "Fruit Slash"


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--camera", type=int, default=0, help="camera index (default 0)")
    p.add_argument("--width", type=int, default=1280)
    p.add_argument("--height", type=int, default=720)
    p.add_argument("--mouse", action="store_true", help="play with the mouse instead of a camera")
    p.add_argument("--no-mirror", action="store_true", help="do not mirror the camera image")
    p.add_argument("--show-hands", action="store_true", help="draw the hand skeleton")
    p.add_argument("--min-speed", type=float, default=0.4,
                   help="swipe speed (screen widths/sec) needed to cut; lower = easier (default 0.4)")
    p.add_argument("--smooth", type=float, default=0.65,
                   help="fingertip smoothing 0-1; higher = snappier but jitterier (default 0.65)")
    p.add_argument("--no-sound", action="store_true", help="disable sound effects")
    p.add_argument("--fullscreen", action="store_true")
    p.add_argument("--seed", type=int, default=None)
    return p.parse_args()


def fake_background(W, H):
    y = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    top, bottom = np.array((60, 45, 30), np.float32), np.array((25, 20, 15), np.float32)
    return (top * (1 - y) + bottom * y).repeat(W, axis=1).astype(np.uint8)


def main():
    args = parse_args()

    cam = None
    if args.mouse:
        W, H = args.width, args.height
        background = fake_background(W, H)
    else:
        from game.camera import Camera
        cam = Camera(args.camera, args.width, args.height)
        W, H = cam.width, cam.height
        background = None

    cv2.namedWindow(WIN, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WIN, W, H)
    if args.fullscreen:
        cv2.setWindowProperty(WIN, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    if args.mouse:
        from game.tracker import MouseTracker
        tracker = MouseTracker(WIN)
    else:
        from game.tracker import HandTracker
        tracker = HandTracker()

    from game.sound import SoundBank
    sound = SoundBank(enabled=not args.no_sound)
    game = Game(W, H, seed=args.seed)
    swipe = SwipeDetector(W, H, smooth=args.smooth, min_speed=args.min_speed)
    show_hands, last_seq, frame = args.show_hands, -1, background
    last_t, fps = time.perf_counter(), 0.0
    fullscreen = args.fullscreen

    while True:
        now = time.perf_counter()
        dt = min(now - last_t, 0.05)
        last_t = now
        fps = 0.9 * fps + 0.1 / max(dt, 1e-4)

        segments = []
        if cam is not None:
            seq, raw = cam.read()
            if seq != last_seq:                       # new camera frame -> run the tracker once
                last_seq = seq
                frame = raw if args.no_mirror else cv2.flip(raw, 1)
                segments = swipe.update(tracker.process(frame), now)
        else:
            segments = swipe.update(tracker.process(frame), now)

        game.update(dt, segments)
        for ev in game.events:
            sound.play(ev)
        game.events.clear()

        canvas = cv2.convertScaleAbs(frame, alpha=0.7)    # dim the camera so the fruit pops
        if show_hands:
            tracker.draw_debug(canvas)
        game.draw(canvas)
        for blade in swipe.blades:
            blade.draw(canvas, now, game.k)
        cv2.putText(canvas, f"{fps:4.0f} fps", (W - 120, H - 15), cv2.FONT_HERSHEY_PLAIN, 1.2, (200, 200, 200), 1, cv2.LINE_AA)
        cv2.imshow(WIN, canvas)

        key = cv2.waitKey(1) & 0xFF
        if key in (27, ord("q")) or cv2.getWindowProperty(WIN, cv2.WND_PROP_VISIBLE) < 1:
            break
        elif key == ord("h"):
            show_hands = not show_hands
        elif key == ord("r"):
            game.reset()
        elif key == ord("f"):
            fullscreen = not fullscreen
            cv2.setWindowProperty(WIN, cv2.WND_PROP_FULLSCREEN,
                                  cv2.WINDOW_FULLSCREEN if fullscreen else cv2.WINDOW_NORMAL)

    if cam is not None:
        cam.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
