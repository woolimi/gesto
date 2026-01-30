"""
웹캠 영상 패널 위젯
"""

from PyQt6.QtWidgets import (
    QGroupBox, QVBoxLayout, QLabel, QWidget, QGridLayout, QFrame,
    QGraphicsOpacityEffect,
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont

import config
from app.widgets.gesture_display import GestureDisplayWidget


class WebcamPanelWidget(QGroupBox):
    """웹캠 영상 라벨과 제스처 표시 위젯을 담는 그룹박스."""

    def __init__(self, parent=None):
        super().__init__("웹캠 영상", parent)
        self._opacity_effect = None
        self._opacity_animation = None
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: 14px;
                color: {config.COLOR_TEXT_PRIMARY};
                border: 2px solid {config.COLOR_SECONDARY};
                border-radius: 10px;
                margin-top: 10px;
                padding-top: 10px;
            }}
        """)
        layout = QVBoxLayout()
        layout.setSpacing(10)

        webcam_container = QWidget()
        grid = QGridLayout(webcam_container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(0)

        self.webcam_label = QLabel()
        self.webcam_label.setMinimumSize(640, 480)
        self.webcam_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.webcam_label.setStyleSheet(f"""
            background-color: #F3F4F6;
            border: 2px dashed {config.COLOR_SECONDARY};
            border-radius: 10px;
            color: {config.COLOR_TEXT_SECONDARY};
        """)
        self.webcam_label.setText("웹캠 영상이 여기에 표시됩니다")
        self.webcam_label.setFont(QFont("Arial", 12))
        grid.addWidget(self.webcam_label, 0, 0)

        indicator_wrapper = QFrame()
        indicator_wrapper.setStyleSheet("background: transparent;")
        wrapper_layout = QGridLayout(indicator_wrapper)
        wrapper_layout.setContentsMargins(0, 12, 12, 0)
        wrapper_layout.setSpacing(0)
        self.recording_indicator = QLabel()
        self.recording_indicator.setFixedSize(14, 14)
        self.recording_indicator.setStyleSheet(
            "background-color: #EF4444; border-radius: 7px;"
        )
        self.recording_indicator.setVisible(False)
        self._opacity_effect = QGraphicsOpacityEffect(self.recording_indicator)
        self.recording_indicator.setGraphicsEffect(self._opacity_effect)
        wrapper_layout.addWidget(self.recording_indicator, 0, 0)
        grid.addWidget(indicator_wrapper, 0, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

        layout.addWidget(webcam_container)
        self.gesture_display = GestureDisplayWidget()
        layout.addWidget(self.gesture_display)
        self.setLayout(layout)

    def _setup_opacity_animation(self):
        if self._opacity_animation is not None:
            return
        self._opacity_animation = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._opacity_animation.setDuration(1000)
        self._opacity_animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._opacity_animation.setStartValue(1.0)
        self._opacity_animation.setEndValue(0.5)
        self._opacity_animation.finished.connect(self._reverse_opacity_animation)

    def _reverse_opacity_animation(self):
        if self._opacity_animation is None:
            return
        start = self._opacity_animation.startValue()
        end = self._opacity_animation.endValue()
        self._opacity_animation.setStartValue(end)
        self._opacity_animation.setEndValue(start)
        self._opacity_animation.start()

    def set_recording(self, active: bool):
        """웹캠 영상 우상단에 녹화 표시등 표시. opacity 1 ↔ 0.5 부드럽게 전환."""
        if active:
            self._setup_opacity_animation()
            self._opacity_effect.setOpacity(1.0)
            self.recording_indicator.setVisible(True)
            self._opacity_animation.setStartValue(1.0)
            self._opacity_animation.setEndValue(0.5)
            self._opacity_animation.start()
        else:
            if self._opacity_animation is not None:
                self._opacity_animation.stop()
                self._opacity_animation.finished.disconnect(self._reverse_opacity_animation)
                self._opacity_animation = None
            self.recording_indicator.setVisible(False)
