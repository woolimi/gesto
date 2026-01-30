"""
공통 트리거 워커 — 모션 감지 시작/종료만 판별 (QThread).
"""

import queue
from PyQt6.QtCore import QThread, pyqtSignal

from app.recognition.trigger import PostureTriggerDetector, TriggerResult


class TriggerWorker(QThread):
    """공통: 프레임에서 양손 펴기/주먹만 판별. trigger_start / trigger_stop 시그널."""

    trigger_start = pyqtSignal()
    trigger_stop = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._detector = PostureTriggerDetector()
        self._frame_queue = queue.Queue(maxsize=2)
        self._running = True

    def enqueue_frame(self, frame_bgr):
        """메인/카메라 스레드에서 호출. 프레임을 큐에 넣음."""
        try:
            self._frame_queue.put_nowait(frame_bgr)
        except queue.Full:
            pass

    def run(self):
        while self._running:
            try:
                frame = self._frame_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if frame is None:
                break
            result = self._detector.process(frame)
            if result == TriggerResult.START:
                self.trigger_start.emit()
            elif result == TriggerResult.STOP:
                self.trigger_stop.emit()
        self._detector.close()

    def stop(self):
        self._running = False
        try:
            self._frame_queue.put_nowait(None)
        except queue.Full:
            pass
