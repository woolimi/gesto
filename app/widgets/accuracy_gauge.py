"""
accuracy_gauge.py
인식 정확도 게이지 위젯
"""

from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtCore import Qt, QRectF, QTimer, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QConicalGradient

import config

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
        
        # 1. 동적 레이아웃 계산
        # 게이지 링과 하단 라벨 사이의 비율을 동적으로 설정 (라벨용 최소 공간 확보)
        label_height_ratio = 0.25 # 하단 라벨용 공간 25%
        ring_area_height = height * (1.0 - label_height_ratio)
        
        # 가로/세로 중 작은 쪽에 맞춰 정사각형 게이지 영역 결정
        available_side = min(width, ring_area_height)
        
        # 기본 크기(450) 기준 스케일 계산 (하한선 제거하여 유연하게 축소)
        scale = available_side / 450.0
        
        # 여백 및 반지름 계산
        margin = 15 * scale
        side = available_side - (2 * margin)
        
        # 게이지 링 위치 중앙 정렬 (링 영역 내에서)
        x_offset = (width - side) / 2
        y_offset = (ring_area_height - side) / 2 + (10 * scale)
        
        gauge_rect = QRectF(x_offset, y_offset, side, side)

        # 2. 배경 링 그리기 (두께 16 -> 24)
        pen_bg = QPen(QColor(20, 30, 50), 24 * scale, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_bg)
        painter.drawArc(gauge_rect, 0, 360 * 16)

        # 3. 프로그레스 링 그리기
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
            pen_core.setWidth(max(1, int(16 * scale)))
            pen_core.setBrush(gradient)
            pen_core.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen_core)
            painter.drawArc(gauge_rect, start_angle, span_angle)
            
            # 파티클 효과 (너무 작을 때는 생략)
            if scale > 0.3:
                import random
                import math
                painter.setPen(Qt.PenStyle.NoPen)
                for i in range(0, 360, 45):
                    if i < (self._display_accuracy / 100.0 * 360):
                        angle_rad = (90 - i) * 3.14159 / 180
                        px = gauge_rect.center().x() + (side/2 - 5) * math.cos(angle_rad)
                        py = gauge_rect.center().y() - (side/2 - 5) * math.sin(angle_rad)
                        
                        color_dot = QColor("#00FFFF") if i > 180 else QColor("#FF00FF")
                        color_dot.setAlpha(150 + random.randint(0, 50))
                        painter.setBrush(color_dot)
                        painter.drawEllipse(QPoint(int(px), int(py)), int(3 * scale), int(3 * scale))

        # 4. 중앙 % 텍스트
        painter.setOpacity(1.0)
        painter.setPen(QColor(255, 255, 255))
        
        font_percent = QFont(config.FONT_MAIN)
        font_percent.setBold(True)
        # 소수점 출력을 피하면서 적절한 폰트 크기 계산 (기존 100 -> 160 상향)
        font_percent.setPixelSize(max(12, int(100 * scale))) 
        font_percent.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 110)
        painter.setFont(font_percent)
        painter.drawText(gauge_rect, Qt.AlignmentFlag.AlignCenter, f"{int(self._display_accuracy)}%")

        # 5. 하단 "인식 정확도" 레이블
        # 남은 하단 여백 전체를 라벨 영역으로 사용
        label_rect = QRectF(0, ring_area_height, width, height - ring_area_height)
        
        font_label = QFont(config.FONT_MAIN)
        font_label.setBold(True)
        # 기존 45 -> 70 -> 80 상향
        font_label.setPixelSize(max(10, int(80 * scale)))
        font_label.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 115)
        painter.setFont(font_label)
        painter.setPen(QColor(0, 255, 255)) 
        
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, "인식 정확도")