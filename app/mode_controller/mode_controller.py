"""
Mode Controller — 현재 모드·감지 on/off 단일 소스, 제스처 → pynput 출력.
"""

import time
from typing import Literal

from PyQt6.QtCore import QObject, pyqtSignal
from pynput.keyboard import Controller as KeyController, Key

import config

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
        """config.GESTURE_ACTION_MAP에서 매핑을 로드하고 문자열 키를 pynput Key 객체로 변환."""
        mapping = {}
        for mode, gestures in config.GESTURE_ACTION_MAP.items():
            for g_name, key_str in gestures.items():
                resolved_key = self._resolve_key(key_str)
                mapping[(mode, g_name)] = resolved_key
        return mapping

    def _resolve_key(self, key_str: str) -> object:
        """문자열을 pynput Key(또는 문자) 또는 조합키 리스트로 변환. 'ctrl+f5' → [Key.ctrl, Key.f5]."""
        key_str = key_str.strip()
        if "+" in key_str:
            # 조합키: 순서대로 press, 역순 release
            parts = [p.strip().lower() for p in key_str.split("+") if p.strip()]
            resolved = []
            for p in parts:
                if len(p) == 1:
                    resolved.append(p)
                else:
                    try:
                        resolved.append(getattr(Key, p))
                    except AttributeError:
                        resolved.append(p)
            return resolved
        if len(key_str) == 1:
            return key_str
        try:
            return getattr(Key, key_str.lower())
        except AttributeError:
            return key_str

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

    def on_gesture(self, gesture_name: str, _cooldown_until: float = 0.0, _probs: dict = None) -> None:
        """모드별 감지(ppt/game 등)에서 인식된 제스처 시 호출. 현재 모드 기준으로 pynput 키 입력.
        gesture_name에 '|'가 있으면 복수 제스처(예: 'forward|right')로 해석.
        Unknown 또는 빈 제스처는 PPT/YouTube/Game 공통으로 모션 미인식과 동일하게 무시(동작 없음)."""
        if not self._is_detecting:
            return
        raw = (gesture_name or "").strip()
        if not raw or raw.lower() == "unknown":
            return
        names = [s.strip() for s in raw.split("|") if s.strip()]
        keys = []
        for name in names:
            key = self._gesture_to_key.get((self._mode, name))
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
                    if isinstance(k, list):
                        for kk in k:
                            self._keyboard.press(kk)
                        for kk in reversed(k):
                            self._keyboard.release(kk)
                    else:
                        self._keyboard.press(k)
                        self._keyboard.release(k)
                time.sleep(0.04)
            except Exception:
                pass
