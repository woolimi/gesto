from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QSlider, QFrame, QGraphicsDropShadowEffect, QSizePolicy,
    QMenu, QWidgetAction
)
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QTimer, QPoint
from PyQt6.QtGui import QColor, QFont, QAction

import config
from app.workers.sound_worker import play_ui_click

class CenteredMenuAction(QWidgetAction):
    """QMenu 내에서 명시적으로 중앙 정렬된 텍스트를 구현하기 위한 커스텀 액션"""
    def __init__(self, label, code, parent=None):
        super().__init__(parent)
        self.code = code
        self.label_text = label
        
        # 커스텀 위젯 생성
        self.widget = QWidget()
        layout = QHBoxLayout(self.widget)
        layout.setContentsMargins(15, 8, 15, 8)
        
        self.label = QLabel(label)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # 중요: 라벨이 마우스 클릭을 막지 않도록 투명화 (위젯이 이벤트를 대신 받음)
        self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.label.setStyleSheet(f"""
            color: white;
            font-family: '{config.FONT_MAIN}';
            font-size: 14px;
            font-weight: 800;
            background: transparent;
            border: none;
        """)
        layout.addWidget(self.label)
        
        self.setDefaultWidget(self.widget)
        
        # 호버 효과를 위해 위젯 스타일 설정
        self.widget.setStyleSheet("""
            QWidget:hover {
                background-color: rgba(0, 255, 255, 60);
                border-radius: 8px;
            }
            QLabel:hover { color: #00FFFF; }
        """)
        
        # 클릭 이벤트 처리 (위젯 클릭 시 액션 트리거)
        # mousePressEvent에서 즉시 트리거하여 '더블 클릭' 느낌 제거
        self.widget.mousePressEvent = self._on_clicked
        self.widget.mouseReleaseEvent = lambda e: None
        
    def _on_clicked(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # 1. 액션 트리거
            self.trigger()
            
            # 2. 메뉴 찾기 및 즉시 닫기
            p = self.parent()
            while p and not isinstance(p, QMenu):
                p = p.parent()
            if p:
                p.close()
                p.hide()

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
        self.label.setStyleSheet(f"color: white; font-weight: bold; font-size: {int(16*s)}px; border: none; background: transparent; font-family: '{config.FONT_MAIN}', 'Audiowide'; letter-spacing: 1px;")
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
                    font-family: '{config.FONT_MAIN}';
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
            lbl.setStyleSheet(f"color: rgba(0, 255, 255, 180); font-size: {int(12*s)}px; border: none; font-family: '{config.FONT_MAIN}', 'Michroma'; letter-spacing: 1px; background: transparent;")
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
        self.setObjectName("ControlPanel")
        self.init_ui()

    def update_scaling(self, scale):
        """실시간 크기 조절 대응"""
        self.current_scale = scale
        is_micro = scale < 0.6
        base_font_size = max(10, int(15 * scale))
        
        font = QFont(config.FONT_MAIN)
        font.setPixelSize(base_font_size)
        font.setBold(True)
        # 폰트 굵기 명시적 강화 (GIANTS 브랜드 특성 반영)
        font.setWeight(QFont.Weight.ExtraBold)
        
        self.mode_btn.setFont(font)
        self.toggle_button.setFont(font)
        
        btn_h = max(35, int(65 * scale))
        self.mode_btn.setFixedHeight(btn_h)
        self.toggle_button.setFixedHeight(btn_h)
        
        min_w = 40 if is_micro else 250
        self.mode_btn.setMinimumWidth(min_w)
        self.toggle_button.setMinimumWidth(min_w)
        
        # 패딩 축소로 더 많은 공간 확보
        padding_h = 2 if is_micro else 15
        self.mode_btn.setStyleSheet(self.mode_btn.styleSheet().replace(
            "padding: 1px 15px;", f"padding: 1px {padding_h}px;"
        ))
        
        # Menu font scaling
        view_font = QFont(config.FONT_MAIN, base_font_size)
        view_font.setWeight(QFont.Weight.Bold)
        self.mode_menu.setFont(view_font)

    def init_ui(self):
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(30, 15, 30, 15)
        layout.setSpacing(30)

        self.setStyleSheet(f"""
            #ControlPanel {{
                background-color: rgba(20, 20, 30, 210);
                border: 1px solid rgba(0, 255, 255, 60);
                border-radius: 20px;
                font-family: '{config.FONT_MAIN}', sans-serif;
            }}
        """)

        # 1. 모드 선택 버튼 + 메뉴
        self.mode_btn = QPushButton("게임 모드 🎮")
        self.mode_btn.setFixedHeight(65)
        self.mode_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.mode_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Create Menu
        self.mode_menu = QMenu(self)
        self.mode_menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        modes = [
            ("PPT 모드 📑", "PPT"),
            ("Youtube/Media 📺", "YOUTUBE"),
            ("게임 모드 🎮", "GAME")
        ]
        
        for label, code in modes:
            action = CenteredMenuAction(label, code, self.mode_menu)
            action.triggered.connect(lambda checked=False, l=label, c=code: self._on_mode_select(l, c))
            self.mode_menu.addAction(action)
            
        # Instead of setMenu (which anchors to left), we manually show it centered
        self.mode_btn.clicked.connect(self._show_mode_menu)
        
        self.mode_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 15);
                color: white;
                border: 1px solid rgba(0, 255, 255, 50);
                border-radius: 8px;
                padding: 1px 15px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: rgba(0, 255, 255, 30);
                border: 2px solid #00FFFF;
            }
            QPushButton::menu-indicator { image: none; }
        """)
        
        self.mode_menu.setStyleSheet("""
            QMenu {
                background-color: #101020;
                color: white;
                border: 1px solid #00FFFF;
                padding: 10px;
            }
            QMenu::item {
                padding: 12px 25px;
                margin: 4px 0px;
                border-radius: 8px;
                min-width: 150px;
            }
            QMenu::item:selected {
                background-color: rgba(0, 255, 255, 40);
                color: #00FFFF;
            }
        """)
        
        layout.addWidget(self.mode_btn)

        # 2. 토글 버튼 (시작/중지)
        self.toggle_button = QPushButton("동작 감지 시작")
        self.toggle_button.setFixedHeight(65)
        self.toggle_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        self._update_toggle_style(False) 
        self.toggle_button.clicked.connect(self.toggle_clicked.emit)
        layout.addWidget(self.toggle_button)

    def _on_mode_select(self, label, code):
        play_ui_click()
        self.mode_btn.setText(label)
        self.mode_changed.emit(code)

    def _show_mode_menu(self):
        """메뉴를 버튼의 수평 중앙에 맞춰서 표시"""
        # 버튼의 최신 전역 위치 계산
        self.mode_menu.adjustSize()
        
        # 버튼 위치 재계산 (현재 상태 반영)
        btn_pos = self.mode_btn.mapToGlobal(QPoint(0, 0))
        
        # 중앙 정렬 X 좌표 계산: (버튼 중앙) - (메뉴 너비 / 2)
        x = btn_pos.x() + (self.mode_btn.width() - self.mode_menu.width()) // 2
        
        # 버튼 상단에 띄울지 하단에 띄울지 결정 (화면 공간 고려)
        # 기본은 하단 (+5px)
        y = btn_pos.y() + self.mode_btn.height() + 5
        
        # 만약 아래쪽에 공간이 부족하면 위쪽으로 표시
        screen = self.screen().availableGeometry()
        if y + self.mode_menu.height() > screen.bottom():
            y = btn_pos.y() - self.mode_menu.height() - 5
            
        self.mode_menu.exec(QPoint(x, y))

    def _on_mode_combo_changed(self, index):
        play_ui_click()
        mode_str = self.mode_map.get(index, "GAME")
        self.mode_changed.emit(mode_str)
        self.mode_combo.clearFocus() 
        self.setFocus()

    def _show_sensitivity_popover(self):
        """No longer used in HUD panel, moved to Settings"""
        pass
        
    def _on_popover_value(self, val):
        self.sensitivity_value = val
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
        
        base_font_size = max(10, int(15 * self.current_scale))
        self.toggle_button.setFont(QFont(config.FONT_MAIN, base_font_size, QFont.Weight.Bold))
