import random
import math
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QPoint, QRect, QLineF, QPointF, QRectF
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QPolygonF, QLinearGradient, QRadialGradient, QImage

class AuroraGradientBackground(QWidget):
    """
    오로라 그라데이션 배경 엔진:
    - 움직이는 방사형 그라데이션 (마젠타, 퍼플, 블루)
    - 노이즈 텍스처 효과
    - 미세한 HUD 오버레이 (DNA, 스캔 효과)
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        
        self.anim_frame = 0.0
        
        # 1. 오로라 블롭 설정
        self.blobs = [
            {'color': QColor(255, 0, 120),  'x_phase': 0.0, 'y_phase': 1.5, 'r_mult': 0.6, 'speed': 0.015}, # 마젠타
            {'color': QColor(100, 0, 255),  'x_phase': 2.0, 'y_phase': 0.5, 'r_mult': 0.8, 'speed': 0.01},  # 퍼플
            {'color': QColor(0, 100, 255),  'x_phase': 1.0, 'y_phase': 2.5, 'r_mult': 0.7, 'speed': 0.02},  # 딥 블루
            {'color': QColor(0, 255, 255),  'x_phase': 3.0, 'y_phase': 1.0, 'r_mult': 0.5, 'speed': 0.018} # 시안
        ]
        
        # 2. 노이즈 텍스처 설정
        self.noise_img = self._create_noise_texture(64, 64)
        
        # 3. HUD 파티클 설정
        self.dust = []
        for _ in range(25):
            self.dust.append({
                'x': random.uniform(0, 1280),
                'y': random.uniform(0, 720),
                'vx': random.uniform(-0.4, 0.4),
                'vy': random.uniform(-0.4, 0.4),
                'size': random.uniform(1, 2)
            })

        # 4. 스캔 펄스 위치
        self.pulse_pos = -0.5

        # 애니메이션 타이머
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(16) # ~60 FPS

    def _create_noise_texture(self, w, h):
        img = QImage(w, h, QImage.Format.Format_ARGB32)
        for x in range(w):
            for y in range(h):
                val = random.randint(0, 20)
                img.setPixelColor(x, y, QColor(255, 255, 255, val))
        return img

    def update_frame(self):
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0: return
        
        self.anim_frame += 0.05
        
        # 블롭 이동
        for b in self.blobs:
            b['x_phase'] += b['speed']
            b['y_phase'] += b['speed'] * 0.8
            
        # 먼지 파티클 이동
        for d in self.dust:
            d['x'] = (d['x'] + d['vx']) % 1280
            d['y'] = (d['y'] + d['vy']) % 720
            
        # 스캔 이동
        self.pulse_pos += 0.002
        if self.pulse_pos > 1.5: self.pulse_pos = -0.5
                
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        
        # 1. 배경 채우기
        painter.fillRect(0, 0, w, h, QColor(10, 5, 25))
        
        # 2. 오로라 블롭 그리기 (스크린 합성 모드)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
        for b in self.blobs:
            cx = w/2 + math.sin(b['x_phase']) * (w/3)
            cy = h/2 + math.cos(b['y_phase']) * (h/3)
            radius = min(w, h) * b['r_mult']
            
            grad = QRadialGradient(QPointF(cx, cy), radius)
            grad.setColorAt(0, b['color'])
            grad.setColorAt(1, QColor(0, 0, 0, 0))
            
            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(cx - radius, cy - radius, radius*2, radius*2))
            
        # 3. 노이즈 텍스처 오버레이
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        for x in range(0, w, 256):
            for y in range(0, h, 256):
                painter.drawImage(x, y, self.noise_img)

        # 4. HUD 디테일 오버레이
        self._draw_hud_details(painter, w, h)

    def _draw_hud_details(self, painter, w, h):
        # DNA 헬릭스 (측면 프레임)
        self._draw_dna_helix(painter, 100, h//2, h-300)
        self._draw_dna_helix(painter, w-100, h//2, h-300)
        
        # 스캔 펄스 효과
        center_x = self.pulse_pos * (w + h)
        grad = QLinearGradient(QPointF(center_x-100, center_x-100), QPointF(center_x+100, center_x+100))
        grad.setColorAt(0, QColor(0, 255, 255, 0))
        grad.setColorAt(0.5, QColor(0, 255, 255, 10))
        grad.setColorAt(1, QColor(0, 255, 255, 0))
        painter.fillRect(0, 0, w, h, grad)
        
        # 데이터 포인트 파티클
        painter.setPen(Qt.PenStyle.NoPen)
        for d in self.dust:
            op = int(100 + 100 * math.sin(self.anim_frame * 0.5))
            painter.setBrush(QBrush(QColor(0, 255, 255, op)))
            painter.drawEllipse(QPointF(d['x']*w/1280, d['y']*h/720), d['size'], d['size'])

    def _draw_dna_helix(self, painter, cx, cy, height):
        num_points = 15
        spacing = height / num_points
        amplitude = 20
        for i in range(num_points):
            y_off = (i - num_points / 2) * spacing
            angle = self.anim_frame + i * 0.4
            
            x1 = cx + math.sin(angle) * amplitude
            y1 = cy + y_off
            x2 = cx + math.sin(angle + math.pi) * amplitude
            y2 = cy + y_off
            
            z1 = math.cos(angle)
            z2 = math.cos(angle + math.pi)
            
            # 베이스 페어 연결선
            painter.setPen(QPen(QColor(0, 255, 255, 20), 1))
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
            
            # 노드
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(0, 255, 255, int(60 + 30*z1))))
            painter.drawEllipse(QPointF(x1, y1), 1.5+z1, 1.5+z1)
            painter.setBrush(QBrush(QColor(255, 0, 255, int(30 + 15*z2))))
            painter.drawEllipse(QPointF(x2, y2), 1.5+z2, 1.5+z2)
