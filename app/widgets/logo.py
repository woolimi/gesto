"""
로고 위젯
"""

import os
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
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
            logo_label = QLabel()
            pixmap = QPixmap(logo_path)
            scaled_pixmap = pixmap.scaled(
                180, 60,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            logo_label.setPixmap(scaled_pixmap)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(logo_label)
        else:
            logo_text = QLabel(config.APP_NAME)
            logo_text.setFont(QFont("Arial", 18, QFont.Weight.Bold))
            logo_text.setStyleSheet(f"color: {config.COLOR_PRIMARY};")
            logo_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(logo_text)
        self.setLayout(layout)
