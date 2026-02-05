"""
제어 패널 위젯 (모드 선택, 감도, 시작/종료 버튼)
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QSlider, QComboBox, QFrame, QGraphicsDropShadowEffect, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QTimer, QPoint
from PyQt6.QtGui import QColor, QFont

import config

class SensitivityPopover(QWidget):
    """감도 조절을 위한 플로팅 팝오버 위젯"""
    value_changed = pyqtSignal(int)

    def __init__(self, parent=None, initial_value=50, scale=1.0):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.scale = scale
        self.init_ui(initial_value)

    def init_ui(self, initial_value):
        layout = QVBoxLayout(self)
        s = self.scale
        layout.setContentsMargins(int(10*s), int(10*s), int(10*s), int(10*s))
        
        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(20, 30, 50, 245);
                border: 1px solid rgba(0, 255, 255, 120);
                border-radius: {int(12*s)}px;
            }}
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(int(15*s), int(15*s), int(15*s), int(15*s))
        container_layout.setSpacing(int(10*s))
        
        self.label = QLabel(f"감도: {initial_value}%")
        self.label.setStyleSheet(f"color: white; font-weight: bold; font-size: {int(16*s)}px; border: none; background: transparent; font-family: 'Audiowide', 'Black Han Sans'; letter-spacing: 1px;")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self.label)
        
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(config.SENSITIVITY_MIN)
        self.slider.setMaximum(config.SENSITIVITY_MAX)
        self.slider.setValue(initial_value)
        self.slider.setFixedHeight(int(30*s))
        
        sh = int(22*s) # 슬라이더 핸들 크기
        self.slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                border: 1px solid rgba(255, 255, 255, 50);
                height: {int(8*s)}px;
                background: rgba(0, 0, 0, 100);
                border-radius: {int(4*s)}px;
            }}
            QSlider::handle:horizontal {{
                background: {config.COLOR_PRIMARY};
                border: 2px solid white;
                width: {sh}px;
                height: {sh}px;
                margin: -{int((sh-8*s)/2)}px 0;
                border-radius: {int(sh/2)}px;
            }}
        """)
        self.slider.valueChanged.connect(self._on_value_changed)
        container_layout.addWidget(self.slider)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.btn_minus = QPushButton("-10")
        self.btn_plus = QPushButton("+10")
        
        for btn in (self.btn_minus, self.btn_plus):
            btn.setFixedHeight(int(36*s))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgba(0, 255, 255, 30);
                    color: #00FFFF;
                    border: 1px solid rgba(0, 255, 255, 100);
                    border-radius: {int(8*s)}px;
                    font-family: 'Audiowide';
                    font-weight: bold;
                    font-size: {int(13*s)}px;
                }}
                QPushButton:hover {{
                    background-color: rgba(0, 255, 255, 80);
                    color: white;
                }}
                QPushButton:pressed {{
                    background-color: rgba(0, 255, 255, 120);
                }}
            """)
            
        self.btn_minus.clicked.connect(lambda: self._adjust_value(-10))
        self.btn_plus.clicked.connect(lambda: self._adjust_value(10))
        
        btn_layout.addWidget(self.btn_minus)
        btn_layout.addWidget(self.btn_plus)
        container_layout.addLayout(btn_layout)
        
        range_layout = QHBoxLayout()
        lbl_low = QLabel("낮음")
        lbl_high = QLabel("높음")
        for lbl in (lbl_low, lbl_high):
            lbl.setStyleSheet(f"color: rgba(0, 255, 255, 180); font-size: {int(12*s)}px; border: none; font-family: 'Michroma', 'Noto Sans KR'; letter-spacing: 1px; background: transparent;")
        range_layout.addWidget(lbl_low)
        range_layout.addStretch()
        range_layout.addWidget(lbl_high)
        container_layout.addLayout(range_layout)
        
        layout.addWidget(container)

    def _on_value_changed(self, val):
        self.label.setText(f"감도: {val}%")
        self.value_changed.emit(val)

    def _adjust_value(self, delta):
        new_val = self.slider.value() + delta
        new_val = max(config.SENSITIVITY_MIN, min(config.SENSITIVITY_MAX, new_val))
        self.slider.setValue(new_val)

class ControlPanelWidget(QWidget):
    """
    모드 선택, 감도 조절, 시작/종료 버튼을 포함하는 제어 패널.
    """
    mode_changed = pyqtSignal(str)
    sensitivity_changed = pyqtSignal(int)
    toggle_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sensitivity_value = config.SENSITIVITY_DEFAULT
        self.current_scale = 1.0
        self.init_ui()

    def update_scaling(self, scale):
        """실시간 크기 조절 대응 (성능 최적화를 위해 다이렉트 폰트/크기 업데이트)"""
        self.current_scale = scale
        base_font_size = max(10, int(13 * scale))
        btn_font_size = max(10, int(14 * scale))
        
        font = QFont("Michroma", base_font_size, QFont.Weight.Bold)
        self.mode_combo.setFont(font)
        self.sensitivity_btn.setFont(font)
        
        toggle_font = QFont("Michroma", btn_font_size, QFont.Weight.Bold)
        self.toggle_button.setFont(toggle_font)
        
        btn_h = max(25, int(45 * scale))
        self.mode_combo.setFixedHeight(btn_h)
        self.sensitivity_btn.setFixedHeight(btn_h)
        self.toggle_button.setFixedHeight(btn_h)
        
        view = self.mode_combo.view()
        if view:
            view_font = QFont("Michroma", base_font_size)
            view.setFont(view_font)

    def init_ui(self):
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(5)

        self.setStyleSheet("""
            QWidget {
                background-color: rgba(20, 20, 30, 210);
                border: 1px solid rgba(0, 255, 255, 60);
                border-radius: 20px;
                font-family: 'Michroma', 'Noto Sans KR', sans-serif;
                min-height: 30px;
            }
        """)

        # 1. 모드 선택 드롭다운
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["PPT 모드 📑", "Youtube/Media 📺", "게임 모드 🎮"])
        self.mode_map = {0: "PPT", 1: "YOUTUBE", 2: "GAME"}
        self.mode_combo.setCurrentIndex(2)
        
        self.mode_combo.setFixedHeight(45)
        self.mode_combo.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.mode_combo.wheelEvent = lambda event: event.ignore() 
        
        self.mode_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: rgba(255, 255, 255, 15);
                color: white;
                border: 1px solid rgba(0, 255, 255, 50);
                border-radius: 8px;
                padding: 1px 15px;
                font-family: 'Michroma', 'Black Han Sans', 'Noto Sans KR';
                font-size: 13px;
                font-weight: bold;
            }}
            QComboBox:hover {{
                background-color: rgba(0, 255, 255, 30);
                border: 1px solid #00FFFF;
            }}
            QComboBox::drop-down {{
                border: none;
                background: transparent;
            }}
            QComboBox::down-arrow {{
                image: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: #101020;
                color: white;
                selection-background-color: #00FFFF;
                selection-color: black;
                outline: none;
                border: 1px solid #00FFFF;
            }}
        """)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_combo_changed)
        layout.addWidget(self.mode_combo)

        # 2. 감도 조절 버튼
        self.sensitivity_btn = QPushButton(f"감도: {self.sensitivity_value}%")
        self.sensitivity_btn.setFixedHeight(45)
        self.sensitivity_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sensitivity_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.sensitivity_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 15);
                color: white;
                border: 1px solid rgba(255, 255, 255, 40);
                border-radius: 8px;
                padding: 1px 15px;
                font-family: 'Michroma', 'Black Han Sans', 'Noto Sans KR';
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 40);
                border: 1px solid white;
            }
        """)
        self.sensitivity_btn.clicked.connect(self._show_sensitivity_popover)
        layout.addWidget(self.sensitivity_btn)

        # 3. 토글 버튼 (시작/중지)
        self.toggle_button = QPushButton("동작 감지 시작")
        self.toggle_button.setFixedHeight(45)
        self.toggle_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        self._update_toggle_style(False) 
        self.toggle_button.clicked.connect(self.toggle_clicked.emit)
        layout.addWidget(self.toggle_button)

    def _on_mode_combo_changed(self, index):
        mode_str = self.mode_map.get(index, "GAME")
        self.mode_changed.emit(mode_str)
        self.mode_combo.clearFocus() 
        self.setFocus()

    def _show_sensitivity_popover(self):
        pop = SensitivityPopover(self, self.sensitivity_value, scale=self.current_scale)
        pop.value_changed.connect(self._on_popover_value)
        
        pop.setFixedWidth(int(240 * self.current_scale))
        pop.adjustSize()
        
        btn_global = self.sensitivity_btn.mapToGlobal(self.sensitivity_btn.rect().topLeft())
        x = int(btn_global.x() + (self.sensitivity_btn.width() - pop.width()) / 2)
        y = int(btn_global.y() - pop.height() - (10 * self.current_scale))
        pop.move(x, y)
        pop.show()
        
    def _on_popover_value(self, val):
        self.sensitivity_value = val
        self.sensitivity_btn.setText(f"감도: {val}%")
        self.sensitivity_changed.emit(val)

    def set_detection_state(self, is_active: bool):
        if is_active:
            self.toggle_button.setText("감지 중지")
            self._update_toggle_style(True)
        else:
            self.toggle_button.setText("동작 감지 시작")
            self._update_toggle_style(False)

    def set_sensitivity_label(self, value: int):
        self.sensitivity_value = value
        self.sensitivity_btn.setText(f"감도: {value}%")

    def _update_toggle_style(self, is_detecting: bool):
        """성능을 고려한 최소한의 스타일 업데이트"""
        if is_detecting:
            self.toggle_button.setText("동작 감지 중지")
            self.toggle_button.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 0, 100, 30);
                    color: #FF5577;
                    border: 1px solid #FF5577;
                    border-radius: 8px;
                }
                QPushButton:hover { background-color: rgba(255, 0, 100, 60); color: white; }
            """)
        else:
            self.toggle_button.setText("동작 감지 시작")
            self.toggle_button.setStyleSheet("""
                QPushButton {
                    background-color: rgba(0, 255, 255, 20);
                    color: #00FFFF;
                    border: 1px solid #00FFFF;
                    border-radius: 8px;
                }
                QPushButton:hover { background-color: rgba(0, 255, 255, 50); color: white; }
            """)
        
        base_font_size = max(10, int(14 * self.current_scale))
        self.toggle_button.setFont(QFont("Michroma", base_font_size, QFont.Weight.Bold))
