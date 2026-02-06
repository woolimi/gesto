"""
main_window.py
메인 윈도우 (UI 전용) - V4 Design
Frameless window with custom top bar, AR-style layout, and Chroma aesthetics.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QSizePolicy, QSizeGrip,
    QDialog, QComboBox, QFormLayout, QApplication, QSlider,
    QGraphicsOpacityEffect, QMenu, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRectF, QEvent, QSize, QTimer
from PyQt6.QtGui import QColor, QFont, QFontDatabase, QPixmap, QAction, QIcon

import config
from app.widgets import LogoWidget, WebcamPanelWidget, ControlPanelWidget
from app.widgets.animated_background import AuroraGradientBackground
from app.widgets.accuracy_gauge import AccuracyGauge
from app.widgets.gesture_display import GestureDisplayWidget
from app.workers.sound_worker import play_ui_click


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setWindowTitle("설정")
        # Aggressively enlarged from 500x650
        self.setFixedSize(650, 850)
        
        if parent:
            parent_geo = parent.geometry()
            self.move(
                parent_geo.center().x() - self.width() // 2,
                parent_geo.center().y() - self.height() // 2
            )
        self.setStyleSheet("""
            QDialog {
                background-color: #101025;
                color: white;
                border: 1px solid #00FFFF;
                border-radius: 10px;
                font-family: 'Giants Inline', 'Michroma', sans-serif;
            }
            QLabel { color: #CCCCCC; font-size: 18px; font-family: '{config.FONT_MAIN}', 'Michroma', sans-serif; }
            QComboBox {
                background-color: rgba(255, 255, 255, 20);
                color: white;
                border: 1px solid rgba(0, 255, 255, 50);
                padding: 5px;
                border-radius: 5px;
                font-family: '{config.FONT_MAIN}', 'Michroma', sans-serif;
            }
            QComboBox QAbstractItemView {
                background-color: #101020;
                color: white;
                selection-background-color: #00FFFF;
                selection-color: black;
                font-family: '{config.FONT_MAIN}', 'Michroma', sans-serif;
            }
            QPushButton {
                 background-color: rgba(0, 255, 255, 30);
                 color: #00FFFF;
                 border: 1px solid #00FFFF;
                 padding: 8px;
                 border-radius: 5px;
                 font-family: 'Giants Inline', 'Audiowide', sans-serif;
                 letter-spacing: 2px;
                 text-transform: uppercase;
             }
            QPushButton:hover {
                background-color: rgba(0, 255, 255, 60);
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Header
        header = QLabel("시스템 설정")
        header.setStyleSheet(f"font-size: 26px; font-weight: bold; color: #00FFFF; font-family: '{config.FONT_MAIN}', 'Audiowide', sans-serif; letter-spacing: 5px;")
        layout.addWidget(header)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        
        self.combo_res = QComboBox()
        self.combo_res.addItems(["1280x720 (기본)", "1920x1080", "800x600"])
        form_layout.addRow("창 크기:", self.combo_res)
        
        self.combo_cam = QComboBox()
        self.combo_cam.addItems(["기본 카메라 (0)", "외부 카메라 (1)"])
        form_layout.addRow("카메라 소스:", self.combo_cam)
        
        layout.addLayout(form_layout)
        
        res_label = QLabel("해상도 강제 설정:")
        res_label.setStyleSheet(f"color: #00FFFF; font-weight: bold; margin-top: 10px; font-family: '{config.FONT_MAIN}', sans-serif;")
        layout.addWidget(res_label)
        
        res_grid = QGridLayout()
        res_grid.setSpacing(10)
        
        specs = [
            ("512x720 (모바일)", 512, 720),
            ("768x1080 (세로 모드)", 768, 1080),
            ("800x600 (클래식)", 800, 600),
            ("1024x768 (태블릿)", 1024, 768),
            ("1280x720 (HD)", 1280, 720),
            ("1920x1080 (FHD)", 1920, 1080)
        ]
        
        for i, (name, w, h) in enumerate(specs):
            btn = QPushButton(name)
            btn.setFixedHeight(50) 
            btn.setStyleSheet("""
                QPushButton {
                    font-size: 16px; 
                    padding: 10px;
                    background-color: rgba(255, 255, 255, 15);
                    border: 2px solid rgba(0, 255, 255, 60);
                    border-radius: 8px;
                    color: white;
                    font-weight: bold;
                    font-family: '{config.FONT_MAIN}', sans-serif;
                }
                QPushButton:hover {
                    background-color: rgba(0, 255, 255, 50);
                    border: 2px solid #00FFFF;
                }
            """)
            btn.clicked.connect(play_ui_click)
            btn.clicked.connect(lambda checked, w=w, h=h: self._set_resolution(w, h))
            res_grid.addWidget(btn, i // 2, i % 2)
            
        layout.addLayout(res_grid)
        
        # Sensitivity Adjustment
        layout.addSpacing(10)
        sens_label = QLabel("인식 감도 조절:")
        sens_label.setStyleSheet(f"color: {config.COLOR_PRIMARY}; font-weight: bold; font-family: '{config.FONT_MAIN}';")
        layout.addWidget(sens_label)
        
        sens_container = QHBoxLayout()
        self.slider_sens = QSlider(Qt.Orientation.Horizontal)
        self.slider_sens.setRange(0, 100)
        self.slider_sens.setValue(parent.sensitivity if parent else 50)
        self.slider_sens.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                border: 1px solid rgba(255, 255, 255, 50);
                height: 10px;
                background: rgba(0, 0, 0, 100);
                border-radius: 5px;
            }}
            QSlider::handle:horizontal {{
                background: {config.COLOR_PRIMARY};
                border: 1px solid white;
                width: 20px;
                margin: -6px 0;
                border-radius: 10px;
            }}
        """)
        
        self.lbl_sens_val = QLabel(f"{self.slider_sens.value()}%")
        self.lbl_sens_val.setFixedWidth(50)
        self.lbl_sens_val.setStyleSheet(f"color: white; font-weight: bold; font-family: '{config.FONT_MAIN}';")
        
        self.slider_sens.valueChanged.connect(lambda v: self.lbl_sens_val.setText(f"{v}%"))
        self.slider_sens.valueChanged.connect(lambda v: parent.on_sensitivity_changed(v) if parent else None)
        
        sens_container.addWidget(self.slider_sens)
        sens_container.addWidget(self.lbl_sens_val)
        layout.addLayout(sens_container)
        
        layout.addStretch()
        
        btn_close = QPushButton("닫기")
        btn_close.setStyleSheet(f"font-family: '{config.FONT_MAIN}', sans-serif; font-size: 14px; font-weight: bold;")
        btn_close.clicked.connect(play_ui_click)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def _set_resolution(self, w, h):
        parent = self.parent()
        if parent:
            if parent.isMaximized():
                parent.showNormal()
                
            screen = QApplication.primaryScreen()
            if screen:
                avail = screen.availableSize()
                w = min(w, avail.width())
                h = min(h, avail.height())
            parent.resize(w, h)
            self.accept()

class CustomTopBar(QWidget):
    settings_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(50)
        self.init_ui()


    def btn_min_clicked(self):
        self.window().showMinimized()

    def btn_max_clicked(self):
        self.toggle_maximize()

    def btn_close_clicked(self):
        self.window().close()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        
        self.title_label = QLabel("GESTO")
        self.title_label.setStyleSheet(f"color: {config.COLOR_PRIMARY}; font-size: 24px; font-weight: bold; font-family: '{config.FONT_MAIN}'; letter-spacing: 6px; background: transparent;")
        layout.addWidget(self.title_label)
        
        layout.addStretch()
        
        # Centered Gesture Label
        self.gesture_label = QLabel("")
        self.gesture_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.gesture_label.setStyleSheet(f"""
            color: #FFFF00;
            font-family: '{config.FONT_MAIN}', sans-serif;
            font-size: 18px;
            font-weight: 800;
            letter-spacing: 2px;
            background: rgba(0, 0, 0, 80);
            border: 1px solid rgba(255, 255, 0, 100);
            border-radius: 12px;
            padding: 5px 25px;
        """)
        self.gesture_label.setVisible(False)
        layout.addWidget(self.gesture_label)
        
        # Managed timer for hiding gesture text (prevents flickering)
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(lambda: self.gesture_label.setVisible(False))
        
        layout.addStretch()
        
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: #00FF00; font-size: 10px; background: transparent;")
        self.status_text = QLabel("상태: 준비됨")
        self.status_text.setStyleSheet(f"color: #00FFFF; font-size: 13px; margin-left: 5px; font-family: '{config.FONT_MAIN}'; letter-spacing: 2px; font-weight: bold; background: transparent;")
        
        status_container = QWidget()
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(8, 4, 12, 4)
        status_layout.addWidget(self.status_dot)
        status_layout.addWidget(self.status_text)
        # Transparent background and no border for a cleaner look
        status_container.setStyleSheet("background-color: transparent; border: none;")
        layout.addWidget(status_container)
        
        # Always on Top Indicator
        self.aot_container = QWidget()
        aot_layout = QHBoxLayout(self.aot_container)
        aot_layout.setContentsMargins(8, 4, 8, 4)
        self.aot_label = QLabel("고정")
        self.aot_label.setStyleSheet(f"color: #FF00FF; font-size: 11px; font-weight: bold; font-family: '{config.FONT_MAIN}', sans-serif;")
        aot_layout.addWidget(self.aot_label)
        self.aot_container.setStyleSheet("background-color: transparent; border: none;")
        self.aot_container.setVisible(False)
        layout.addWidget(self.aot_container)
        
        layout.addSpacing(20)
        
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)
        
        self.btn_settings = QPushButton("⚙")
        self.btn_settings.setFixedSize(30, 30)
        self.btn_settings.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.style_nav_btn(self.btn_settings, color="#00FFFF")
        self.btn_settings.clicked.connect(self.settings_clicked.emit)
        controls_layout.addWidget(self.btn_settings)

        self.btn_min = QPushButton("─")
        self.btn_min.setFixedSize(30, 30)
        self.btn_min.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.style_nav_btn(self.btn_min)
        self.btn_min.clicked.connect(self.window().showMinimized)
        controls_layout.addWidget(self.btn_min)
        
        self.btn_max = QPushButton("☐")
        self.btn_max.setFixedSize(30, 30)
        self.btn_max.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.style_nav_btn(self.btn_max)
        self.btn_max.clicked.connect(self.toggle_maximize)
        controls_layout.addWidget(self.btn_max)
        
        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.style_nav_btn(self.btn_close, hover_color="rgba(255, 255, 255, 0.5)")
        self.btn_close.clicked.connect(self.window().close)
        controls_layout.addWidget(self.btn_close)
        
        layout.addLayout(controls_layout)

    def style_nav_btn(self, btn, color="rgba(255, 255, 255, 0.7)", hover_color="rgba(255, 255, 255, 0.2)"):
        btn.setStyleSheet(f"""
            QPushButton {{
                color: {color};
                background: transparent;
                border: none;
                font-family: '{config.FONT_MAIN}', sans-serif;
                font-weight: bold;
            }}
            QPushButton:hover {{
                color: white;
                background-color: {hover_color};
                border-radius: 20px;
            }}
        """)

    def toggle_maximize(self):
        win = self.window()
        if win.isMaximized():
            win.showNormal()
        else:
            win.showMaximized()
        if hasattr(win, '_apply_dynamic_scaling'):
            win._apply_dynamic_scaling(win.width(), win.height())

    def set_status(self, is_detecting: bool, mode: str):
        mode_text = f"({mode})" if mode else ""
        if is_detecting:
            self.status_dot.setStyleSheet("color: #00FFFF; background: transparent;") 
            self.status_text.setText(f"감지 중 {mode_text}")
        else:
            self.status_dot.setStyleSheet("color: #555555; background: transparent;")
            self.status_text.setText(f"대기 중 {mode_text}")

    def update_gesture(self, text, visible=True):
        """중앙 제스처 텍스트 업데이트 (타이머 관리 포함)"""
        if not text:
            self.gesture_label.setVisible(False)
            return

        display_text = config.GESTURE_DISPLAY_MAP.get(text, text)
        self.gesture_label.setText(display_text)
        self.gesture_label.setVisible(visible)
        
        # Restart timer every time a gesture is detected
        if visible:
            self.hide_timer.start(2500) 

    def set_aot(self, enabled: bool):
        """Always on Top 활성화 상태 표시기 업데이트"""
        self.aot_container.setVisible(enabled)
            
class MainWindow(QMainWindow):
    start_detection = pyqtSignal()
    stop_detection = pyqtSignal()
    sensitivity_changed = pyqtSignal(int)
    mode_changed = pyqtSignal(str)
    toggle_detection_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.current_mode = "GAME"
        self.sensitivity = config.SENSITIVITY_DEFAULT
        self.is_detecting = False
        
        self._dragging = False
        self._resizing = False
        self._start_geometry = None
        self._start_mouse_pos = None
        self._normal_size = QSize(800, 600) 
        self._drag_pos = None
        self._edge = None

        self._last_scale = 0.0
        
        self.background_animation = AuroraGradientBackground(self)
        self.background_animation.resize(self.size())
        
        self.setMouseTracking(True) 

        self.init_ui()

        self.control_panel.mode_changed.connect(self.on_mode_changed)
        self.control_panel.sensitivity_changed.connect(self.on_sensitivity_changed)
        self.control_panel.toggle_clicked.connect(self.on_toggle_clicked)
        self.top_bar.settings_clicked.connect(self.open_settings)
        
        self.on_mode_changed(self.current_mode) 
        # Label update no longer needed in bottom panel
        # self.control_panel.set_sensitivity_label(self.sensitivity)
        self.top_bar.set_status(False, self.current_mode)
        is_on_top = bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        self.top_bar.set_aot(is_on_top)

    def init_ui(self):
        self.setWindowTitle(config.WINDOW_TITLE)
        
        self.resize(1100, 950)
        self.setMinimumSize(100, 100)
        
        screen = QApplication.primaryScreen()
        if screen:
            self.setMaximumSize(screen.availableSize())
            
        self._normal_size = self.size()
        self.background_animation.raise_()
        self.background_animation.stackUnder(self.centralWidget() if self.centralWidget() else self)
        
        screen_geo = self.screen().availableGeometry()
        w, h = self.width(), self.height()
        self.move(
            screen_geo.x() + (screen_geo.width() - w) // 2,
            screen_geo.y() + (screen_geo.height() - h) // 2
        )
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        QApplication.instance().installEventFilter(self)
        self.setMouseTracking(True)
        
        central_widget = QWidget()
        central_widget.setObjectName("CentralWidget")
        central_widget.setMouseTracking(True) 
        central_widget.setStyleSheet(f"""
            #CentralWidget {{
                background: rgba(10, 10, 25, 140);
                border: 1px solid rgba(0, 255, 255, 0.4);
                border-radius: 10px;
            }}
        """)
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 1. Top Bar
        self.top_bar = CustomTopBar(self)
        self.top_bar.setFixedHeight(45) 
        main_layout.addWidget(self.top_bar)
        
        self.div_top = QFrame()
        self.div_top.setFrameShape(QFrame.Shape.HLine)
        self.div_top.setFrameShadow(QFrame.Shadow.Sunken)
        self.div_top.setStyleSheet("background-color: rgba(255, 255, 255, 20); min-height: 1px;")
        main_layout.addWidget(self.div_top)
        
        main_layout.addSpacing(5) 
        
        # Content Layout
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 5, 20, 10) 
        content_layout.setSpacing(5) 

        # 2. Camera Panel (AR View)
        self.webcam_panel = WebcamPanelWidget()
        content_layout.addWidget(self.webcam_panel, 15) 
        
        # 3. Accuracy Gauge
        gauge_container = QHBoxLayout()
        gauge_container.addStretch()
        self.accuracy_gauge = AccuracyGauge()
        gauge_container.addWidget(self.accuracy_gauge)
        gauge_container.addStretch()
        content_layout.addLayout(gauge_container, 5) 
        
        self.div_bottom = QFrame()
        self.div_bottom.setFrameShape(QFrame.Shape.HLine)
        self.div_bottom.setFrameShadow(QFrame.Shadow.Sunken)
        self.div_bottom.setStyleSheet("background-color: rgba(255, 255, 255, 20); min-height: 1px;")
        content_layout.addWidget(self.div_bottom)
        
        # 4. Control Panel - Fixed Height
        self.control_panel = ControlPanelWidget()
        self.control_panel.setFixedHeight(110) 
        content_layout.addWidget(self.control_panel)
        
        content_layout.addSpacing(10)
        
        main_layout.addLayout(content_layout)
        
        self.size_grip = QSizeGrip(self)
        self.size_grip.setStyleSheet("width: 20px; height: 20px; background: transparent;")
        self.size_grip.resize(20, 20)

    def open_settings(self):
        play_ui_click()
        if not hasattr(self, "_settings_dialog") or self._settings_dialog is None:
            self._settings_dialog = SettingsDialog(self)
        self._center_settings_dialog()
        self._settings_dialog.show()

    def _center_settings_dialog(self):
        if hasattr(self, "_settings_dialog") and self._settings_dialog:
            parent_geo = self.geometry()
            self._settings_dialog.move(
                parent_geo.center().x() - self._settings_dialog.width() // 2,
                parent_geo.center().y() - self._settings_dialog.height() // 2
            )

    def moveEvent(self, event):
        super().moveEvent(event)
        self._center_settings_dialog()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        
        if hasattr(self, 'background_animation'):
             self.background_animation.setGeometry(self.rect())
            
        self._apply_dynamic_scaling(self.width(), self.height())
            
        if not self.isMaximized():
            self._normal_size = self.size()
        self._center_settings_dialog()

    def _apply_dynamic_scaling(self, w, h):
        """UI 요소 스케일링 엔진 (캐싱 적용)"""
        scale_w = w / 1000.0
        scale_h = h / 900.0
        scale = min(scale_w, scale_h)
        
        # 중복 호출 방지를 위한 스케일 체크
        if abs(scale - self._last_scale) < 0.005: 
            return
        self._last_scale = scale
        
        # 1. Scale Top Bar
        # 1. Scale Top Bar
        if hasattr(self, 'top_bar'):
            tb = self.top_bar
            # Slimmed down from 100 to 55 to maximize camera space
            tb_h = max(35, int(55 * scale)) 
            tb.setFixedHeight(tb_h)
            
            # Micro-Mode: Hide labels but KEEP LED dot for status feedback
            is_micro = scale < 0.6
            tb.title_label.setVisible(not is_micro)
            tb.status_text.setVisible(not is_micro)
            # tb.status_dot remains visible as per user request
            tb.status_dot.setVisible(True)
            
            # Use same visibility logic for AOT container
            is_on_top = bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
            tb.aot_container.setVisible(is_on_top and not is_micro)
            
            # FAST: Use setFont instead of setStyleSheet during resize
            if not is_micro:
                logo_font = QFont("Ubuntu Sans")
                logo_font.setPixelSize(max(20, int(45 * scale)))
                logo_font.setBold(True)
                logo_font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 140) 
                tb.title_label.setFont(logo_font)
                
                status_font = QFont("NanumSquareRound")
                status_font.setPixelSize(max(16, int(26 * scale)))
                status_font.setBold(True)
                status_font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 105)
                tb.status_text.setFont(status_font)
                
                aot_font = QFont("NanumSquareRound")
                aot_font.setPixelSize(max(16, int(26 * scale)))
                aot_font.setBold(True)
                tb.aot_label.setFont(aot_font)
                
                # Use faster update for container and spacing too
                tb.aot_container.setMinimumWidth(int(80 * scale))
            else:
                # Micro-mode: Adjust dot font size and container to be compact
                tb.status_dot.setFont(QFont("Audiowide", 14, QFont.Weight.Bold))
                tb.status_dot.setContentsMargins(0, 0, 0, 0)
                # find container (parent of status_dot) and shrink it
                container = tb.status_dot.parentWidget()
                if container:
                    container.setStyleSheet("background: transparent; border: none; padding: 0px;")
                    container.layout().setContentsMargins(0, 0, 0, 0)
            
            # Aggressively enlarge top bar buttons as per user request
            btn_size = max(30, int(45 * scale))
            for btn in [tb.btn_settings, tb.btn_min, tb.btn_max, tb.btn_close]:
                btn.setFixedSize(btn_size, btn_size)
                # 아이콘 크기를 버튼 크기의 70% 정도로 대폭 상향 (고해상도 대응)
                current_font = btn.font()
                current_font.setPixelSize(int(btn_size * 0.7)) 
                btn.setFont(current_font)
                
            m = 0 if is_micro else int(15*scale)
            tb.layout().setContentsMargins(m, 0, m, 0)
            tb.layout().setSpacing(2 if is_micro else int(5*scale))

        # 2. Scale Separator Lines (Thickness)
        thickness = max(1, int(1 * scale))
        if hasattr(self, 'div_top'): self.div_top.setFixedHeight(thickness)
        if hasattr(self, 'div_bottom'): self.div_bottom.setFixedHeight(thickness)

        # 3. Scale Accuracy Gauge container height
        if hasattr(self, 'accuracy_gauge'):
             self.accuracy_gauge.setMinimumHeight(int(80 * scale))

        # 4. Scale Control Panel
        if hasattr(self, 'control_panel'):
            cp = self.control_panel
            is_micro = scale < 0.6
            cp.update_scaling(scale) 
            
            # Modified: Keep all elements visible in micro mode
            if is_micro:
                cp.mode_btn.show() # Keep it visible as per user request
                cp.toggle_button.setText("") 
                cp.toggle_button.setIcon(QApplication.style().standardIcon(QApplication.style().StandardPixmap.SP_MediaPlay if not self.is_detecting else QApplication.style().StandardPixmap.SP_MediaStop))
            else:
                cp.mode_btn.show()
                cp.toggle_button.setIcon(QIcon())
                cp.set_detection_state(self.is_detecting)
                
            cp.setFixedHeight(max(35, int(90 * scale)))
            
            m = 2 if is_micro else int(10*scale)
            cp.layout().setContentsMargins(m, 2, m, 2)
            cp.layout().setSpacing(2 if is_micro else int(8*scale))

        # 6. Global Margins (Central Widget)
        if hasattr(self, 'centralWidget') and self.centralWidget() and self.centralWidget().layout():
            m = max(2, int(10 * scale)) # Reduced padding
            self.centralWidget().layout().setContentsMargins(m, m, m, m)
            self.centralWidget().layout().setSpacing(0) # No spacing between blocks, separators handle it

    # --- Event Filter for Robust Resizing & Dragging ---
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseMove:
            global_pos = event.globalPosition().toPoint()
            
            if self._resizing:
                self._resize_window(global_pos)
                return True
            
            widget = QApplication.widgetAt(global_pos)
            is_interactive = False
            if widget:
                from PyQt6.QtWidgets import QAbstractItemView
                targets = (QPushButton, QComboBox, QSlider, QAbstractItemView)
                if isinstance(widget, targets) or (widget.parent() and isinstance(widget.parent(), targets)):
                    is_interactive = True

            if is_interactive:
                if self.cursor().shape() != Qt.CursorShape.ArrowCursor:
                    self.setCursor(Qt.CursorShape.ArrowCursor)
                self._edge = None
                return super().eventFilter(obj, event)

            if event.buttons() & Qt.MouseButton.LeftButton and self._drag_pos is not None:
                if self.isMaximized():
                    old_w = self.width()
                    mouse_x = self.mapFromGlobal(global_pos).x()
                    rel_x = mouse_x / old_w if old_w > 0 else 0.5
                    
                    self.showNormal()
                    self.resize(self._normal_size)
                    QApplication.processEvents() 
                    
                    new_w = self._normal_size.width()
                    drag_y = self._drag_pos.y()
                    self._drag_pos = QPoint(int(new_w * rel_x), drag_y)
                
                self.move(global_pos - self._drag_pos)
                return True

            if not self.isMaximized():
                local_pos = self.mapFromGlobal(global_pos)
                self._update_cursor(local_pos)
            else:
                if self.cursor().shape() != Qt.CursorShape.ArrowCursor:
                    self.setCursor(Qt.CursorShape.ArrowCursor)
            
        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                global_pt = event.globalPosition().toPoint()
                widget = QApplication.widgetAt(global_pt)
                
                if hasattr(self, "_settings_dialog") and self._settings_dialog and self._settings_dialog.isVisible():
                    if not self._settings_dialog.geometry().contains(global_pt):
                        self._settings_dialog.close()
                
                is_interactive = False
                if widget:
                    from PyQt6.QtWidgets import QAbstractItemView
                    targets = (QPushButton, QComboBox, QSlider, QAbstractItemView)
                    if isinstance(widget, targets) or (widget.parent() and isinstance(widget.parent(), targets)):
                        is_interactive = True

                if is_interactive:
                    return super().eventFilter(obj, event)
                
                if self._edge:
                    self._resizing = True
                    self._start_geometry = self.geometry()
                    self._start_mouse_pos = event.globalPosition().toPoint()
                    return True 
                
                is_draggable = False
                if obj == self.top_bar or (widget and self.top_bar.isAncestorOf(widget)):
                    is_draggable = True
                elif obj == self or obj == self.centralWidget():
                    is_draggable = True
                
                if is_draggable:
                     # Standardize on _drag_pos to match MouseMove logic
                     self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                     return True
            
        elif event.type() == QEvent.Type.MouseButtonDblClick:
            if event.button() == Qt.MouseButton.LeftButton:
                widget = QApplication.widgetAt(event.globalPosition().toPoint())
                
                is_interactive = False
                if widget:
                    from PyQt6.QtWidgets import QAbstractItemView
                    targets = (QPushButton, QComboBox, QSlider, QAbstractItemView)
                    if isinstance(widget, targets) or (widget.parent() and isinstance(widget.parent(), targets)):
                        is_interactive = True
                
                if is_interactive:
                    return super().eventFilter(obj, event)
                
                if obj == self.top_bar or (widget and self.top_bar.isAncestorOf(widget)):
                    self.top_bar.toggle_maximize()
                    return True

        elif event.type() == QEvent.Type.MouseButtonRelease:
            if self._resizing:
                self._resizing = False
                self._edge = None
                self._start_geometry = None
                self.setCursor(Qt.CursorShape.ArrowCursor)
                return True 
            
            self._resizing = False
            self._drag_pos = None

        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)

    def _update_cursor(self, pos):
        margin = 6 
        w, h = self.width(), self.height()
        self._edge = None
        
        left = pos.x() < margin
        right = pos.x() > w - margin
        top = pos.y() < margin
        bottom = pos.y() > h - margin
        
        cursor = Qt.CursorShape.ArrowCursor
        
        if top and left: self._edge = "TL"; cursor = Qt.CursorShape.SizeFDiagCursor
        elif top and right: self._edge = "TR"; cursor = Qt.CursorShape.SizeBDiagCursor
        elif bottom and left: self._edge = "BL"; cursor = Qt.CursorShape.SizeBDiagCursor
        elif bottom and right: self._edge = "BR"; cursor = Qt.CursorShape.SizeFDiagCursor
        elif left: self._edge = "L"; cursor = Qt.CursorShape.SizeHorCursor
        elif right: self._edge = "R"; cursor = Qt.CursorShape.SizeHorCursor
        elif top: self._edge = "T"; cursor = Qt.CursorShape.SizeVerCursor
        elif bottom: self._edge = "B"; cursor = Qt.CursorShape.SizeVerCursor
        
        if self.cursor().shape() != cursor:
            self.setCursor(cursor)

    def contextMenuEvent(self, event):
        context_menu = QMenu(self)
        context_menu.setStyleSheet("""
            QMenu {
                background-color: #1A1A2E;
                color: #00FFFF;
                border: 1px solid #00FFFF;
                font-family: 'Inter', 'Noto Sans KR';
            }
            QMenu::item:selected {
                background-color: #0F3460;
            }
        """)
        
        is_on_top = bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        action_top = QAction("항상 위에" if not is_on_top else "✓ 항상 위에", self)
        action_top.triggered.connect(self.toggle_always_on_top)
        context_menu.addAction(action_top)
        
        context_menu.exec(event.globalPos())

    def set_always_on_top(self, enable: bool):
        is_currently_on_top = bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        is_currently_ghost = bool(self.windowFlags() & Qt.WindowType.WindowDoesNotAcceptFocus)
        
        # PPT 모드에서 AOT를 켤 때만 '포커스 비수용(Ghost)' 모드 적용
        target_ghost = enable and self.current_mode == "PPT"
        
        if enable == is_currently_on_top and target_ghost == is_currently_ghost:
            return
            
        self.hide()
        flags = self.windowFlags()
        
        if enable:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
            
        if target_ghost:
            flags |= Qt.WindowType.WindowDoesNotAcceptFocus
        else:
            flags &= ~Qt.WindowType.WindowDoesNotAcceptFocus
            
        self.setWindowFlags(flags)
        self.show()
        
        if enable:
            self.raise_()
            if not target_ghost:
                self.activateWindow()
        
        # Update UI Indicator
        self.top_bar.set_aot(enable)
        
        # PPT 모드일 때만 다른 창 뒤로 완전히 숨기기 처리
        if not enable and self.current_mode == "PPT":
            self.lower()
            self.clearFocus()

    def toggle_always_on_top(self):
        is_on_top = bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        self.set_always_on_top(not is_on_top)

    def _resize_window(self, global_pos):
        if not self._edge or not self._start_geometry: return
        
        diff = global_pos - self._start_mouse_pos
        curr_geo = self._start_geometry
        new_geo = QRectF(curr_geo).toRect() 
        
        min_w, min_h = self.minimumWidth(), self.minimumHeight()
        
        if "R" in self._edge:
            new_geo.setWidth(max(min_w, curr_geo.width() + diff.x()))
        if "B" in self._edge:
            new_geo.setHeight(max(min_h, curr_geo.height() + diff.y()))
        if "L" in self._edge:
            new_w = max(min_w, curr_geo.width() - diff.x())
            if new_w != curr_geo.width():
               new_geo.setX(curr_geo.x() + (curr_geo.width() - new_w))
               new_geo.setWidth(new_w)
        if "T" in self._edge:
            new_h = max(min_h, curr_geo.height() - diff.y())
            if new_h != curr_geo.height():
               new_geo.setY(curr_geo.y() + (curr_geo.height() - new_h))
               new_geo.setHeight(new_h)
               
        self.setGeometry(new_geo)
    
    def set_detection_state(self, is_active: bool):
        self.is_detecting = is_active
        self.control_panel.set_detection_state(is_active)
        self.webcam_panel.set_recording(is_active)
        
        self.top_bar.set_status(is_active, self.current_mode)
        if is_active:
            self.top_bar.update_gesture("AR 추적 활성화됨")
        else:
            self.top_bar.update_gesture("대기 중")
        
        if is_active:
            self.start_detection.emit()
        else:
            self.stop_detection.emit()

    def on_toggle_clicked(self):
        self.toggle_detection_requested.emit()

    def on_sensitivity_changed(self, value: int):
        self.sensitivity = value
        self.control_panel.set_sensitivity_label(value)
        self.webcam_panel.gesture_display.set_threshold(
            config.sensitivity_to_confidence_threshold(value)
        )
        self.sensitivity_changed.emit(value)

    def on_mode_changed(self, mode: str):
        self.current_mode = mode
        self.mode_changed.emit(mode)
        
        # Sync TriggerWorker mode
        if hasattr(self, 'trigger_worker'):
            self.trigger_worker.set_current_mode(mode)
            
        self.top_bar.set_status(self.is_detecting, mode)
        
        # 모드 변경 시 '항상 위에'의 Ghost 모드 상태 업데이트 (PPT <-> Other 대응)
        is_on_top = bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        if is_on_top:
            self.set_always_on_top(True)

    def update_webcam_frame(self, pixmap):
        if not pixmap or pixmap.isNull(): return
        
        lbl = self.webcam_panel.webcam_label
        label_size = lbl.size()
        
        if label_size.width() > 0 and label_size.height() > 0:
            scaled_pixmap = pixmap.scaled(
                label_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation
            )
            lbl.setPixmap(scaled_pixmap)
            if lbl.text(): lbl.setText("")


    def update_gesture(self, gesture_name: str, confidence: float = 0.0, cooldown_until: float = 0.0):
        # 제스처 정보를 UI/게이지에 전달
        if self.is_detecting and gesture_name:
             self.accuracy_gauge.set_accuracy(int(confidence * 100))
        else:
             self.accuracy_gauge.set_accuracy(0)

        if self.is_detecting:
            if gesture_name: self.top_bar.update_gesture(gesture_name)
