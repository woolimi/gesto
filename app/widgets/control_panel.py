"""
제어 패널 위젯 (모드 선택, 감도, 시작/종료 버튼)
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QLabel, QPushButton,
    QRadioButton, QButtonGroup, QSlider, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal

import config


class ControlPanelWidget(QGroupBox):
    """모드 선택, 감도 슬라이더, 시작/종료 버튼을 담는 위젯."""

    mode_changed = pyqtSignal(str)
    sensitivity_changed = pyqtSignal(int)
    toggle_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("제어", parent)
        self._init_ui()
        self.setMinimumHeight(380)

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
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        mode_group = QGroupBox("모드 선택")
        mode_group.setStyleSheet(f"color: {config.COLOR_TEXT_PRIMARY};")
        mode_layout = QVBoxLayout()
        self.mode_button_group = QButtonGroup()
        self.ppt_radio = QRadioButton("PPT 모드")
        self.youtube_radio = QRadioButton("유투브 모드")
        self.game_radio = QRadioButton("게임 모드")
        self.mode_button_group.addButton(self.ppt_radio, 0)
        self.mode_button_group.addButton(self.youtube_radio, 1)
        self.mode_button_group.addButton(self.game_radio, 2)
        self.ppt_radio.setStyleSheet(f"color: {config.COLOR_TEXT_PRIMARY}; font-size: 12px;")
        self.youtube_radio.setStyleSheet(f"color: {config.COLOR_TEXT_PRIMARY}; font-size: 12px;")
        self.game_radio.setStyleSheet(f"color: {config.COLOR_TEXT_PRIMARY}; font-size: 12px;")
        self.ppt_radio.toggled.connect(lambda: self.mode_changed.emit("PPT"))
        self.youtube_radio.toggled.connect(lambda: self.mode_changed.emit("YOUTUBE"))
        self.game_radio.toggled.connect(lambda: self.mode_changed.emit("GAME"))
        mode_layout.addWidget(self.ppt_radio)
        mode_layout.addWidget(self.youtube_radio)
        mode_layout.addWidget(self.game_radio)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        sensitivity_group = QGroupBox("감도 설정")
        sensitivity_group.setStyleSheet(f"color: {config.COLOR_TEXT_PRIMARY};")
        sensitivity_layout = QVBoxLayout()
        self.sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self.sensitivity_slider.setMinimum(config.SENSITIVITY_MIN)
        self.sensitivity_slider.setMaximum(config.SENSITIVITY_MAX)
        self.sensitivity_slider.setValue(config.SENSITIVITY_DEFAULT)
        self.sensitivity_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{ border: 1px solid {config.COLOR_SECONDARY}; height: 8px; background: #E5E7EB; border-radius: 4px; }}
            QSlider::handle:horizontal {{ background: {config.COLOR_SECONDARY}; border: 2px solid {config.COLOR_PRIMARY}; width: 20px; margin: -2px 0; border-radius: 10px; }}
            QSlider::handle:horizontal:hover {{ background: {config.COLOR_BUTTON_HOVER}; }}
        """)
        self.sensitivity_slider.valueChanged.connect(self.sensitivity_changed.emit)
        sensitivity_layout.addWidget(self.sensitivity_slider)
        self.sensitivity_label = QLabel(f"감도: {config.SENSITIVITY_DEFAULT}%")
        self.sensitivity_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sensitivity_label.setStyleSheet(f"color: {config.COLOR_TEXT_PRIMARY}; font-size: 12px; font-weight: bold;")
        sensitivity_layout.addWidget(self.sensitivity_label)
        sensitivity_group.setLayout(sensitivity_layout)
        layout.addWidget(sensitivity_group)

        self.toggle_button = QPushButton("동작 감지 시작")
        self.toggle_button.setMinimumHeight(48)
        self.toggle_button.setStyleSheet(f"""
            QPushButton {{ background-color: {config.COLOR_SECONDARY}; color: white; border: none; padding: 12px; border-radius: 8px; font-size: 14px; font-weight: bold; }}
            QPushButton:hover {{ background-color: {config.COLOR_BUTTON_HOVER}; }}
            QPushButton:pressed {{ background-color: {config.COLOR_PRIMARY}; }}
        """)
        self.toggle_button.clicked.connect(self.toggle_clicked.emit)
        layout.addWidget(self.toggle_button)

    def set_detection_state(self, is_active: bool):
        """토글 버튼 텍스트 및 스타일 설정."""
        if is_active:
            self.toggle_button.setText("동작 감지 종료")
            self.toggle_button.setStyleSheet("""
                QPushButton { background-color: #EF4444; color: white; border: none; padding: 12px; border-radius: 8px; font-size: 14px; font-weight: bold; }
                QPushButton:hover { background-color: #DC2626; }
                QPushButton:pressed { background-color: #B91C1C; }
            """)
        else:
            self.toggle_button.setText("동작 감지 시작")
            self.toggle_button.setStyleSheet(f"""
                QPushButton {{ background-color: {config.COLOR_SECONDARY}; color: white; border: none; padding: 12px; border-radius: 8px; font-size: 14px; font-weight: bold; }}
                QPushButton:hover {{ background-color: {config.COLOR_BUTTON_HOVER}; }}
                QPushButton:pressed {{ background-color: {config.COLOR_PRIMARY}; }}
            """)

    def set_sensitivity_label(self, value: int):
        """감도 라벨 텍스트 업데이트."""
        self.sensitivity_label.setText(f"감도: {value}%")
