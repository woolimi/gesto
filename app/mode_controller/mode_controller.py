"""
Mode Controller — 현재 모드·감지 on/off 단일 소스, 제스처 → pynput 출력.
"""

from typing import Literal

from PyQt6.QtCore import QObject, pyqtSignal
from pynput.keyboard import Controller as KeyController, Key

ModeName = Literal["PPT", "YOUTUBE", "GAME"]


class ModeController(QObject):
    """현재 모드(PPT/YOUTUBE/GAME) 및 모션 감지 시작/정지 단일 소스. 제스처 시 pynput으로 동작 출력."""

    VALID_MODES: tuple[ModeName, ...] = ("PPT", "YOUTUBE", "GAME")
    detection_state_changed = pyqtSignal(bool)  # 감지 시작/정지 시 UI용

    def __init__(self, initial_mode: ModeName = "GAME", parent=None):
        super().__init__(parent)
        self._mode: ModeName = initial_mode if initial_mode in self.VALID_MODES else "PPT"
        self._is_detecting = False
        self._keyboard = KeyController()
        self._gesture_to_key = self._build_gesture_mapping()

    def _build_gesture_mapping(self) -> dict[tuple[str, str], object]:
        """(mode, gesture_name) -> pynput Key 또는 문자."""
        return {
            # PPT
            ("PPT", "next"): Key.right,
            ("PPT", "prev"): Key.left,
            ("PPT", "next_slide"): Key.right,
            ("PPT", "prev_slide"): Key.left,
            # YouTube
            ("YOUTUBE", "play_pause"): Key.space,
            ("YOUTUBE", "forward"): Key.right,
            ("YOUTUBE", "backward"): Key.left,
            ("YOUTUBE", "mute"): "m",
            ("YOUTUBE", "fullscreen"): "f",
            # Game
            ("GAME", "forward"): "w",
            ("GAME", "back"): "s",
            ("GAME", "left"): "a",
            ("GAME", "right"): "d",
            ("GAME", "직진"): "w",
            ("GAME", "후진"): "s",
            ("GAME", "좌회전"): "a",
            ("GAME", "우회전"): "d",
        }

    def set_mode(self, mode: ModeName) -> None:
        if mode in self.VALID_MODES:
            self._mode = mode

    def get_mode(self) -> ModeName:
        return self._mode

    def set_detection_state(self, is_active: bool) -> None:
        """공통 트리거(시작/정지)에서 호출. 감지 on/off 상태 갱신 후 UI에 시그널."""
        if self._is_detecting == is_active:
            return
        self._is_detecting = is_active
        self.detection_state_changed.emit(is_active)

    def get_is_detecting(self) -> bool:
        return self._is_detecting

    def on_gesture(self, gesture_name: str) -> None:
        """모드별 감지(ppt/game 등)에서 인식된 제스처 시 호출. 현재 모드 기준으로 pynput 키 입력."""
        if not gesture_name or not self._is_detecting:
            return
        key = self._gesture_to_key.get((self._mode, gesture_name))
        if key is None:
            key = self._gesture_to_key.get((self._mode, gesture_name.lower()))
        if key is not None:
            try:
                self._keyboard.press(key)
                self._keyboard.release(key)
            except Exception:
                pass
