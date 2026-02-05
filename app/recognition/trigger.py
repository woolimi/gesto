import os
import time
from enum import Enum
from types import SimpleNamespace

import cv2
import mediapipe as mp

import config

# Hand Landmarker 21점 연결
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8),
    (0, 9), (9, 10), (10, 11), (11, 12), (0, 13), (13, 14), (14, 15), (15, 16),
    (0, 17), (17, 18), (18, 19), (19, 20), (5, 9), (9, 13), (13, 17),
]

# 같은 포즈를 이만큼 유지해야 트리거 발생 (초)
TRIGGER_HOLD_DURATION_SEC = 3.0


class TriggerResult(str, Enum):
    NONE = "none"
    START = "start"   # 양손 펴기 + 손바닥 정면 + 위 방향
    STOP = "stop"     # 양손 주먹 + 손바닥 정면 + 위 방향
    ALWAYS_ON_TOP_ON = "aot_on"   # 한 손 검지 위로
    ALWAYS_ON_TOP_OFF = "aot_off" # 한 손 검지 아래로

# 랜드마크 인덱스 정의
WRIST = 0
THUMB_TIP = 4
INDEX_MCP, INDEX_PIP, INDEX_TIP = 5, 6, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_TIP = 9, 10, 12
RING_MCP, RING_PIP, RING_TIP = 13, 14, 16
PINKY_MCP, PINKY_PIP, PINKY_TIP = 17, 18, 20
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
    # 2. 손가락 펴짐 여부 확인 (MCP와 TIP의 Y좌표 비교)
    # 팁(TIP)이 뿌리(MCP)보다 위에(y값이 작게) 있으면 펴진 것으로 간주
    fingers_tip = [INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP]
    mcps = [INDEX_MCP, MIDDLE_MCP, RING_MCP, PINKY_MCP]
    pips = [INDEX_PIP, MIDDLE_PIP, RING_PIP, PINKY_PIP]

    is_open_list = [landmarks[tip].y < landmarks[mcp].y for tip, mcp in zip(fingers_tip, mcps)]
    open_count = sum(is_open_list)

    # 보 (모든 손가락이 펴짐)
    if open_count >= 4:
        # 방향 체크 (MCP가 손목보다 위에 있을 때만 모션인식 시작용)
        if landmarks[MIDDLE_MCP].y < landmarks[WRIST].y:
            return "OPEN"
            
    # 주먹: 모든 손가락이 접혀 있음
    if open_count == 0:
        # MCP가 손목보다 위에 있을 때만 모션인식 종료용
        if landmarks[MIDDLE_MCP].y < landmarks[WRIST].y:
            pip_above_tip = all(landmarks[pip].y < landmarks[tip].y for pip, tip in zip(pips, fingers_tip))
            if pip_above_tip:
                return "FIST"
    
    # 검지 손가락 위/아래 제스처 판별 (Always on Top용)
    # 1. 검지 손가락 확장 여부 확인
    index_extended = landmarks[INDEX_TIP].y < landmarks[INDEX_PIP].y < landmarks[INDEX_MCP].y
    index_pointing_down = landmarks[INDEX_TIP].y > landmarks[INDEX_PIP].y > landmarks[INDEX_MCP].y
    
    # 2. 나머지 손가락 접힘 여부 확인
    others_folded = all(landmarks[tip].y > landmarks[mcp].y for tip, mcp in zip([MIDDLE_TIP, RING_TIP, PINKY_TIP], [MIDDLE_MCP, RING_MCP, PINKY_MCP]))

    if others_folded:
        if index_extended: return "INDEX_UP"
        if index_pointing_down: return "INDEX_DOWN"

    return "IGNORE"

def _draw_landmarks_on_frame(frame_bgr, result, motion_active: bool):
    """모션 인식이 켜져 있으면 컬러, 꺼져 있으면 회색으로 랜드마크 표시."""
    if not result.hand_landmarks:
        return
    h, w = frame_bgr.shape[:2]

    if motion_active:
        # BRAND THEME: Cyan connections, Magenta joints
        color_core = (255, 255, 255)    # Pure White core for skin contrast
        glow_conn = (255, 230, 0)       # Neon Cyan (BGR)
        glow_joint = (255, 0, 255)      # Neon Magenta (BGR)
                
        thickness_glow = 5
        thickness_core = 1
        
        for hand_landmarks in result.hand_landmarks:
            pts = [(int(lm.x * w), int(lm.y * h)) for lm in hand_landmarks]
            
            # 1. Draw Connections (Cyan Glow + White Core)
            for i, j in HAND_CONNECTIONS:
                cv2.line(frame_bgr, pts[i], pts[j], glow_conn, thickness_glow)
                cv2.line(frame_bgr, pts[i], pts[j], color_core, thickness_core)
                
            # 2. Draw Joint Nodes (Magenta Glow + White Core)
            for pt in pts:
                cv2.circle(frame_bgr, pt, 5, glow_joint, -1)
                cv2.circle(frame_bgr, pt, 2, color_core, -1)
    else:
        # Standby: Muted grayscale
        color_mute = (80, 80, 80)
        color_mute_core = (150, 150, 150)
        for hand_landmarks in result.hand_landmarks:
            pts = [(int(lm.x * w), int(lm.y * h)) for lm in hand_landmarks]
            for i, j in HAND_CONNECTIONS:
                cv2.line(frame_bgr, pts[i], pts[j], color_mute, 2)
            for pt in pts:
                cv2.circle(frame_bgr, pt, 3, color_mute_core, -1)

class PostureTriggerDetector:
    """mp.solutions.hands (Solution API) 기반 트리거 감지."""

    def __init__(self, hold_duration_sec: float = TRIGGER_HOLD_DURATION_SEC):
        self._hold_duration_sec = hold_duration_sec
        self._hold_candidate: TriggerResult | None = None
        self._hold_since: float = 0.0
        self._mp_hands = mp.solutions.hands
        self._hands = self._mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7,
        )

    def _detect(self, frame_bgr):
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        results = self._hands.process(rgb)
        out = SimpleNamespace()
        out.hand_landmarks = [h.landmark for h in (results.multi_hand_landmarks or [])]
        return out

    def _result_to_trigger(self, result, motion_active: bool) -> TriggerResult:
        if not result.hand_landmarks:
            return TriggerResult.NONE

        hands = result.hand_landmarks
        hand_states = [_get_hand_state(h) for h in hands]
        
        # Always on Top: ONE hand is enough
        if "INDEX_UP" in hand_states:
            return TriggerResult.ALWAYS_ON_TOP_ON
        if "INDEX_DOWN" in hand_states:
            return TriggerResult.ALWAYS_ON_TOP_OFF

        # START/STOP: Requires TWO hands
        if len(hands) < 2:
            return TriggerResult.NONE

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

    def _apply_hold_duration(self, raw: TriggerResult) -> TriggerResult:
        """동일 포즈가 hold_duration_sec 이상 유지될 때만 START/STOP 반환."""
        if raw == TriggerResult.NONE:
            self._hold_candidate = None
            self._hold_since = 0.0
            return TriggerResult.NONE

        now = time.monotonic()
        if raw != self._hold_candidate:
            self._hold_candidate = raw
            self._hold_since = now
            return TriggerResult.NONE

        if now - self._hold_since >= self._hold_duration_sec:
            self._hold_candidate = None
            self._hold_since = 0.0
            return raw
        return TriggerResult.NONE

    def process(self, frame_bgr, motion_active: bool = False) -> TriggerResult:
        result = self._detect(frame_bgr)
        raw = self._result_to_trigger(result, motion_active)
        return self._apply_hold_duration(raw)

    def process_annotated(self, frame_bgr, motion_active: bool = False):
        result = self._detect(frame_bgr)
        raw = self._result_to_trigger(result, motion_active)
        trigger = self._apply_hold_duration(raw)
        annotated = frame_bgr.copy()
        _draw_landmarks_on_frame(annotated, result, motion_active)
        return trigger, annotated

    def close(self):
        if self._hands:
            self._hands.close()
            self._hands = None