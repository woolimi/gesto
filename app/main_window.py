"""
메인 윈도우 (UI 전용)
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStatusBar, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal

import config
from app.widgets import LogoWidget, WebcamPanelWidget, ControlPanelWidget


class MainWindow(QMainWindow):
    start_detection = pyqtSignal()
    stop_detection = pyqtSignal()
    sensitivity_changed = pyqtSignal(int)
    mode_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.current_mode = "PPT"
        self.sensitivity = config.SENSITIVITY_DEFAULT
        self.is_detecting = False

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(config.WINDOW_TITLE)
        self.setGeometry(100, 100, config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
        self.setStyleSheet(f"background-color: {config.COLOR_BACKGROUND};")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        self.webcam_panel = WebcamPanelWidget()
        content_layout.addWidget(self.webcam_panel, 2)

        right_content = QWidget()
        right_layout = QVBoxLayout(right_content)
        right_layout.setSpacing(15)
        right_layout.addWidget(LogoWidget())
        self.control_panel = ControlPanelWidget()
        right_layout.addWidget(self.control_panel)
        right_layout.addStretch()
        scroll = QScrollArea()
        scroll.setWidget(right_content)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content_layout.addWidget(scroll, 1)

        main_layout.addLayout(content_layout)
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet(f"background-color: {config.COLOR_BACKGROUND}; color: {config.COLOR_TEXT_SECONDARY};")
        self.status_bar.showMessage("준비됨")
        self.setStatusBar(self.status_bar)
        central_widget.setLayout(main_layout)

        self.control_panel.ppt_radio.setChecked(True)

        self.control_panel.mode_changed.connect(self.on_mode_changed)
        self.control_panel.sensitivity_changed.connect(self.on_sensitivity_changed)
        self.control_panel.toggle_clicked.connect(self.on_toggle_clicked)

    def closeEvent(self, event):
        event.accept()

    def set_detection_state(self, is_active: bool):
        self.is_detecting = is_active
        self.control_panel.set_detection_state(is_active)
        self.webcam_panel.set_recording(is_active)
        if is_active:
            self.status_bar.showMessage("제스처 인식 시작됨")
            self.webcam_panel.gesture_display.update_status("감지 중", None)
            self.start_detection.emit()
        else:
            self.status_bar.showMessage("제스처 인식 중지됨")
            self.webcam_panel.gesture_display.update_status("대기 중", None)
            self.stop_detection.emit()

    def on_toggle_clicked(self):
        self.set_detection_state(not self.is_detecting)

    def on_sensitivity_changed(self, value: int):
        self.sensitivity = value
        self.control_panel.set_sensitivity_label(value)
        self.sensitivity_changed.emit(value)

    def on_mode_changed(self, mode: str):
        self.current_mode = mode
        self.mode_changed.emit(mode)
        self.status_bar.showMessage(f"{mode} 모드로 전환됨")

    def update_webcam_frame(self, pixmap):
        """웹캠 프레임 표시 (백엔드 연결 시 사용)."""
        if pixmap and not pixmap.isNull():
            label_size = self.webcam_panel.webcam_label.size()
            if label_size.width() > 0 and label_size.height() > 0:
                scaled_pixmap = pixmap.scaled(
                    label_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            else:
                scaled_pixmap = pixmap
            if scaled_pixmap and not scaled_pixmap.isNull():
                self.webcam_panel.webcam_label.setPixmap(scaled_pixmap)
                if self.webcam_panel.webcam_label.text():
                    self.webcam_panel.webcam_label.setText("")

    def update_gesture(self, gesture_name: str):
        """인식된 제스처 표시 (백엔드 연결 시 사용)."""
        if self.is_detecting:
            self.webcam_panel.gesture_display.update_status("감지 중", gesture_name)
