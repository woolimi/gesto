"""
웹캠 캡처 — QThread에서 OpenCV로 프레임 읽기, 시그널로 전달.
"""

import cv2
import mediapipe as mp
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage

import config
from app.recognition.trigger import HAND_CONNECTIONS, _draw_landmarks_on_frame


class CameraWorker(QThread):
    """OpenCV VideoCapture를 QThread에서 실행하고, 
    MediaPipe로 랜드마크를 추출하여 시그널로 전달.
    """
    # frame_updated: 이미 랜드마크가 그려진 QImage (UI용)
    frame_updated = pyqtSignal(object)
    # landmarks_updated: (multi_hand_landmarks, multi_handedness) - 인식 워커용
    landmarks_updated = pyqtSignal(object, object)
    error_occurred = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._cap = None
        self._motion_active = False # 트리거 상태 (랜드마크 색상 결정용)

        # MediaPipe Hands 초기화
        self._mp_hands = mp.solutions.hands
        self._hands = self._mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7,
        )

    def set_motion_active(self, active: bool):
        self._motion_active = active

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
            frame = cv2.flip(frame, 1)  # 좌우 반전

            # MediaPipe 처리
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self._hands.process(rgb)

            # 1. landmarks_updated 시그널 (인식 워커용)
            # results.multi_hand_landmarks, results.multi_handedness 전달
            self.landmarks_updated.emit(results.multi_hand_landmarks, results.multi_handedness)

            # 2. 랜드마크 시각화 (frame_updated용)
            annotated_frame = frame.copy()
            if results.multi_hand_landmarks:
                # trigger.py의 _draw_landmarks_on_frame 재사용
                # 래핑 객체 필요 없이 직접 그리는 로직으로 수정하거나, 
                # 래핑 객체(SimpleNamespace)를 만들어 전달
                from types import SimpleNamespace
                draw_res = SimpleNamespace()
                draw_res.hand_landmarks = [h.landmark for h in results.multi_hand_landmarks]
                _draw_landmarks_on_frame(annotated_frame, draw_res, self._motion_active)

            h, w, ch = annotated_frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(annotated_frame.data, w, h, bytes_per_line, QImage.Format.Format_BGR888)
            self.frame_updated.emit(qt_image.copy())

        self._release()

    def _release(self):
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        if self._hands is not None:
            self._hands.close()

    def stop(self):
        self._running = False

    def __del__(self):
        self._running = False
        self._release()
