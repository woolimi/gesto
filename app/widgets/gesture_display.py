"""
제스처 표시 위젯
"""

import time

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

import config


class GestureDisplayWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_gesture: str | None = None
        self._clear_timer: QTimer | None = None
        self._current_status = "대기 중"
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        self.status_label = QLabel("대기 중")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.status_label.setStyleSheet(f"color: {config.COLOR_TEXT_PRIMARY};")
        layout.addWidget(self.status_label)
        self.gesture_label = QLabel("동작 감지가 시작되지 않았습니다")
        self.gesture_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.gesture_label.setFont(QFont("Arial", 12))
        self.gesture_label.setStyleSheet(f"color: {config.COLOR_TEXT_SECONDARY};")
        layout.addWidget(self.gesture_label)
        self.setLayout(layout)
        self.setStyleSheet(f"background-color: {config.COLOR_BACKGROUND}; border-radius: 10px;")

    def _clear_gesture_label(self):
        """쿨다운 종료 시점에 호출: 인식된 제스처 라벨 초기화."""
        self._clear_timer = None
        self._last_gesture = None
        if self._current_status == "감지 중":
            self.gesture_label.setText("제스처가 인식되지 않았습니다")

    def update_status(
        self,
        status: str,
        gesture: str = None,
        clear_at_monotonic: float | None = None,
    ):
        """clear_at_monotonic: 백엔드와 공유한 쿨다운 종료 시각(time.monotonic()). 이 시각에 라벨 초기화."""
        self._current_status = status
        self.status_label.setText(status)
        if status == "대기 중":
            self._last_gesture = None
            if self._clear_timer is not None:
                self._clear_timer.stop()
                self._clear_timer = None
            self.gesture_label.setText("동작 감지가 시작되지 않았습니다")
        elif gesture:
            self._last_gesture = gesture
            self.gesture_label.setText(f"인식된 제스처: {gesture}")
            if self._clear_timer is not None:
                self._clear_timer.stop()
            if clear_at_monotonic is not None and clear_at_monotonic > 0:
                delay_sec = max(0.0, clear_at_monotonic - time.monotonic())
                self._clear_timer = QTimer(self)
                self._clear_timer.setSingleShot(True)
                self._clear_timer.timeout.connect(self._clear_gesture_label)
                self._clear_timer.start(int(delay_sec * 1000))
        else:
            if self._last_gesture is not None:
                self.gesture_label.setText(f"인식된 제스처: {self._last_gesture}")
            else:
                self.gesture_label.setText("제스처가 인식되지 않았습니다")
