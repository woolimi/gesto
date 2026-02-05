import math
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QRegion, QPainterPath

class NeonFrameWidget(QWidget):
    """
    동적 HUD 프레임:
    - 색상 순환 애니메이션.
    - 네온 엣지 및 코너 HUD 포인트 포인트 효과.
    """
    def __init__(self, content_widget, parent=None):
        super().__init__(parent)
        self.content_widget = content_widget
        self.anim_frame = 0.0
        self.color_hue = 180 # 시안색에서 시작
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(self.content_widget)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_anim)
        self.timer.start(16)
        
    def update_anim(self):
        self.anim_frame += 0.05
        # 부드러운 색상 변화 (시안 180 ~ 바이올렛 280 사이)
        self.color_hue = 180 + 50 + 50 * math.sin(self.anim_frame * 0.2)
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w, h = self.width(), self.height()
        outer_rect = QRectF(2, 2, w-4, h-4)
        
        # 비율 스케일링
        scale = h / 480.0
        scale = max(0.2, min(1.2, scale))
        
        # 색상 계산
        neon_color = QColor.fromHsvF(self.color_hue / 360.0, 0.8, 1.0)
        
        # 1. 메인 네온 글로우 (펄싱 효과)
        pulse = 0.5 + 0.5 * math.sin(self.anim_frame)
        glow_alpha = int(30 + 15 * pulse)
        
        glow_pen = QPen(neon_color, 6 * scale)
        neon_color.setAlpha(glow_alpha)
        glow_pen.setColor(neon_color)
        
        painter.setPen(glow_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(outer_rect, 10 * scale, 10 * scale)
        
        # 2. 선명한 코어 라인
        line_alpha = int(150 + 50 * pulse)
        core_color = QColor.fromHsvF(self.color_hue / 360.0, 0.5, 1.0, line_alpha/255.0)
        painter.setPen(QPen(core_color, 2 * scale))
        painter.drawRoundedRect(outer_rect, 10 * scale, 10 * scale)
        
        # 3. 코너 HUD 장식 (기하학적 브래킷)
        acc_len = 35 * scale
        acc_color = QColor.fromHsvF(self.color_hue / 360.0, 0.9, 1.0, line_alpha/255.0)
        painter.setPen(QPen(acc_color, 3 * scale))
        
        # TL
        painter.drawLine(QPointF(2, 2), QPointF(2 + acc_len, 2))
        painter.drawLine(QPointF(2, 2), QPointF(2, 2 + acc_len))
        # TR
        painter.drawLine(QPointF(w - 2 - acc_len, 2), QPointF(w - 2, 2))
        painter.drawLine(QPointF(w - 2, 2), QPointF(w - 2, 2 + acc_len))
        # BL
        painter.drawLine(QPointF(2, h - 2 - acc_len), QPointF(2, h - 2))
        painter.drawLine(QPointF(2, h - 2), QPointF(2 + acc_len, h - 2))
        # BR
        painter.drawLine(QPointF(w - 2 - acc_len, h - 2), QPointF(w - 2, h - 2))
        painter.drawLine(QPointF(w - 2, h - 2), QPointF(w - 2, h - 2 - acc_len))
