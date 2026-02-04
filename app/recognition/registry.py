"""모드별 감지기 등록 — get_mode_detector."""

from typing import Callable, Optional

from app.recognition.ppt import PPTDetector
from app.recognition.youtube import YouTubeDetector
from app.recognition.game import GameDetector


def get_mode_detector(
    mode: str,
    get_confidence_threshold: Optional[Callable[[], float]] = None,
):
    """모드 문자열에 해당하는 감지기 인스턴스 반환.
    get_confidence_threshold: LSTM 계열(PPT 등)에서 감도 실시간 반영용. 호출 시 0.3~0.9 반환.
    """
    mode_upper = (mode or "").upper()
    if mode_upper == "PPT":
        return PPTDetector(get_confidence_threshold=get_confidence_threshold)
    if mode_upper == "YOUTUBE":
        return YouTubeDetector(get_confidence_threshold=get_confidence_threshold)
    if mode_upper == "GAME":
        return GameDetector()
    return PPTDetector(get_confidence_threshold=get_confidence_threshold)
