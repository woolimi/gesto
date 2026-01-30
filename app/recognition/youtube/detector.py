"""
YouTube 모드 전용 감지.
(추후: 재생/정지, 10초 앞/뒤, 음소거, 전체화면 등)
"""

from typing import Optional


class YouTubeDetector:
    """YouTube 모드: 재생/정지, 빨리감기 등 제스처 감지 (추후 구현)."""

    def process(self, frame_bgr) -> Optional[str]:
        # TODO: MediaPipe + 규칙/LSTM으로 YouTube 제스처 인식
        return None

    def close(self) -> None:
        pass
