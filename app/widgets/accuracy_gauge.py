"""
accuracy_gauge.py
인식 정확도 게이지 위젯
"""

from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtCore import Qt, QRectF, QTimer, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QConicalGradient

class AccuracyGauge(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.accuracy = 0
        self._target_accuracy = 0.0
        self._display_accuracy = 0.0
        
        self.setMinimumSize(10, 10) 
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16) 
        self._anim_timer.timeout.connect(self._animate_step)
        
        self._hold_timer = QTimer(self)
        self._hold_timer.setSingleShot(True)
        self._hold_timer.timeout.connect(self._reset_value)
        self._is_holding = False

    def set_accuracy(self, value: int):
        if value > 0:
            self._target_accuracy = float(value)
            self._is_holding = True
            self._hold_timer.start(2000)
            if not self._anim_timer.isActive():
                self._anim_timer.start()
        else:
            if not self._is_holding:
                self._target_accuracy = 0.0
                if not self._anim_timer.isActive():
                    self._anim_timer.start()

    def _reset_value(self):
        self._is_holding = False
        self._target_accuracy = 0.0
        if not self._anim_timer.isActive():
            self._anim_timer.start()

    def _animate_step(self):
        diff = self._target_accuracy - self._display_accuracy
        if abs(diff) < 0.5:
            self._display_accuracy = self._target_accuracy
            self._anim_timer.stop()
        else:
            self._display_accuracy += diff * 0.15
            
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        width = rect.width()
        height = rect.height()
        
        # 텍스트 공간을 위해 높이의 70%만 게이지용으로 사용
        available_side = min(width, height * 0.70)
        
        # 기본 크기(450) 대비 스케일 계산
        scale = available_side / 450.0
        scale = max(0.4, scale)
        
        margin = 10 * scale
        size = available_side - (2 * margin)
        
        x_offset = (width - size) / 2
        y_offset = ((height * 0.70) - size) / 2 + (20 * scale)
        
        gauge_rect = QRectF(x_offset, y_offset, size, size)

        # 1. 배경 링
        pen_bg = QPen(QColor(20, 30, 50), 12 * scale, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_bg)
        painter.drawArc(gauge_rect, 0, 360 * 16)

        # 2. 프로그레스 링
        if self._display_accuracy > 0.1:
            span_angle = int(- (self._display_accuracy / 100.0) * 360 * 16)
            start_angle = 90 * 16
            
            gradient = QConicalGradient(gauge_rect.center(), 90)
            gradient.setColorAt(0.0, QColor("#FF00FF")) 
            gradient.setColorAt(0.5, QColor("#00FFFF")) 
            gradient.setColorAt(1.0, QColor("#FF00FF")) 
            
            # 글로우 효과
            painter.setPen(QPen(QColor(0, 255, 255, 30), 20 * scale, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawArc(gauge_rect, start_angle, span_angle)
            
            painter.setPen(QPen(QColor(255, 0, 255, 60), 16 * scale, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawArc(gauge_rect, start_angle, span_angle)
            
            pen_core = QPen(Qt.PenStyle.SolidLine)
            pen_core.setWidth(int(6 * scale))
            pen_core.setBrush(gradient)
            pen_core.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen_core)
            painter.drawArc(gauge_rect, start_angle, span_angle)
            
            # 파티클 효과
            import random
            import math
            painter.setPen(Qt.PenStyle.NoPen)
            for i in range(0, 360, 45):
                if i < (self._display_accuracy / 100.0 * 360):
                    angle_rad = (90 - i) * 3.14159 / 180
                    px = gauge_rect.center().x() + (size/2 - 5) * math.cos(angle_rad)
                    py = gauge_rect.center().y() - (size/2 - 5) * math.sin(angle_rad)
                    
                    color_dot = QColor("#00FFFF") if i > 180 else QColor("#FF00FF")
                    color_dot.setAlpha(150 + random.randint(0, 50))
                    painter.setBrush(color_dot)
                    painter.drawEllipse(QPoint(int(px), int(py)), int(3 * scale), int(3 * scale))

        # 3. 텍스트 (퍼센트)
        painter.setOpacity(1.0)
        painter.setPen(QColor(255, 255, 255))
        
        font_percent = QFont("Orbitron")
        font_percent.setStyleHint(QFont.StyleHint.SansSerif)
        font_percent.setBold(True)
        font_percent.setPixelSize(int(60 * scale)) 
        painter.setFont(font_percent)
        painter.drawText(gauge_rect, Qt.AlignmentFlag.AlignCenter, f"{int(self._display_accuracy)}%")

        # 4. 레이블 "인식 정확도"
        font_label = QFont("Arial", int(32 * scale), QFont.Weight.Bold)
        painter.setFont(font_label)
        painter.setPen(QColor(0, 255, 255)) 
        
        label_y = gauge_rect.bottom() + (40 * scale)
        label_h = height - label_y
        label_rect = QRectF(0, label_y, width, label_h)
        
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, "인식 정확도")