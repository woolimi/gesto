"""
Gesto 프로젝트 설정 파일
"""

import os
import sys

# 애플리케이션 정보
APP_NAME = "Gesto"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "핸즈프리 제스처 컨트롤 서비스"

# 경로 설정 (app/ 하위)
_ROOT = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(_ROOT, "app", "assets")
MODELS_DIR = os.path.join(_ROOT, "app", "models")
DATA_DIR = os.path.join(_ROOT, "app", "data")

# 웹 게임 설정
GAME_URL = "https://ratlabyrinth.netlify.app/"

# 웹캠 설정
CAMERA_INDEX = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 30

# 제스처 인식 설정
GESTURE_DETECTION_FPS = 30
GESTURE_SEQUENCE_LENGTH = 30  # LSTM 입력 시퀀스 길이
# True면 UI에 제스처별 확률·threshold 디버그 표시 (기존 UI 유지)
GESTURE_DEBUG = False
# 모드별 쿨다운(초). 제스처 인식 후 이 시간 동안 새 제스처 인식 안 함
PPT_COOLDOWN_SEC = 1.0
YOUTUBE_COOLDOWN_SEC = 1.0

# 감도 설정 (0-100). UI 감도 → LSTM confidence threshold 매핑 (재훈련 불필요)
SENSITIVITY_DEFAULT = 0
SENSITIVITY_MIN = 0
SENSITIVITY_MAX = 100
# 감도 0(엄격) → threshold 0.9, 감도 100(쉽게) → threshold 0.3
SENSITIVITY_THRESHOLD_MIN = 0.90
SENSITIVITY_THRESHOLD_MAX = 0.99


def sensitivity_to_confidence_threshold(sensitivity: int) -> float:
    """UI 감도 0~100을 LSTM 인식용 confidence threshold(0.80~0.99)로 변환."""
    sensitivity = max(0, min(100, sensitivity))
    return SENSITIVITY_THRESHOLD_MAX - (sensitivity / 100.0) * (
        SENSITIVITY_THRESHOLD_MAX - SENSITIVITY_THRESHOLD_MIN
    )

# UI 설정
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = f"{APP_NAME} - {APP_DESCRIPTION}"

FONT_MAIN = "Giants Inline"

# 색상 테마 (V4 Chroma/Neon Dark Theme)
COLOR_PRIMARY = "#00FFFF"      # Neon Cyan
COLOR_SECONDARY = "#FF00FF"    # Neon Magenta
COLOR_ACCENT = "#9D00FF"       # Deep Purple
COLOR_BACKGROUND = "#050510"   # Deep Dark Navy/Black
COLOR_TEXT_PRIMARY = "#FFFFFF" # White
COLOR_TEXT_SECONDARY = "#AAAAAA" # Light Grey
COLOR_BUTTON_HOVER = "#00CCCC" # Cyan Hover

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
# 제스처 표시 이름 매핑
GESTURE_DISPLAY_MAP = {
    "Swipe_Left": "Swipe Left",
    "Swipe_Right": "Swipe Right",
    "Pinch_Out_Left": "전체 화면 📺",
    "Pinch_Out_Right": "전체 화면 📺",
    "Pinch_In_Left": "최소화 ⬇️",
    "Pinch_In_Right": "최소화 ⬇️",
    "Play_Pause_Left": "재생/일시정지 ⏯️",
    "Play_Pause_Right": "재생/일시정지 ⏯️",
    "Volume_Up_Left": "볼륨 올림 🔊",
    "Volume_Up_Right": "볼륨 올림 🔊",
    "Volume_Down_Left": "볼륨 내림 🔉",
    "Volume_Down_Right": "볼륨 내림 🔉",
    "forward": "전진 ⬆️",
    "back": "후진 ⬇️",
    "left": "좌회전 ⬅️",
    "right": "우회전 ➡️",
    "forward|left": "전진 + 좌회전 ↖️",
    "forward|right": "전진 + 우회전 ↗️",
    "back|left": "후진 + 좌회전 ↙️",
    "back|right": "후진 + 우회전 ↘️",
    "back|forward": "전진 + 후진 ",
    "left|right": "좌회전 + 우회전 ",
    "AR 추적 활성화됨": "동작 감지중 ✨",
    "대기 중": "동작 감지 해제 ⏸️"
}

# 구글 슬라이드 발표 시작(전체화면): Mac = cmd+enter, Ubuntu/Linux = ctrl+f5
PPT_PRESENT_KEYS = "cmd+enter" if sys.platform == "darwin" else "ctrl+f5"
PPT_PLAY_PAUSE_KEY = "k"

# 제스처 -> 키 입력 매핑 (ModeController 사용)
# 형식: { "모드": { "제스처명": "키보드키" } }
# pynput.keyboard.Key 속성명(예: "right", "left", "up", "space") 또는 일반 문자 사용 가능
# ','를 사용하여 여러 키를 순차적으로 입력 가능 (예: "ctrl+f5, k")
GESTURE_ACTION_MAP = {
    "PPT": {
        "Swipe_Left": "right",
        "Swipe_Right": "left",
        # 구글 슬라이드: Pinch Out = 발표 시작, Pinch In = 발표 종료
        "Pinch_Out_Left": PPT_PRESENT_KEYS,
        "Pinch_Out_Right": PPT_PRESENT_KEYS,
        "Pinch_In_Left": "esc",
        "Pinch_In_Right": "esc",

        # 재생/일시정지 제스처 추가 (전용 제스처 사용)
        "Play_Pause_Left": PPT_PLAY_PAUSE_KEY,
        "Play_Pause_Right": PPT_PLAY_PAUSE_KEY,
    },
    "YOUTUBE": {
        "Swipe_Left": "j",
        "Swipe_Right": "l",

        # Legacy LSTM labels (좌/우 분리)
        "Pinch_Out_Left": "f",
        "Pinch_Out_Right": "f",
        "Pinch_In_Left": "esc",
        "Pinch_In_Right": "esc",

        # New explicit play/pause gestures (좌/우 분리)
        "Play_Pause_Left": "k",
        "Play_Pause_Right": "k",

        # Volume control (좌/우 분리)
        # YouTube 단축키: ArrowUp/ArrowDown = 볼륨 ±5%
        "Volume_Up_Left": "up",
        "Volume_Up_Right": "up",
        "Volume_Down_Left": "down",
        "Volume_Down_Right": "down",
    },
    "GAME": {
        "forward": "up",
        "back": "down",
        "left": "left",
        "right": "right",
    }
}

