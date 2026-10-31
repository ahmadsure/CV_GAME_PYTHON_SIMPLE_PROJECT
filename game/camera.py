"""Threaded webcam capture so a slow read never stalls rendering."""
import threading
import time

import cv2


class Camera:
    def __init__(self, index=0, width=1280, height=720):
        self.cap = cv2.VideoCapture(index)
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open camera {index}. Try --camera 1, or play with --mouse.")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self._lock = threading.Lock()
        self._frame, self._seq, self._running = None, 0, True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        t0 = time.time()
        while self._frame is None and time.time() - t0 < 5:
            time.sleep(0.01)
        if self._frame is None:
            raise RuntimeError("Camera opened but gave no frames.")
        self.height, self.width = self._frame.shape[:2]

    def _loop(self):
        while self._running:
            ok, frame = self.cap.read()
            if not ok:
                time.sleep(0.01)
                continue
            with self._lock:
                self._frame, self._seq = frame, self._seq + 1

    def read(self):
        """Returns (sequence_number, latest_frame). The number changes with every new frame."""
        with self._lock:
            return self._seq, self._frame

    def release(self):
        self._running = False
        self._thread.join(timeout=1)
        self.cap.release()
