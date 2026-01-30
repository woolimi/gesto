"""
웹캠 캡처 — QThread에서 OpenCV로 프레임 읽기, 시그널로 전달.
"""

import cv2
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage

import config


class CameraWorker(QThread):
    """OpenCV VideoCapture를 QThread에서 실행하고, 프레임을 QImage로 emit."""

    frame_ready = pyqtSignal(object)  # QImage
    frame_bgr_ready = pyqtSignal(object)  # numpy (BGR) — 인식 파이프라인용
    error_occurred = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._cap = None

    def run(self):
        self._running = True
        self._cap = cv2.VideoCapture(config.CAMERA_INDEX)
        if not self._cap.isOpened():
            self.error_occurred.emit("웹캠을 열 수 없습니다.")
            self._running = False
            return
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
        self._cap.set(cv2.CAP_PROP_FPS, config.CAMERA_FPS)

        while self._running and self._cap.isOpened():
            ret, frame = self._cap.read()
            if not ret:
                continue
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_BGR888)
            self.frame_ready.emit(qt_image.copy())
            self.frame_bgr_ready.emit(frame.copy())
        self._release()

    def _release(self):
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def stop(self):
        self._running = False

    def __del__(self):
        self._running = False
        self._release()
