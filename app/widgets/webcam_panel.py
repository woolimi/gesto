"""
웹캠 영상 패널 위젯
"""

from PyQt6.QtWidgets import (
    QGroupBox, QVBoxLayout, QLabel, QWidget, QGridLayout, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

import config
from app.widgets.gesture_display import GestureDisplayWidget
from app.widgets.neon_frame import NeonFrameWidget


class WebcamPanelWidget(QGroupBox):
    """웹캠 영상 라벨과 제스처 표시 위젯을 담는 그룹박스."""

    def __init__(self, parent=None):
        super().__init__("", parent)
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("""
            QGroupBox {
                border: none;
                margin-top: 0px;
                padding-top: 0px;
            }
        """)

        # 비율 유지를 위한 중앙 정렬 레이아웃
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(10)

        # 카메라 컨테이너
        self.camera_container = QWidget()
        self.cam_layout = QVBoxLayout(self.camera_container)
        self.cam_layout.setContentsMargins(0, 0, 0, 0)
        self.cam_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.webcam_label = QLabel()
        self.webcam_label.setMinimumSize(10, 10)
        self.webcam_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.webcam_label.setStyleSheet(f"""
            background-color: #000000;
            color: {config.COLOR_TEXT_PRIMARY};
            border: 1px solid rgba(0, 255, 255, 0.2);
            border-radius: 5px;
        """)
        
        self.neon_frame = NeonFrameWidget(self.webcam_label)
        self.neon_frame.setMinimumSize(10, 10)
        self.cam_layout.addWidget(self.neon_frame)
        
        self.main_layout.addWidget(self.camera_container, 1)
        self.setLayout(self.main_layout)

    def resizeEvent(self, event):
        """카메라 뷰의 4:3 비율 유지"""
        super().resizeEvent(event)
        w = self.camera_container.width()
        h = self.camera_container.height()
        
        if w > 0 and h > 0:
            target_ratio = 4.0 / 3.0
            curr_ratio = w / h
            
            if curr_ratio > target_ratio:
                new_h = h
                new_w = int(h * target_ratio)
            else:
                new_w = w
                new_h = int(w / target_ratio)
                
            self.neon_frame.setFixedSize(new_w, new_h)

    def set_recording(self, active: bool):
        """Webcam indicator removed."""
        pass
