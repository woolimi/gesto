"""
Gesto 프로젝트 설정 파일
"""

import os

# 애플리케이션 정보
APP_NAME = "Gesto"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Hands-Free Presentation Control"

# 경로 설정 (app/ 하위)
_ROOT = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(_ROOT, "app", "assets")
MODELS_DIR = os.path.join(_ROOT, "app", "models")
DATA_DIR = os.path.join(_ROOT, "app", "data")

# 웹캠 설정
CAMERA_INDEX = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 30

# 제스처 인식 설정
GESTURE_DETECTION_FPS = 30
GESTURE_SEQUENCE_LENGTH = 30  # LSTM 입력 시퀀스 길이
# 모드별 쿨다운(초). 제스처 인식 후 이 시간 동안 새 제스처 인식 안 함
PPT_COOLDOWN_SEC = 1.5
YOUTUBE_COOLDOWN_SEC = 2.0

# 감도 설정 (0-100). UI 감도 → LSTM confidence threshold 매핑 (재훈련 불필요)
SENSITIVITY_DEFAULT = 50
SENSITIVITY_MIN = 0
SENSITIVITY_MAX = 100
# 감도 0(엄격) → threshold 0.9, 감도 100(쉽게) → threshold 0.3
SENSITIVITY_THRESHOLD_MIN = 0.3
SENSITIVITY_THRESHOLD_MAX = 0.9


def sensitivity_to_confidence_threshold(sensitivity: int) -> float:
    """UI 감도 0~100을 LSTM 인식용 confidence threshold(0.3~0.9)로 변환."""
    sensitivity = max(SENSITIVITY_MIN, min(SENSITIVITY_MAX, sensitivity))
    return SENSITIVITY_THRESHOLD_MAX - (sensitivity / 100) * (
        SENSITIVITY_THRESHOLD_MAX - SENSITIVITY_THRESHOLD_MIN
    )

# UI 설정
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
WINDOW_TITLE = f"{APP_NAME} - {APP_DESCRIPTION}"

# 색상 테마 (로고 기반 블루 테마)
COLOR_PRIMARY = "#1E3A5F"  # 진한 네이비 블루
COLOR_SECONDARY = "#4A90E2"  # 밝은 블루
COLOR_ACCENT = "#6BB6FF"  # 라이트 블루
COLOR_BACKGROUND = "#FFFFFF"  # 흰색
COLOR_TEXT_PRIMARY = "#1E3A5F"  # 진한 블루
COLOR_TEXT_SECONDARY = "#6B7280"  # 회색
COLOR_BUTTON_HOVER = "#3B82F6"  # 호버 블루

# 제스처 클래스 정의
GESTURE_CLASSES = {
    "COMMON": {
        "START": 0,
        "STOP": 1,
    },
    "PPT": {
        "NEXT": 2,
        "PREV": 3,
        "SHOW_START": 4,
    },
    "YOUTUBE": {
        "PLAY_PAUSE": 5,
        "VOLUME_UP": 6,
        "VOLUME_DOWN": 7,
        "MUTE": 8,
        "FULLSCREEN": 9,
    }
}
