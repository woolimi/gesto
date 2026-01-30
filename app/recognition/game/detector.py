"""
Game 모드 전용 감지.
(추후: 직진/후진/좌회전/우회전 등 Posture)

이 디텍터는 process(frame) → 제스처 이름 문자열만 반환하면 됨.
제스처 이름 → 키 매핑 및 pynput 입력은 ModeController가 담당.
지원 문자열: "직진"|"forward" → w, "후진"|"back" → s, "좌회전"|"left" → a, "우회전"|"right" → d
(매핑 추가는 mode_controller._build_gesture_mapping)
"""

from typing import Optional


class GameDetector:
    """Game 모드: 직진/후진/좌회전/우회전 등 자세 감지 (추후 구현)."""

    def process(self, frame_bgr) -> Optional[str]:
        """BGR 프레임에서 자세/제스처 판별. 인식되면 '직진'/'후진'/'좌회전'/'우회전' 등 문자열 반환."""
        # TODO: MediaPipe Posture로 방향 인식
        return None

    def close(self) -> None:
        """리소스 해제 (모델 등)."""
        pass
