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

    gesture_detected = pyqtSignal(str, float, float)  # (gesture_name, confidence, cooldown_until_monotonic)
    # GESTURE_DEBUG 시 제스처별 확률·threshold 표시용 (매 프레임 LSTM 추론 후 emit)
    gesture_debug_updated = pyqtSignal(dict, float)  # (probs, threshold)

    def __init__(
        self,
        get_current_mode: Callable[[], str],
        get_sensitivity: Optional[Callable[[], int]] = None,
        parent=None,
    ):
        """
        Args:
            get_current_mode: 현재 모드(PPT/YOUTUBE/GAME)를 반환하는 콜백.
            get_sensitivity: UI 감도 0~100 반환 콜백. 있으면 LSTM 계열에 실시간 반영.
        """
        super().__init__(parent)
        self._get_current_mode = get_current_mode
        self._get_sensitivity = get_sensitivity
        # 최신 1프레임만 유지: 큐가 쌓이면 지연된 동작 발생 → maxsize=1, Full 시 구식 프레임 폐기
        self._frame_queue = queue.Queue(maxsize=1)
        self._running = True
        self._detector = None  # 모드별 감지기 (모드 변경 시 교체)

    def enqueue_frame(self, frame_bgr) -> None:
        """메인/카메라 스레드에서 호출. 모션 감지 중일 때만 호출. 최신 프레임만 유지(구식 폐기)."""
        try:
            self._frame_queue.put_nowait(frame_bgr)
        except queue.Full:
            try:
                self._frame_queue.get_nowait()
            except queue.Empty:
                pass
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
                get_threshold = None
                if self._get_sensitivity is not None:
                    get_threshold = lambda: config.sensitivity_to_confidence_threshold(
                        self._get_sensitivity()
                    )
                self._detector = get_mode_detector(mode, get_confidence_threshold=get_threshold)
                last_mode = mode
            if self._detector is not None:
                result = self._detector.process(frame)
                if isinstance(result, tuple):
                    gesture, confidence = result
                else:
                    gesture, confidence = result, 0.0 # Safety for old detectors
                
                # GAME 모드: 빈 제스처도 emit하여 방향 해제(release) 가능하도록 함
                # 쿨다운 중에도 cooldown_until 전달 → UI에서 감지된 제스처 유지 후 종료 시 실시간으로 전환
                cooldown_until = getattr(self._detector, "cooldown_until", 0.0)
                self.gesture_detected.emit(gesture or "", confidence, cooldown_until)
                # 디버그: 매 프레임 확률 전달. UI에서 쿨다운 중일 때만 갱신 생략해 제스처와 함께 유지
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
            self._frame_queue.put_nowait(None)
        except queue.Full:
            pass
