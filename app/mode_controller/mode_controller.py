"""
Mode Controller — 현재 모드·감지 on/off 단일 소스, 제스처 → pynput 출력.
"""

import time
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
        # Game 모드: 현재 눌려 있다고 보는 키. 방향 전환 시 이전 키를 먼저 놓기 위함.
        self._last_game_keys: set = set()

    def _build_gesture_mapping(self) -> dict[tuple[str, str], object]:
        """(mode, gesture_name) -> pynput Key 또는 문자. Game은 방향키(↑↓←→)."""
        return {
            # PPT: 공통 LSTM Swipe만 사용 (app/models/ lstm_legacy)
            ("PPT", "Swipe_Left"): Key.left,
            ("PPT", "Swipe_Right"): Key.right,
            ("PPT", "next"): Key.right,
            ("PPT", "prev"): Key.left,
            ("PPT", "next_slide"): Key.right,
            ("PPT", "prev_slide"): Key.left,
            # YouTube: 공통 LSTM 4종 제스처 → YouTube 단축키 (j 10초 뒤, l 10초 앞, k 재생·정지, m 음소거)
            ("YOUTUBE", "Swipe_Left"): "j",
            ("YOUTUBE", "Swipe_Right"): "l",
            ("YOUTUBE", "Pinch_Out"): "k",
            ("YOUTUBE", "Pinch_In"): "m",
            # Game: 방향키 (크롬 등에서 방향키로 동작하는 게임 제어)
            ("GAME", "forward"): Key.up,
            ("GAME", "back"): Key.down,
            ("GAME", "left"): Key.left,
            ("GAME", "right"): Key.right,
            ("GAME", "직진"): Key.up,
            ("GAME", "후진"): Key.down,
            ("GAME", "좌회전"): Key.left,
            ("GAME", "우회전"): Key.right,
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
        if not is_active and self._last_game_keys:
            self._release_game_keys()
        self.detection_state_changed.emit(is_active)

    def get_is_detecting(self) -> bool:
        return self._is_detecting

    def _release_game_keys(self) -> None:
        """GAME 모드에서 현재 눌려 있다고 보는 키를 모두 release. macOS Key Sticky 방지."""
        try:
            for k in self._last_game_keys:
                self._keyboard.release(k)
        except Exception:
            pass
        self._last_game_keys = set()

    def on_gesture(self, gesture_name: str, _cooldown_until: float = 0.0) -> None:
        """모드별 감지(ppt/game 등)에서 인식된 제스처 시 호출. 현재 모드 기준으로 pynput 키 입력.
        gesture_name에 '|'가 있으면 복수 제스처(예: 'forward|right')로 해석.
        GAME 모드: 방향이 바뀔 때만 즉시 이전 키 release 후 새 키 press (macOS Key Sticky 방지)."""
        if not self._is_detecting:
            return
        names = [s.strip() for s in (gesture_name or "").split("|") if s.strip()]
        keys = []
        for name in names:
            key = self._gesture_to_key.get((self._mode, name))
            if key is None:
                key = self._gesture_to_key.get((self._mode, name.lower()))
            if key is not None:
                keys.append(key)

        if self._mode == "GAME":
            keys_set = set(keys)
            if keys_set != self._last_game_keys:
                self._release_game_keys()
                if keys_set:
                    try:
                        for k in keys_set:
                            self._keyboard.press(k)
                        self._last_game_keys = keys_set
                    except Exception:
                        pass
            return

        if keys:
            try:
                for k in keys:
                    self._keyboard.press(k)
                time.sleep(0.04)
                for k in keys:
                    self._keyboard.release(k)
            except Exception:
                pass
