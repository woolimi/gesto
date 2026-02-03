"""
PPT 모드 전용 감지.
app/models/의 lstm_legacy(tflite/h5) 사용. Swipe_Left → 이전 슬라이드, Swipe_Right → 다음 슬라이드.
Pinch_In / Pinch_Out 은 무시.
"""

from typing import Callable, Optional

from app.recognition.lstm_gesture_base import LstmGestureBase


class PPTDetector:
    """PPT 모드: 공통 LSTM으로 Swipe만 사용 — 이전/다음 슬라이드."""

    _SWIPE_ONLY = ("Swipe_Left", "Swipe_Right")

    def __init__(self, get_confidence_threshold: Optional[Callable[[], float]] = None):
        self._base = LstmGestureBase(get_confidence_threshold=get_confidence_threshold)

    def process(self, frame_bgr) -> Optional[str]:
        gesture = self._base.process(frame_bgr)
        if gesture in self._SWIPE_ONLY:
            return gesture
        return None

    def close(self) -> None:
        if self._base is not None:
            self._base.close()
            self._base = None
