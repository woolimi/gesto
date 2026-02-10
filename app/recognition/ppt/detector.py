"""
PPT 모드 전용 감지.
app/models/의 lstm_legacy(tflite/h5) 사용. Swipe_Left/Right: 이전/다음 슬라이드. Pinch_Out: 발표 시작, Pinch_In: 발표 종료.
"""

from typing import Callable, Optional

import config
from app.recognition.lstm_gesture_base import LstmGestureBase


class PPTDetector:
    """PPT 모드: LSTM으로 Swipe + Pinch(전체화면/종료) 사용."""

    _ALLOWED = (
        "Swipe_Left",
        "Swipe_Right",
        "Pinch_Out_Left",
        "Pinch_Out_Right",
        "Pinch_In_Left",
        "Pinch_In_Right",
    )

    def __init__(self, get_confidence_threshold: Optional[Callable[[], float]] = None):
        self._base = LstmGestureBase(
            get_confidence_threshold=get_confidence_threshold,
            cooldown_sec=config.PPT_COOLDOWN_SEC,
        )

    def process_landmarks(self, multi_hand_landmarks, multi_handedness) -> tuple[Optional[str], float]:
        """LSTM 베이스와 동일하게 (gesture, confidence) 반환. Swipe·Pinch 인정."""
        result = self._base.process_landmarks(multi_hand_landmarks, multi_handedness)
        if isinstance(result, tuple):
            gesture, confidence = result
        else:
            gesture, confidence = result, 0.0
        if gesture in self._ALLOWED:
            return (gesture, confidence)
        return (None, 0.0)

    def process(self, frame_bgr) -> tuple[Optional[str], float]:
        return (None, 0.0)

    @property
    def cooldown_until(self) -> float:
        """쿨다운 종료 시각 (time.monotonic()). UI와 동기화용."""
        return self._base.cooldown_until if self._base is not None else 0.0

    @property
    def last_probs(self) -> dict:
        """마지막 인식 시 모든 클래스별 확률. UI/디버그 표시용 (YouTubeDetector와 동일)."""
        return getattr(self._base, "last_probs", {}) if self._base else {}

    @property
    def last_11ch_means(self):
        """GESTURE_DEBUG용. 11채널 평균."""
        return getattr(self._base, "last_11ch_means", None) if self._base else None

    @property
    def last_fist_debug(self):
        """GESTURE_DEBUG용. is_fist 손가락별 판정."""
        return getattr(self._base, "last_fist_debug", None) if self._base else None

    def close(self) -> None:
        if self._base is not None:
            self._base.close()
            self._base = None
