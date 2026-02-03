"""
제스처 표시 위젯
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

import config


class GestureDisplayWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
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

    def update_status(self, status: str, gesture: str = None):
        self.status_label.setText(status)
        if status == "대기 중":
            self.gesture_label.setText("동작 감지가 시작되지 않았습니다")
        elif gesture:
            self.gesture_label.setText(f"인식된 제스처: {gesture}")
        else:
            # 감지 중이지만 아직 제스처 없음
            self.gesture_label.setText("제스처가 인식되지 않았습니다")
