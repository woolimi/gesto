"""
모드별 감지 워커 — 모션 감지가 시작된 뒤, 현재 모드에 해당하는 제스처/자세만 감지.
"""

import queue
from typing import Callable, Optional

from PyQt6.QtCore import QThread, pyqtSignal

from app.recognition.registry import get_mode_detector


class ModeDetectionWorker(QThread):
    """모션 감지 중일 때만 프레임을 받아, 현재 모드 감지기로 제스처/자세 판별. gesture_detected 시그널."""

    gesture_detected = pyqtSignal(str)

    def __init__(self, get_current_mode: Callable[[], str], parent=None):
        """
        Args:
            get_current_mode: 현재 모드(PPT/YOUTUBE/GAME)를 반환하는 콜백. 메인에서 mode_controller.get_mode 등.
        """
        super().__init__(parent)
        self._get_current_mode = get_current_mode
        self._frame_queue = queue.Queue(maxsize=2)
        self._running = True
        self._detector = None  # 모드별 감지기 (모드 변경 시 교체)

    def enqueue_frame(self, frame_bgr) -> None:
        """메인/카메라 스레드에서 호출. 모션 감지 중일 때만 호출할 것."""
        try:
            self._frame_queue.put_nowait(frame_bgr)
        except queue.Full:
            pass

    def run(self) -> None:
        last_mode: Optional[str] = None
        while self._running:
            try:
                frame = self._frame_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if frame is None:
                break
            mode = self._get_current_mode()
            if mode != last_mode:
                if self._detector is not None:
                    self._detector.close()
                self._detector = get_mode_detector(mode)
                last_mode = mode
            if self._detector is not None:
                gesture = self._detector.process(frame)
                if gesture:
                    self.gesture_detected.emit(gesture)
        if self._detector is not None:
            self._detector.close()
            self._detector = None

    def stop(self) -> None:
        self._running = False
        try:
            self._frame_queue.put_nowait(None)
        except queue.Full:
            pass
