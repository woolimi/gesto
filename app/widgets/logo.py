"""
로고 위젯
"""

import os
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QFont

import config


class LogoWidget(QWidget):
    """앱 로고 또는 앱명을 표시하는 위젯."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        logo_path = os.path.join(config.ASSETS_DIR, "gesto-light.png")
        if os.path.exists(logo_path):
            self.logo_label = QLabel()
            pixmap = QPixmap(logo_path)
            # 오리지널 로고 크기 설정
            self.logo_label.setPixmap(pixmap)
            self.logo_label.setScaledContents(True)
            self.logo_label.setMaximumHeight(80)
            self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(self.logo_label)
        else:
            self.logo_text = QLabel(config.APP_NAME)
            # 기본 폰트 설정
            self.logo_text.setFont(QFont("Arial", 18, QFont.Weight.Bold))
            self.logo_text.setStyleSheet(f"color: {config.COLOR_PRIMARY};")
            self.logo_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(self.logo_text)
        self.setLayout(layout)
