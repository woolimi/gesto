import os
from enum import Enum

import cv2
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision
import mediapipe as mp

import config

# Hand Landmarker 21점 연결
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8),
    (0, 9), (9, 10), (10, 11), (11, 12), (0, 13), (13, 14), (14, 15), (15, 16),
    (0, 17), (17, 18), (18, 19), (19, 20), (5, 9), (9, 13), (13, 17),
]

class TriggerResult(str, Enum):
    NONE = "none"
    START = "start"   # 양손 펴기 + 손바닥 정면 + 위 방향
    STOP = "stop"     # 양손 주먹 + 손바닥 정면 + 위 방향

# 랜드마크 인덱스 정의
WRIST = 0
THUMB_TIP = 4
INDEX_MCP, INDEX_TIP = 5, 8
MIDDLE_MCP, MIDDLE_TIP = 9, 12
RING_MCP, RING_TIP = 13, 16
PINKY_MCP, PINKY_TIP = 17, 20
FINGER_TIPS = (THUMB_TIP, INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP)


def _is_palm_facing_camera(landmarks, threshold: float = 0.02) -> bool:
    """
    손바닥이 카메라를 향하고 있는지 판별.
    MediaPipe z: 손목 기준 상대 깊이, 값이 작을수록 카메라에 가까움.
    손바닥이 카메라를 향하면 손가락 끝이 손목보다 카메라 쪽(z 작음)에 있음.
    """
    wrist_z = landmarks[WRIST].z
    tips_z = [landmarks[i].z for i in FINGER_TIPS]
    mean_tip_z = sum(tips_z) / len(tips_z)
    # 손가락 끝이 손목보다 카메라에 가깝거나 비슷하면 손바닥 정면
    return mean_tip_z <= wrist_z + threshold


def _get_hand_state(landmarks):
    """
    손가락 마디의 Y좌표를 비교하여 상태 판별.
    카메라 좌표계에서 위쪽일수록 y값이 작음.
    """
    # 1. 손끝이 위를 향하는지 확인 (손목보다 중지 뿌리가 위에 있어야 함)
    # 최소한 손이 수직으로 세워져 있는 상태인지 체크
    if landmarks[MIDDLE_MCP].y > landmarks[WRIST].y:
        return "IGNORE"

    # 2. 손가락 펴짐 여부 확인 (MCP와 TIP의 Y좌표 비교)
    # 팁(TIP)이 뿌리(MCP)보다 위에(y값이 작게) 있으면 펴진 것으로 간주
    fingers = [INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP]
    mcps = [INDEX_MCP, MIDDLE_MCP, RING_MCP, PINKY_MCP]
    
    is_open_list = [landmarks[tip].y < landmarks[mcp].y for tip, mcp in zip(fingers, mcps)]
    open_count = sum(is_open_list)

    # 보 (모든 손가락이 펴짐)
    if open_count >= 4:
        return "OPEN"
    # 주먹 (모든 손가락이 MCP보다 아래로 내려감)
    if open_count == 0:
        return "FIST"
    
    return "IGNORE"

def _draw_landmarks_on_frame(frame_bgr, result, motion_active: bool):
    """모션 인식이 켜져 있으면 컬러, 꺼져 있으면 회색으로 랜드마크 표시."""
    if not result.hand_landmarks:
        return
    h, w = frame_bgr.shape[:2]

    if motion_active:
        color = (255, 200, 100)  # BGR 밝은 파랑 (모션 인식 중)
        thickness = 3
    else:
        color = (160, 160, 160)  # BGR 회색 (대기)
        thickness = 1

    for hand_landmarks in result.hand_landmarks:
        pts = [(int(lm.x * w), int(lm.y * h)) for lm in hand_landmarks]
        for pt in pts:
            cv2.circle(frame_bgr, pt, 4, color, -1)
        for i, j in HAND_CONNECTIONS:
            cv2.line(frame_bgr, pts[i], pts[j], color, thickness)

class PostureTriggerDetector:
    def __init__(self):
        # 환경에 맞춰 config.MODELS_DIR 사용
        model_path = os.path.join(config.MODELS_DIR, "hand_landmarker.task")
        base_options = mp_tasks.BaseOptions(model_asset_path=model_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=2,
            min_hand_detection_confidence=0.7, # 정확도를 위해 상향
            min_hand_presence_confidence=0.7,
            min_tracking_confidence=0.7,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)

    def _detect(self, frame_bgr):
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        return self._landmarker.detect(mp_image)

    def _result_to_trigger(self, result, motion_active: bool) -> TriggerResult:
        # 반드시 두 손이 다 보여야 함
        if not result.hand_landmarks or len(result.hand_landmarks) < 2:
            return TriggerResult.NONE

        hands = result.hand_landmarks
        hand_states = [_get_hand_state(h) for h in hands]
        palm_facing = [_is_palm_facing_camera(h) for h in hands]
        both_palm = palm_facing[0] and palm_facing[1]

        # 모션 인식 중: 종료 제스처(STOP)만 판단
        if motion_active:
            if both_palm and hand_states[0] == "FIST" and hand_states[1] == "FIST":
                return TriggerResult.STOP
            return TriggerResult.NONE

        # 모션 인식 대기: 시작 제스처(START)만 판단
        if both_palm and hand_states[0] == "OPEN" and hand_states[1] == "OPEN":
            return TriggerResult.START
        return TriggerResult.NONE

    def process(self, frame_bgr, motion_active: bool = False) -> TriggerResult:
        result = self._detect(frame_bgr)
        return self._result_to_trigger(result, motion_active)

    def process_annotated(self, frame_bgr, motion_active: bool = False):
        result = self._detect(frame_bgr)
        trigger = self._result_to_trigger(result, motion_active)
        annotated = frame_bgr.copy()
        _draw_landmarks_on_frame(annotated, result, motion_active)
        return trigger, annotated

    def close(self):
        if self._landmarker:
            self._landmarker.close()