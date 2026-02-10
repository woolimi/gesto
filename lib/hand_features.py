"""
MediaPipe Hands 기반 손 랜드마크 상수 및 11채널 피처 계산.
- 데이터 수집(collect_mp), 변환(data_converter), 앱 인식(lstm_gesture_base)에서 공통 사용.
- landmarks: (21, 3) 또는 21개 [x,y,z] 리스트. list/ndarray 모두 지원.
"""

import numpy as np

# Feature Indices (저장/추론 시 사용하는 채널 번호)
# --- 원본 좌표 ---
# 0: x - 랜드마크 x (이미지 너비 기준 0~1 정규화)
# 1: y - 랜드마크 y (이미지 높이 기준 0~1 정규화)
# 2: z - 랜드마크 z (손목 기준 상대 깊이, 단위 비율)
# --- 왼손 파생 피처 ---
# 3: Is_Fist (Left) - 왼손 주먹 여부. 1.0=주먹(검지·중지·약지·새끼 네 손가락이 접힘), 0.0=펴진 손
# 4: Pinch_Dist (Left) - 왼손 엄지 끝과 검지 끝 사이 거리. 핀치(꼬집기) 제스처 강도, 0에 가까우면 꼬집은 상태
# 5: Thumb_V (Left) - 왼손 엄지 끝의 y방향 속도(이전 프레임 대비 변화량). 위·아래 움직임 감지용
# 6: Index_Z_V (Left) - 왼손 검지 끝의 z방향 속도. 카메라 쪽/멀리(앞뒤) 움직임 감지용
# --- 오른손 파생 피처 ---
# 7: Is_Fist (Right) - 오른손 주먹 여부 (3번과 동일 정의)
# 8: Pinch_Dist (Right) - 오른손 엄지–검지 거리 (4번과 동일 정의)
# 9: Thumb_V (Right) - 오른손 엄지 y방향 속도 (5번과 동일 정의)
# 10: Index_Z_V (Right) - 오른손 검지 z방향 속도 (6번과 동일 정의)
NUM_CHANNELS = 11

# Landmark Indices (MediaPipe Hands)
WRIST = 0
THUMB_TIP = 4
INDEX_MCP = 5
INDEX_PIP = 6
INDEX_TIP = 8
MIDDLE_PIP = 10
MIDDLE_TIP = 12
RING_PIP = 14
RING_TIP = 16
PINKY_PIP = 18
PINKY_TIP = 20


def calculate_euclidean_dist(p1, p2):
    """두 점 사이 유클리드 거리. list 또는 ndarray 모두 지원."""
    return float(np.linalg.norm(np.asarray(p1) - np.asarray(p2)))


def _fist_curled_mask(landmarks):
    """4손가락(검지·중지·약지·새끼) 각각 접힘 여부. 접힘: Dist(손목,TIP) < Dist(손목,PIP). 반환: (값 0|1, [검지,중지,약지,새끼] bool 리스트)."""
    landmarks = np.asarray(landmarks)
    wrist = landmarks[WRIST]
    fingers = [
        (INDEX_PIP, INDEX_TIP),
        (MIDDLE_PIP, MIDDLE_TIP),
        (RING_PIP, RING_TIP),
        (PINKY_PIP, PINKY_TIP),
    ]
    curled = []
    for pip_idx, tip_idx in fingers:
        dist_tip = calculate_euclidean_dist(wrist, landmarks[tip_idx])
        dist_pip = calculate_euclidean_dist(wrist, landmarks[pip_idx])
        curled.append(dist_pip > 1e-6 and dist_tip < dist_pip)
    val = 1.0 if sum(curled) == 4 else 0.0
    return (val, curled)


def is_fist(landmarks):
    """
    손이 주먹 상태인지 판별.
    조건: 4손가락(검지·중지·약지·새끼) 모두 접혀 있어야 1.0.
    접힘: Dist(손목, 끝) < Dist(손목, PIP). 회전에 강함.
    """
    val, _ = _fist_curled_mask(landmarks)
    return val


def is_fist_debug(landmarks):
    """
    GESTURE_DEBUG용. is_fist 판정과 손가락별 접힘 여부 반환.
    반환: (0.0|1.0, [검지접힘, 중지접힘, 약지접힘, 새끼접힘] bool 4개)
    """
    return _fist_curled_mask(landmarks)


def process_hand_features(landmarks, prev_landmarks):
    """
    한 손(21 랜드마크)에 대해 4개 피처 계산.
    반환: [Is_Fist, Pinch_Dist, Thumb_V, Index_Z_V]
    """
    landmarks = np.asarray(landmarks)
    fist_val = is_fist(landmarks)
    pinch_dist = calculate_euclidean_dist(landmarks[THUMB_TIP], landmarks[INDEX_TIP])

    thumb_v = 0.0
    index_z_v = 0.0
    if prev_landmarks is not None:
        prev_landmarks = np.asarray(prev_landmarks)
        thumb_v = float(landmarks[THUMB_TIP][1] - prev_landmarks[THUMB_TIP][1])
        index_z_v = float(landmarks[INDEX_TIP][2] - prev_landmarks[INDEX_TIP][2])

    return [fist_val, pinch_dist, thumb_v, index_z_v]
