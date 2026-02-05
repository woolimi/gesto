"""
YouTube 모드 전용 감지.
app/models/의 lstm_legacy.tflite 사용. 공통 LSTM 4종 제스처 모두 사용.
- Swipe_Left → 10초 뒤로, Swipe_Right → 10초 앞으로
- Pinch_In → 음소거, Pinch_Out → 재생/정지
"""

from typing import Callable, Optional

import config
from app.recognition.lstm_gesture_base import LstmGestureBase


class YouTubeDetector:
    """YouTube 모드: 공통 LSTM으로 4종 제스처 사용 — 10초 앞/뒤, 재생·정지, 음소거."""

    def __init__(self, get_confidence_threshold: Optional[Callable[[], float]] = None):
        self._base = LstmGestureBase(
            get_confidence_threshold=get_confidence_threshold,
            cooldown_sec=config.YOUTUBE_COOLDOWN_SEC,
        )

    def process(self, frame_bgr) -> tuple[Optional[str], float]:
        """한 프레임 처리. Pinch_In / Pinch_Out / Swipe_Left / Swipe_Right 중 하나 또는 (None, 0.0)."""
        return self._base.process(frame_bgr)

    @property
    def cooldown_until(self) -> float:
        """쿨다운 종료 시각 (time.monotonic()). UI와 동기화용."""
        return self._base.cooldown_until if self._base is not None else 0.0

    def close(self) -> None:
        if self._base is not None:
            self._base.close()
            self._base = None
