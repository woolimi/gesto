"""
모드별 감지 워커 — 모션 감지가 시작된 뒤, 현재 모드에 해당하는 제스처/자세만 감지.

이 워커가 전용 QThread에서 동작하므로, Game 모드 포함 모든 모드가 메인 스레드와
분리된 스레드에서 실행된다. Game 전용 별도 스레드는 필요 없다.
"""

import queue
from typing import Callable, Optional

from PyQt6.QtCore import QThread, pyqtSignal

import config
from app.recognition.registry import get_mode_detector


class ModeDetectionWorker(QThread):
    """모션 감지 중일 때만 프레임을 받아, 현재 모드 감지기로 제스처/자세 판별. gesture_detected 시그널."""

    gesture_detected = pyqtSignal(str, float, float)
    gesture_debug_updated = pyqtSignal(dict, float)

    def __init__(
        self,
        get_current_mode: Callable[[], str],
        get_sensitivity: Optional[Callable[[], int]] = None,
        parent=None,
    ):
        super().__init__(parent)
        self._get_current_mode = get_current_mode
        self._get_sensitivity = get_sensitivity
        self._landmarks_queue = queue.Queue(maxsize=1)
        self._running = True
        self._detector = None

    def enqueue_landmarks(self, landmarks, handedness) -> None:
        """카메라 스레드에서 호출. 모션 감지 중일 때만 호출. 최신 랜드마크만 유지."""
        try:
            self._landmarks_queue.put_nowait((landmarks, handedness))
        except queue.Full:
            try:
                self._landmarks_queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self._landmarks_queue.put_nowait((landmarks, handedness))
            except queue.Full:
                pass

    def run(self) -> None:
        last_mode: Optional[str] = None
        while self._running:
            try:
                item = self._landmarks_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if item is None:
                break
            
            landmarks, handedness = item
            mode = self._get_current_mode()
            if mode != last_mode:
                if self._detector is not None:
                    self._detector.close()
                get_threshold = None
                if self._get_sensitivity is not None:
                    get_threshold = lambda: config.sensitivity_to_confidence_threshold(
                        self._get_sensitivity()
                    )
                self._detector = get_mode_detector(mode, get_confidence_threshold=get_threshold)
                last_mode = mode
                
            if self._detector is not None:
                # process_landmarks 호출
                result = self._detector.process_landmarks(landmarks, handedness)
                if isinstance(result, tuple):
                    gesture, confidence = result
                else:
                    gesture, confidence = result, 0.0
                
                cooldown_until = getattr(self._detector, "cooldown_until", 0.0)
                self.gesture_detected.emit(gesture or "", confidence, cooldown_until)
                
                if config.GESTURE_DEBUG:
                    probs = getattr(self._detector, "last_probs", None) or {}
                    thr = (
                        config.sensitivity_to_confidence_threshold(self._get_sensitivity())
                        if self._get_sensitivity is not None
                        else 0.0
                    )
                    self.gesture_debug_updated.emit(probs, thr)
                    
        if self._detector is not None:
            self._detector.close()
            self._detector = None

    def stop(self) -> None:
        self._running = False
        try:
            self._landmarks_queue.put_nowait(None)
        except queue.Full:
            pass
