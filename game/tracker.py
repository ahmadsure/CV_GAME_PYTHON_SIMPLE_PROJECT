"""Hand tracking (MediaPipe) -> index-fingertip positions in pixel coordinates.

Works with both MediaPipe APIs:
  * legacy ``mp.solutions.hands``       (no model file needed)
  * new Tasks ``HandLandmarker``         (downloads hand_landmarker.task once)
"""
import os
import time
import urllib.request

import cv2

MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
             "hand_landmarker/float16/1/hand_landmarker.task")
MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "assets", "models", "hand_landmarker.task")
INDEX_TIP = 8
HAND_CONNECTIONS = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10),
                    (10, 11), (11, 12), (9, 13), (13, 14), (14, 15), (15, 16), (13, 17), (17, 18),
                    (18, 19), (19, 20), (0, 17)]


def _ensure_model():
    if not os.path.exists(MODEL_PATH):
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        print("[tracker] downloading hand_landmarker.task (one time, ~8 MB)...")
        try:
            urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        except Exception as e:
            if os.path.exists(MODEL_PATH):
                os.remove(MODEL_PATH)
            raise RuntimeError(
                f"Could not download the hand model ({e}).\n"
                f"Download it manually from:\n  {MODEL_URL}\n"
                f"and save it as:\n  {MODEL_PATH}") from e
    return MODEL_PATH


class HandTracker:
    def __init__(self, max_hands=2, detect_conf=0.35, track_conf=0.35, proc_width=640):
        import mediapipe as mp
        self.mp = mp
        self.proc_width = proc_width
        self.hands_px = []          # all 21 landmarks per hand, for the debug overlay
        self._last_ts_ms = 0
        self._legacy = hasattr(mp, "solutions") and hasattr(mp.solutions, "hands")
        if self._legacy:
            self._hands = mp.solutions.hands.Hands(
                static_image_mode=False, max_num_hands=max_hands, model_complexity=0,
                min_detection_confidence=detect_conf, min_tracking_confidence=track_conf)
        else:
            from mediapipe.tasks import python as mp_python
            from mediapipe.tasks.python import vision
            opts = vision.HandLandmarkerOptions(
                base_options=mp_python.BaseOptions(model_asset_path=_ensure_model()),
                running_mode=vision.RunningMode.VIDEO, num_hands=max_hands,
                min_hand_detection_confidence=detect_conf,
                min_hand_presence_confidence=detect_conf,
                min_tracking_confidence=track_conf)
            self._landmarker = vision.HandLandmarker.create_from_options(opts)

    def process(self, frame_bgr):
        """frame_bgr: the (already mirrored) frame shown to the player. Returns [(x, y), ...]."""
        h, w = frame_bgr.shape[:2]
        if self.proc_width and w > self.proc_width:
            target_h = int(h * self.proc_width / w)
            small = cv2.resize(frame_bgr, (self.proc_width, target_h))
        else:
            small = frame_bgr
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        if self._legacy:
            rgb.flags.writeable = False
            res = self._hands.process(rgb)
            hands = res.multi_hand_landmarks or []
            landmarks = [hl.landmark for hl in hands]
        else:
            img = self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=rgb)
            now_ms = int(time.monotonic() * 1000)
            if now_ms <= self._last_ts_ms:
                now_ms = self._last_ts_ms + 1
            self._last_ts_ms = now_ms
            res = self._landmarker.detect_for_video(img, now_ms)
            landmarks = res.hand_landmarks or []
        self.hands_px = [[(p.x * w, p.y * h) for p in lm] for lm in landmarks]
        return [pts[INDEX_TIP] for pts in self.hands_px]

    def draw_debug(self, frame):
        for pts in self.hands_px:
            for a, b in HAND_CONNECTIONS:
                cv2.line(frame, (int(pts[a][0]), int(pts[a][1])), (int(pts[b][0]), int(pts[b][1])),
                         (200, 200, 200), 2, cv2.LINE_AA)
            for x, y in pts:
                cv2.circle(frame, (int(x), int(y)), 4, (80, 200, 255), -1, cv2.LINE_AA)
            cv2.circle(frame, (int(pts[INDEX_TIP][0]), int(pts[INDEX_TIP][1])), 9, (0, 255, 0), 2, cv2.LINE_AA)


class MouseTracker:
    """Fallback so you can play / test without a camera: the mouse is the blade."""

    def __init__(self, window):
        self.pos = None
        self.hands_px = []
        cv2.setMouseCallback(window, self._cb)

    def _cb(self, event, x, y, flags, param):
        self.pos = (x, y)

    def process(self, frame_bgr):
        return [self.pos] if self.pos else []

    def draw_debug(self, frame):
        pass
