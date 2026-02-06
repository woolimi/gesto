"""
공통 트리거 워커 — 모션 감지 시작/종료만 판별 (QThread).
"""

import queue
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage

from app.recognition.trigger import PostureTriggerDetector, TriggerResult


class TriggerWorker(QThread):
    """공통: 프레임에서 양손 펴기/주먹만 판별. trigger_start / trigger_stop 시그널."""

    trigger_start = pyqtSignal()
    trigger_stop = pyqtSignal()
    trigger_aot_on = pyqtSignal()
    trigger_aot_off = pyqtSignal()
    frame_annotated = pyqtSignal(object)  # QImage — 손 랜드마크가 그려진 프레임

    def __init__(self, parent=None):
        super().__init__(parent)
        self._detector = PostureTriggerDetector()
        self._frame_queue = queue.Queue(maxsize=2)
        self._running = True
        self._motion_active = False  # 모션 인식 중이면 True (종료 제스처만 판단)
        self._current_mode = "GAME"
        self._aot_active = False

    def enqueue_frame(self, frame_bgr):
        """메인/카메라 스레드에서 호출. 프레임을 큐에 넣음."""
        try:
            self._frame_queue.put_nowait(frame_bgr)
        except queue.Full:
            pass

    def set_motion_active(self, active: bool):
        """버튼 등으로 감지 상태가 바뀔 때 호출. 랜드마크 색(파랑/회색) 동기화용."""
        self._motion_active = active

    def set_current_mode(self, mode: str):
        """현재 앱의 모드를 동기화. PPT 모드에서만 AOT 제스처 허용 위함."""
        self._current_mode = mode

    def run(self):
        while self._running:
            try:
                frame = self._frame_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if frame is None:
                break
            result, annotated = self._detector.process_annotated(frame, motion_active=self._motion_active)
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
            h, w, ch = annotated.shape
            bytes_per_line = ch * w
            qimage = QImage(annotated.data, w, h, bytes_per_line, QImage.Format.Format_BGR888)
            self.frame_annotated.emit(qimage.copy())
        self._detector.close()

    def stop(self):
        self._running = False
        try:
            self._frame_queue.put_nowait(None)
        except queue.Full:
            pass
