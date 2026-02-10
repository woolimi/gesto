"""
공통 트리거 워커 — 모션 감지 시작/종료만 판별 (QThread).
"""

import queue
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage

from app.recognition.trigger import PostureTriggerDetector, TriggerResult


class TriggerWorker(QThread):
    """공통: 전달받은 landmarks에서 양손 펴기/주먹만 판별. trigger_start / trigger_stop 시그널."""

    trigger_start = pyqtSignal()
    trigger_stop = pyqtSignal()
    trigger_aot_on = pyqtSignal()
    trigger_aot_off = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._detector = PostureTriggerDetector()
        self._landmarks_queue = queue.Queue(maxsize=10)
        self._running = True
        self._motion_active = False
        self._current_mode = "GAME"
        self._aot_active = False

    def enqueue_landmarks(self, landmarks, handedness):
        """카메라 스레드에서 호출. 추출된 랜드마크를 큐에 넣음."""
        try:
            self._landmarks_queue.put_nowait((landmarks, handedness))
        except queue.Full:
            pass

    def set_motion_active(self, active: bool):
        self._motion_active = active

    def set_current_mode(self, mode: str):
        self._current_mode = mode

    def run(self):
        while self._running:
            try:
                item = self._landmarks_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if item is None:
                break
            
            landmarks, handedness = item
            result = self._detector.process_landmarks(landmarks, motion_active=self._motion_active)
            
            if result == TriggerResult.START:
                self.trigger_start.emit()
                self._motion_active = True
            elif result == TriggerResult.STOP:
                self.trigger_stop.emit()
                self._motion_active = False
            elif result == TriggerResult.ALWAYS_ON_TOP_ON:
                if self._current_mode == "PPT" and not self._aot_active:
                    self.trigger_aot_on.emit()
                    self._aot_active = True
            elif result == TriggerResult.ALWAYS_ON_TOP_OFF:
                if self._current_mode == "PPT" and self._aot_active:
                    self.trigger_aot_off.emit()
                    self._aot_active = False

    def stop(self):
        self._running = False
        try:
            self._landmarks_queue.put_nowait(None)
        except queue.Full:
            pass
