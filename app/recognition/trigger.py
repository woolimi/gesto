"""
공통 트리거: 모션 감지 시작/종료 판별.
MediaPipe Task API Hand Landmarker로 양손 펴기(시작) / 양손 주먹(종료) 판별.
"""

import os
from enum import Enum

import cv2
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision
import mediapipe as mp

import config


class TriggerResult(str, Enum):
    NONE = "none"
    START = "start"   # 양손 펴기 → 모션 감지 시작
    STOP = "stop"     # 양손 주먹 → 모션 감지 종료


# Hand Landmarker 21 landmarks
WRIST = 0
THUMB_TIP = 4
INDEX_TIP = 8
MIDDLE_TIP = 12
RING_TIP = 16
PINKY_TIP = 20
INDEX_MCP = 5
PINKY_MCP = 17


def _distance(a, b) -> float:
    return ((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5


def _hand_openness(landmarks) -> float:
    """손이 펴져 있으면 큰 값, 주먹이면 작은 값."""
    wrist = landmarks[WRIST]
    palm_ref = _distance(landmarks[INDEX_MCP], landmarks[PINKY_MCP]) or 0.01
    tips = [landmarks[THUMB_TIP], landmarks[INDEX_TIP], landmarks[MIDDLE_TIP], landmarks[RING_TIP], landmarks[PINKY_TIP]]
    total = sum(_distance(wrist, t) for t in tips)
    return total / (palm_ref * 5)


class PostureTriggerDetector:
    """양손 펴기 → START, 양손 주먹 → STOP. (공통 트리거)"""

    def __init__(self, open_threshold: float = 1.4, fist_threshold: float = 0.85):
        self.open_threshold = open_threshold
        self.fist_threshold = fist_threshold
        model_path = os.path.join(config.MODELS_DIR, "hand_landmarker.task")
        if not os.path.isfile(model_path):
            model_path = os.path.abspath(model_path)
        base_options = mp_tasks.BaseOptions(model_asset_path=model_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=2,
            min_hand_detection_confidence=0.6,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)

    def process(self, frame_bgr) -> TriggerResult:
        """BGR 프레임에서 트리거만 판별. NONE / START / STOP."""
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect(mp_image)
        if not result.hand_landmarks or len(result.hand_landmarks) < 2:
            return TriggerResult.NONE
        hands = result.hand_landmarks
        openness = [_hand_openness(h) for h in hands]
        if len(openness) < 2:
            return TriggerResult.NONE
        o0, o1 = openness[0], openness[1]
        if o0 >= self.open_threshold and o1 >= self.open_threshold:
            return TriggerResult.START
        if o0 <= self.fist_threshold and o1 <= self.fist_threshold:
            return TriggerResult.STOP
        return TriggerResult.NONE

    def close(self):
        if self._landmarker is not None:
            close_fn = getattr(self._landmarker, "close", None)
            if callable(close_fn):
                close_fn()
            self._landmarker = None
