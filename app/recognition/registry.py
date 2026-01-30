"""모드별 감지기 등록 — get_mode_detector."""

from app.recognition.ppt import PPTDetector
from app.recognition.youtube import YouTubeDetector
from app.recognition.game import GameDetector


def get_mode_detector(mode: str):
    """모드 문자열에 해당하는 감지기 인스턴스 반환."""
    mode_upper = (mode or "").upper()
    if mode_upper == "PPT":
        return PPTDetector()
    if mode_upper == "YOUTUBE":
        return YouTubeDetector()
    if mode_upper == "GAME":
        return GameDetector()
    return PPTDetector()  # 기본
