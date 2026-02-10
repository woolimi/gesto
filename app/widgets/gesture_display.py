"""
제스처 표시 위젯
"""

import time

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

import config


class GestureDisplayWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_gesture: str | None = None
        self._last_probs: dict = {}
        self._current_threshold: float | None = None
        self._clear_timer: QTimer | None = None
        self._current_status = "대기 중"
        self.init_ui()

    def init_ui(self):
        # Remove parent layout margins to let widgets center themselves
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)
        
        # Status Label Removed (User Request)
        # self.status_label = ...

        # Gesture Label (e.g., "인식된 제스처: ...")
        self.gesture_label = QLabel("")
        self.gesture_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.gesture_label.setFont(QFont("Arial", 11))
        self.gesture_label.setStyleSheet(f"color: {config.COLOR_TEXT_SECONDARY}; background-color: transparent;")
        self.gesture_label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        layout.addWidget(self.gesture_label)

        # GESTURE_DEBUG 시 제스처별 확률·threshold·11채널 표시 (가독성 위해 큰 글씨·최소 높이)
        self.debug_label = QLabel("")
        self.debug_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.debug_label.setFont(QFont("Monospace", 13))
        self.debug_label.setMinimumHeight(78)
        self.debug_label.setStyleSheet(
            "color: rgba(0, 255, 255, 220); background-color: rgba(0, 0, 0, 180); "
            "border: none; padding: 6px 8px;"
        )
        is_debug = getattr(config, "GESTURE_DEBUG", False)
        self.debug_label.setVisible(is_debug)
        self.debug_label.setWordWrap(True)
        layout.addWidget(self.debug_label)
        if is_debug:
            self.setMinimumHeight(130)
        # 11채널 이름 (lib/hand_features 순서)
        self._ch_names = (
            "x", "y", "z",
            "IsFist_L", "Pinch_L", "ThumbV_L", "IdxZ_L",
            "IsFist_R", "Pinch_R", "ThumbV_R", "IdxZ_R",
        )

        self.setLayout(layout)
        # Remove widget-level background
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_font_scaling()

    def _update_font_scaling(self):
        """창 크기에 맞춰 폰트 크기와 패딩을 동적으로 조정."""
        w = self.width()
        h = self.height()
        if w <= 0 or h <= 0:
            return

        # 400x60 규격 기준 스케일 계산
        scale_w = w / 400.0
        scale_h = h / 60.0
        scale = min(scale_w, scale_h)
        
        # 폰트 크기 계산 (기존 11 -> 22 -> 40으로 공격적 상향)
        base_size = 18
        new_size = max(20, int(base_size * scale))
        
        font = QFont("NanumSquareRound")
        if not font.exactMatch(): 
            font = QFont("Ubuntu Sans")
            
        font.setPixelSize(new_size)
        font.setBold(True)
        font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 105)
        self.gesture_label.setFont(font)

        # 디버그 라벨 폰트도 스케일 (가독성)
        if getattr(config, "GESTURE_DEBUG", False):
            debug_font = QFont("Monospace", 13)
            debug_font.setPixelSize(max(12, int(14 * scale)))
            self.debug_label.setFont(debug_font)
            self.debug_label.setMinimumHeight(max(78, int(40 * scale)))

        # 상태에 따른 스타일 업데이트 (패딩 등 스케일링 적용)
        self._refresh_style(scale)

    def _refresh_style(self, scale: float = 1.0):
        """현재 상태의 스타일을 스케일에 맞춰 다시 적용."""
        if self._current_status == "대기 중":
            self.gesture_label.setStyleSheet(
                f"color: {config.COLOR_TEXT_SECONDARY}; background-color: transparent;"
            )
        elif self._last_gesture:
            padding = int(8 * scale)
            radius = int(8 * scale)
            self.gesture_label.setStyleSheet(
            f"color: #00FFFF; font-family: '{config.FONT_MAIN}', 'Ubuntu Sans'; "
            f"background-color: rgba(10, 20, 30, 230); "
            f"border: 1px solid rgba(0, 255, 255, 80); "
            f"border-radius: {radius}px; padding: {padding}px {padding*2.5}px;"
        )
        else:
            padding = int(5 * scale)
            radius = int(8 * scale)
            self.gesture_label.setStyleSheet(
                f"color: {config.COLOR_TEXT_SECONDARY}; background-color: rgba(0, 0, 0, 150); "
                f"border-radius: {radius}px; padding: {padding}px {padding*3}px;"
            )

    def set_threshold(self, threshold: float):
        """Main Window에서 호출: 현재 감도 기준 임계값 업데이트."""
        self._current_threshold = threshold

    def _format_fist_debug(self, fist_debug) -> str:
        """fist_debug = {"left": (0|1, ...), "right": ...} → Fist: L=1 R=0 형태만 표시."""
        if not fist_debug:
            return ""
        parts = []
        for hand in ("left", "right"):
            short = "L" if hand == "left" else "R"
            val, _ = fist_debug.get(hand, (0.0, []))
            parts.append(f"{short}={int(round(val))}")
        return "Fist: " + "  ".join(parts)

    def update_debug(self, probs: dict, threshold: float, channels_11=None, fist_debug=None):
        """GESTURE_DEBUG 시: 확률 상위 3개, 왼/오 주먹값, is_fist 실시간 손가락별 판정 표시."""
        if not getattr(config, "GESTURE_DEBUG", False):
            return
        self.debug_label.setVisible(True)
        parts = [f"Thr:{threshold:.2f}"]
        if probs:
            top3 = sorted(probs.items(), key=lambda x: -x[1])[:3]
            parts.append("|")
            for k, v in top3:
                parts.append(f"{k}={v:.2f}")
        line1 = " ".join(parts)
        lines = [line1]
        fist_line = self._format_fist_debug(fist_debug)
        if fist_line:
            lines.append(fist_line)
        self.debug_label.setText("\n".join(lines))


    def _clear_gesture_label(self):
        """쿨다운 종료 시점에 호출: 인식된 제스처·디버그 라벨 초기화 후 실시간 반영 모드로 전환."""
        self._clear_timer = None
        self._last_gesture = None
        if self._current_status == "감지 중":
            self._last_gesture = None
            self.gesture_label.setText("제스처가 인식되지 않았습니다")
            self._update_font_scaling()


    def update_status(
        self,
        status: str,
        gesture: str = None,
        clear_at_monotonic: float | None = None,
        probs: dict = None,
        threshold: float | None = None,
    ):
        """clear_at_monotonic: 백엔드와 공유한 쿨다운 종료 시각(time.monotonic()). 이 시각에 라벨 초기화.
        probs: 인식 시 모든 클래스별 확률 (클래스명 → 0~1).
        threshold: 현재 감도 기준 인식 기준선 (0.80~0.99)."""
        self._current_status = status
        
        if status == "대기 중":
            self._last_gesture = None
            self._last_probs = {}
            if self._clear_timer is not None:
                self._clear_timer.stop()
                self._clear_timer = None
            self.gesture_label.setText("")
            
        elif gesture:
            self._last_gesture = gesture
            self.gesture_label.setText(f"{gesture}") 
            
            if self._clear_timer is not None:
                self._clear_timer.stop()
            if clear_at_monotonic is not None and clear_at_monotonic > 0:
                delay_sec = max(0.0, clear_at_monotonic - time.monotonic())
                self._clear_timer = QTimer(self)
                self._clear_timer.setSingleShot(True)
                self._clear_timer.timeout.connect(self._clear_gesture_label)
                self._clear_timer.start(int(delay_sec * 1000))
        else:
            # 쿨다운 중: 감지된 제스처 로그 유지. clear_at_monotonic으로 쿨다운 종료 시에만 타이머 설정
            if self._last_gesture is not None:
                pass 
            else:
                self.gesture_label.setText("")
        
        # 마지막에 폰트 및 스타일 업데이트
        self._update_font_scaling()
