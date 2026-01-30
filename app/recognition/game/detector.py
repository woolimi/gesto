"""
Game 모드 전용 감지.
크롬 브라우저에서 방향키(↑↓←→)로 동작하는 게임 제어를 전제로,
직진/후진/좌회전/우회전을 방향키에 매핑. 양손 지원, 1~2방향 동시 적용 가능.

이 디텍터는 process(frame) → 제스처 이름 문자열만 반환.
제스처 이름 → 키 매핑 및 pynput 입력은 ModeController가 담당.
지원 문자열: "forward", "back", "left", "right".
복수 방향은 "|"로 연결 (예: "forward|right"). 검지만 방향을 가리키고 엄지 제외
나머지(중지·약지·소지)는 접힌 상태일 때만 인식.
양손 인식률을 높이려면 두 손이 모두 화면에 잘 보이도록 하면 좋다.
"""

import math
import os
from typing import Optional

import cv2
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision
import mediapipe as mp

import config

# 랜드마크 인덱스 (trigger.py와 동일)
WRIST = 0
INDEX_MCP, INDEX_PIP, INDEX_TIP = 5, 6, 8
MIDDLE_MCP, MIDDLE_TIP = 9, 12
RING_MCP, RING_TIP = 13, 16
PINKY_MCP, PINKY_TIP = 17, 20

# 방향명 정렬 순서 (일관된 "|" 결합용)
_DIR_ORDER = ("back", "forward", "left", "right")

# 각도 구간 (degree). 구간 확대·겹침으로 경계에서 튀는 현상 완화
# up -120~-60, right -60~60, down 60~120, left 120~180 / -180~-120
_ANGLE_UP = (-120, -60)
_ANGLE_RIGHT = (-60, 60)
_ANGLE_DOWN = (60, 120)
_ANGLE_LEFT_LOW = 120  # left: angle_deg >= 120 or angle_deg < -120

# EMA 스무딩: 경계 근처에서 forward/right 등이 떨리지 않도록 (alpha=0.75 → 25% 신규 반영)
_ANGLE_EMA_ALPHA = 0.75


def _hand_size(landmarks) -> float:
    """손 크기: 손목~중지 MCP 거리. 최소값으로 나눗셈 안정화."""
    raw = math.hypot(
        landmarks[MIDDLE_MCP].x - landmarks[WRIST].x,
        landmarks[MIDDLE_MCP].y - landmarks[WRIST].y,
    )
    return max(raw, 0.04)


def _dist(a, b, landmarks) -> float:
    return math.hypot(landmarks[b].x - landmarks[a].x, landmarks[b].y - landmarks[a].y)


# 주먹: 네 손가락 중 가장 펴진 값이 이 값 미만이면 "아무 손가락도 안 펴진 것" → 주먹
_FIST_MAX_EXTEND = 0.13
# 검지 포인팅으로 인정할 검지 최소 연장 (이 이상 펴져 있어야 포인팅)
_INDEX_POINT_MIN_EXTEND = 0.14


def _is_index_pointing_gesture(landmarks, hand_scale: float) -> bool:
    """
    검지로 방향을 가리키는 자세인지 판별.
    - 주먹: max(검·중·약·소 연장) < _FIST_MAX_EXTEND 이면 무조건 False.
    - 완화/엄격 모두 검지가 _INDEX_POINT_MIN_EXTEND 이상일 때만 포인팅 인정.
    """
    if hand_scale <= 0:
        return False
    index_extend = _dist(INDEX_MCP, INDEX_TIP, landmarks) / hand_scale
    middle_extend = _dist(MIDDLE_MCP, MIDDLE_TIP, landmarks) / hand_scale
    ring_extend = _dist(RING_MCP, RING_TIP, landmarks) / hand_scale
    pinky_extend = _dist(PINKY_MCP, PINKY_TIP, landmarks) / hand_scale

    # 주먹: 어떤 손가락도 충분히 펴지 않았으면 포인팅 아님 (양손 주먹 → back 오인 방지)
    max_extend = max(index_extend, middle_extend, ring_extend, pinky_extend)
    if max_extend < _FIST_MAX_EXTEND:
        return False

    # 검지는 최소 _INDEX_POINT_MIN_EXTEND 이상 펴져 있어야 포인팅 (엄격/완화 공통)
    if index_extend < _INDEX_POINT_MIN_EXTEND:
        return False
    # 완화 모드: 검지가 네 손가락 중 가장 펴져 있을 때
    if index_extend >= middle_extend and index_extend >= ring_extend and index_extend >= pinky_extend:
        return True
    # 엄격 모드: 검지 펴짐 + 나머지 접힘
    fold_thresh = 0.55
    return (
        middle_extend < fold_thresh
        and ring_extend < fold_thresh
        and pinky_extend < fold_thresh
    )


def _index_angle_deg(landmarks) -> Optional[float]:
    """검지 방향 각도(degree). PIP→TIP 벡터 기준. None이면 유효하지 않음."""
    dx = landmarks[INDEX_TIP].x - landmarks[INDEX_PIP].x
    dy = landmarks[INDEX_TIP].y - landmarks[INDEX_PIP].y
    length = math.hypot(dx, dy)
    if length < 0.01:
        return None
    return math.degrees(math.atan2(dy, dx))


def _angle_to_direction(angle_deg: float) -> Optional[str]:
    """각도(degree)를 forward/back/left/right 중 하나로 변환. 경계는 상수 사용."""
    def in_range(lo, hi):
        return lo <= angle_deg < hi

    if in_range(_ANGLE_UP[0], _ANGLE_UP[1]):
        return "forward"
    if in_range(_ANGLE_RIGHT[0], _ANGLE_RIGHT[1]):
        return "right"
    if in_range(_ANGLE_DOWN[0], _ANGLE_DOWN[1]):
        return "back"
    if angle_deg >= _ANGLE_LEFT_LOW or angle_deg < -_ANGLE_LEFT_LOW:
        return "left"
    return None


def _direction_from_hand(landmarks) -> Optional[str]:
    """한 손 랜드마크에서 유효한 '검지 포인팅'이면 방향 반환, 아니면 None."""
    scale = _hand_size(landmarks)
    if not _is_index_pointing_gesture(landmarks, scale):
        return None
    angle = _index_angle_deg(landmarks)
    if angle is None:
        return None
    return _angle_to_direction(angle)


def _normalize_angle(deg: float) -> float:
    """각도를 [-180, 180) 구간으로 정규화. EMA 시 경계 넘김 보정용."""
    while deg >= 180:
        deg -= 360
    while deg < -180:
        deg += 360
    return deg


def _hand_label_from_result(result, index: int) -> str:
    """
    result에서 index번 손의 Left/Right 라벨 반환.
    MediaPipe는 프레임마다 hand_landmarks 순서가 바뀔 수 있으므로, EMA는 리스트 인덱스가 아니라
    손 identity(Left/Right) 기준으로 유지해야 함.
    """
    try:
        if not hasattr(result, "handedness") or not result.handedness or index >= len(result.handedness):
            return str(index)
        h = result.handedness[index]
        name = None
        if hasattr(h, "categories") and len(h.categories) > 0:
            c = h.categories[0]
            name = getattr(c, "category_name", None) or getattr(c, "label", None)
        if name is None and hasattr(h, "classification") and len(h.classification) > 0:
            c = h.classification[0]
            name = getattr(c, "label", None) or getattr(c, "category_name", None)
        if name in ("Left", "Right"):
            return name
    except (IndexError, AttributeError, TypeError):
        pass
    return str(index)


class GameDetector:
    """Game 모드: 검지 포인팅으로 직진/후진/좌회전/우회전 방향 감지. 양손·동시 2방향 지원."""

    def __init__(self):
        # 손별 각도 EMA (Left/Right 기준). 프레임마다 손 순서가 바뀌어도 동일 손끼리 스무딩
        self._angle_ema: dict[str, Optional[float]] = {"Left": None, "Right": None}
        model_path = os.path.join(config.MODELS_DIR, "hand_landmarker.task")
        base_options = mp_tasks.BaseOptions(model_asset_path=model_path)
        # 2손 인식: num_hands=2. 임계값 낮춰 손/제스처 인식률 확보 (검지 포인팅이 잘 잡히도록)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=2,
            min_hand_detection_confidence=0.25,
            min_hand_presence_confidence=0.25,
            min_tracking_confidence=0.25,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)

    def _detect(self, frame_bgr):
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        return self._landmarker.detect(mp_image)

    def process(self, frame_bgr) -> Optional[str]:
        """
        BGR 프레임에서 자세/제스처 판별.
        검지만 방향을 가리키고 나머지(중지·약지·소지) 접힌 상태일 때만 인식.
        반환: None, "forward", "back", "left", "right", 또는 "dir1|dir2" (최대 2방향, 정렬됨).
        """
        result = self._detect(frame_bgr)
        if not result.hand_landmarks:
            return None

        directions = []
        for i, hand_landmarks in enumerate(result.hand_landmarks):
            hand_key = _hand_label_from_result(result, i)
            if hand_key not in self._angle_ema:
                self._angle_ema[hand_key] = None

            scale = _hand_size(hand_landmarks)
            if not _is_index_pointing_gesture(hand_landmarks, scale):
                self._angle_ema[hand_key] = None
                continue
            raw_angle = _index_angle_deg(hand_landmarks)
            if raw_angle is None:
                self._angle_ema[hand_key] = None
                continue
            # EMA 스무딩 (손 identity 기준이라 프레임마다 순서가 바뀌어도 왼손/오른손 각각 유지)
            if self._angle_ema[hand_key] is None:
                self._angle_ema[hand_key] = raw_angle
            else:
                diff = _normalize_angle(raw_angle - self._angle_ema[hand_key])
                self._angle_ema[hand_key] = _normalize_angle(
                    self._angle_ema[hand_key] + (1.0 - _ANGLE_EMA_ALPHA) * diff
                )
            d = _angle_to_direction(self._angle_ema[hand_key])
            if d is not None and d not in directions:
                directions.append(d)
                if len(directions) >= 2:
                    break

        if not directions:
            return None
        ordered = sorted(directions, key=lambda x: _DIR_ORDER.index(x))
        return "|".join(ordered)

    def close(self) -> None:
        """리소스 해제 (Hand Landmarker)."""
        if self._landmarker:
            self._landmarker.close()
            self._landmarker = None
