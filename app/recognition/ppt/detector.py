"""
PPT 모드 전용 감지.
(추후: 다음/이전 슬라이드 등 제스처)
"""

from typing import Optional


class PPTDetector:
    """PPT 모드: 다음/이전 슬라이드 등 제스처 감지 (추후 구현)."""

    def process(self, frame_bgr) -> Optional[str]:
        # TODO: MediaPipe + 규칙/LSTM으로 PPT 제스처 인식
        return None

    def close(self) -> None:
        pass
