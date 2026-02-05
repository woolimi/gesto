"""
제스처 표시 위젯
"""

import time

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
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
        # Remove parent layout margins to let widgets center themselves
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)
        
        # Status Label Removed (User Request)
        # self.status_label = ...

        # Gesture Label (e.g., "인식된 제스처: ...")
        self.gesture_label = QLabel("동작 감지가 시작되지 않았습니다")
        self.gesture_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.gesture_label.setFont(QFont("Arial", 11))
        self.gesture_label.setStyleSheet(f"color: {config.COLOR_TEXT_SECONDARY}; background-color: transparent;")
        self.gesture_label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        layout.addWidget(self.gesture_label)

        self.setLayout(layout)
        # Remove widget-level background
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def _clear_gesture_label(self):
        """쿨다운 종료 시점에 호출: 인식된 제스처 라벨 초기화."""
        self._clear_timer = None
        if self._current_status == "감지 중":
            self.gesture_label.setText("제스처가 인식되지 않았습니다")
            self.gesture_label.setStyleSheet(f"color: {config.COLOR_TEXT_SECONDARY}; background-color: rgba(0, 0, 0, 150); border-radius: 8px; padding: 5px 15px;")


    def update_status(
        self,
        status: str,
        gesture: str = None,
        clear_at_monotonic: float | None = None,
    ):
        """clear_at_monotonic: 백엔드와 공유한 쿨다운 종료 시각(time.monotonic()). 이 시각에 라벨 초기화."""
        self._current_status = status
        # self.status_label.setText(status) # Removed
        
        if status == "대기 중":
            self._last_gesture = None
            if self._clear_timer is not None:
                self._clear_timer.stop()
                self._clear_timer = None
            self.gesture_label.setText("동작 감지가 시작되지 않았습니다")
            
            # Make Transparent when Idle
            # self.status_label.setStyleSheet(...)
            self.gesture_label.setStyleSheet(f"color: {config.COLOR_TEXT_SECONDARY}; background-color: transparent;")
            
        elif gesture:
            self._last_gesture = gesture
            self.gesture_label.setText(f"{gesture}") 
            # Active Style with Background
            # self.status_label.setStyleSheet(...)
            self.gesture_label.setStyleSheet("color: #00FFFF; font-weight: bold; background-color: rgba(0, 0, 0, 200); border-radius: 8px; padding: 8px 20px;")
            
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
                pass # Keep showing last gesture? User said "make it stay for a while".
                     # Logic is handled by cooldown mainly, but here we can ensure text remains.
            else:
                self.gesture_label.setText("제스처가 인식되지 않았습니다")
                self.gesture_label.setStyleSheet(f"color: {config.COLOR_TEXT_SECONDARY}; background-color: rgba(0, 0, 0, 150); border-radius: 8px; padding: 5px 15px;")
