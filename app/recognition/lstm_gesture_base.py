"""
공통 LSTM 제스처 인식기 (Pinch_In/Out_Left/Right, Swipe_Left/Right).
mp.solutions.hands (Legacy) → 시퀀스 버퍼 → lstm_legacy.tflite 추론.
학습 데이터(collect_mp)와 동일한 파이프라인 사용.
Ubuntu: tflite-runtime 또는 tensorflow. Mac: tensorflow (tf.lite).
"""

import os
import time
from collections import deque
from typing import Any, Callable, Optional

import cv2
import numpy as np
import mediapipe as mp

import config

# 학습 시와 동일 (data_trainer/train.py) — 두 손: 42 랜드마크, 30프레임(1초)
SEQUENCE_LENGTH = 30
LANDMARKS_COUNT = 42
COORDS_COUNT = 11
INPUT_SHAPE = (SEQUENCE_LENGTH, LANDMARKS_COUNT * COORDS_COUNT)

# Feature Indices
# 0-2: x, y, z
# 3: Is_Fist (Left)
# 4: Pinch_Dist (Left)
# 5: Thumb_V (Left)
# 6: Index_Z_V (Left)
# 7: Is_Fist (Right)
# 8: Pinch_Dist (Right)
# 9: Thumb_V (Right)
# 10: Index_Z_V (Right)
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


def _load_gesture_classes(models_dir: str, base_name: str = "lstm_legacy") -> list:
    """학습 시 저장한 레이블 순서 로드. 없으면 기본 순서."""
    path = os.path.join(models_dir, f"{base_name}_labels.txt")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            classes = [line.strip() for line in f if line.strip()]
        if classes:
            return classes
    return [
        "Pinch_In_Left", "Pinch_In_Right",
        "Pinch_Out_Left", "Pinch_Out_Right",
        "Swipe_Left", "Swipe_Right",
    ]


def _normalize_landmarks(data: np.ndarray) -> np.ndarray:
    """
    랜드마크 정규화: 손목(0, 21) 기준 상대 좌표. (frames, 21, 3) 또는 (frames, 42, 3).
    """
    n_landmarks = data.shape[1]
    if n_landmarks == 21:
        wrist = data[:, 0:1, :]
        normalized = data - wrist
        scale = np.max(np.abs(normalized), axis=(1, 2), keepdims=True) + 1e-6
        return (normalized / scale).astype(np.float32)
    normalized = np.zeros_like(data, dtype=np.float32)
    
    # Copy all channels first (features are passed through)
    normalized = data.copy()
    
    for start in (0, 21):
        end = start + 21
        # Extract xyz only (Channels 0-2)
        wrist = data[:, start : start + 1, 0:3]
        part = data[:, start:end, 0:3] - wrist
        
        # Scale based on xyz max value
        scale = np.max(np.abs(part), axis=(1, 2), keepdims=True) + 1e-6
        
        # Update normalized xyz
        normalized[:, start:end, 0:3] = part / scale
        
    return normalized


class LstmGestureBase:
    """
    lstm_legacy.tflite + mp.solutions.hands (Legacy) 기반 4종 제스처 인식.
    학습 데이터(collect_mp)와 동일한 랜드마크 파이프라인 사용.
    process(frame_bgr) → Pinch_In/Out_Left/Right | Swipe_Left/Right | None.
    """

    def __init__(
        self,
        cooldown_sec: float,
        get_confidence_threshold: Optional[Callable[[], float]] = None,
        confidence_threshold: Optional[float] = None,
    ):
        # 민감도 통일: getter 없으면 config 기본 감도 → threshold 사용
        self._get_confidence_threshold = get_confidence_threshold
        if get_confidence_threshold is None:
            self._confidence_threshold = (
                confidence_threshold
                if confidence_threshold is not None
                else config.sensitivity_to_confidence_threshold(config.SENSITIVITY_DEFAULT)
            )
        else:
            self._confidence_threshold = 0.5  # getter 사용 시 미사용
        self._cooldown_sec = cooldown_sec
        self._cooldown_until = 0.0
        self._buffer: deque = deque(maxlen=SEQUENCE_LENGTH)
        self._last_probs: dict = {}  # 인식 시 모든 클래스 확률 (UI 표시용)

        # mp.solutions.hands (Legacy) — 학습 데이터 수집(collect_mp)과 동일, 두 손
        self._mp_hands = mp.solutions.hands
        self._hands = self._mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        tflite_path = os.path.join(config.MODELS_DIR, "lstm_legacy.tflite")
        if not os.path.isfile(tflite_path):
            raise RuntimeError(
                f"LSTM 모델 파일이 없습니다: {tflite_path} "
                "(app/models/lstm_legacy.tflite 필요)"
            )
        self._gesture_classes = _load_gesture_classes(config.MODELS_DIR)
        InterpreterClass = self._get_tflite_interpreter_class()
        self._interpreter: Any = InterpreterClass(model_path=tflite_path)
        self._interpreter.allocate_tensors()
        
        # Velocity calculation state
        self._prev_right = None
        self._prev_left = None

    def _calculate_euclidean_dist(self, p1, p2):
        return np.linalg.norm(p1 - p2)

    def _is_fist(self, landmarks):
        """
        Check if the hand is in a fist state (Robust, Rotation-Invariant).
        Condition: Dist(Wrist, Tip) < Dist(Wrist, PIP) for ALL 4 fingers.
        """
        wrist = landmarks[WRIST]
        
        fingers = [
            (INDEX_PIP, INDEX_TIP),
            (MIDDLE_PIP, MIDDLE_TIP),
            (RING_PIP, RING_TIP),
            (PINKY_PIP, PINKY_TIP)
        ]
        
        curled_count = 0
        for pip_idx, tip_idx in fingers:
            dist_tip = self._calculate_euclidean_dist(wrist, landmarks[tip_idx])
            dist_pip = self._calculate_euclidean_dist(wrist, landmarks[pip_idx])
            if dist_tip < dist_pip:
                curled_count += 1
                
        return 1.0 if curled_count == 4 else 0.0

    def _process_hand_features(self, landmarks, prev_landmarks):
        """
        Calculate 4 features for a single hand (21 landmarks).
        Features: [Is_Fist, Pinch_Dist, Thumb_V, Index_Z_V]
        """
        # 1. Is_Fist
        fist_val = self._is_fist(landmarks)
        
        # 2. Pinch_Dist (Thumb Tip - Index Tip)
        pinch_dist = self._calculate_euclidean_dist(landmarks[THUMB_TIP], landmarks[INDEX_TIP])
        
        # 3. Thumb_V (y velocity)
        thumb_v = 0.0
        if prev_landmarks is not None:
            thumb_v = landmarks[THUMB_TIP][1] - prev_landmarks[THUMB_TIP][1]
            
        # 4. Index_Z_V (z velocity)
        index_z_v = 0.0
        if prev_landmarks is not None:
            index_z_v = landmarks[INDEX_TIP][2] - prev_landmarks[INDEX_TIP][2]
            
        return [fist_val, pinch_dist, thumb_v, index_z_v]

    @property
    def cooldown_until(self) -> float:
        """쿨다운 종료 시각 (time.monotonic()). UI와 시작/종료 시각 공유용."""
        return self._cooldown_until

    @property
    def last_probs(self) -> dict:
        """마지막 인식 시 모든 클래스별 확률 (클래스명 → 0~1). UI 표시용."""
        return self._last_probs.copy()

    def _get_tflite_interpreter_class(self):
        """tflite_runtime(우분투) 또는 tensorflow.lite(맥/우분투) 반환."""
        try:
            from tflite_runtime.interpreter import Interpreter
            return Interpreter
        except (ImportError, ModuleNotFoundError):
            pass
        try:
            import tensorflow as tf
            if hasattr(tf, "lite") and hasattr(tf.lite, "Interpreter"):
                return tf.lite.Interpreter
        except Exception:
            pass
        try:
            from tensorflow.lite.python.interpreter import Interpreter
            return Interpreter
        except Exception:
            pass
        raise RuntimeError(
            "TFLite 로드를 위해 tensorflow가 필요합니다: pip install tensorflow "
            "(Ubuntu에서는 pip install tflite-runtime 도 가능)"
        )

    def _get_landmarks_from_frame(self, frame_bgr) -> np.ndarray:
        """BGR 프레임에서 두 손 랜드마크 (42, 3) 반환. handedness로 순서 고정: Right=0~20, Left=21~41."""
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        results = self._hands.process(rgb)
        zero_hand = np.zeros((21, 3), dtype=np.float32)
        right_slot = zero_hand.copy()
        left_slot = zero_hand.copy()
        if results.multi_hand_landmarks and results.multi_handedness:
            for hlm, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                label = handedness.classification[0].label if handedness.classification else ""
                arr = np.array([[lm.x, lm.y, lm.z] for lm in hlm.landmark], dtype=np.float32)
                if label == "Right":
                    right_slot = arr
                else:
                    left_slot = arr
        return np.vstack([right_slot, left_slot])  # (42, 3)

    def _construct_11_channel_data(self, landmarks: np.ndarray) -> np.ndarray:
        """
        (42, 3) landmarks -> (42, 11) data with features.
        Updates self._prev_right and self._prev_left.
        """
        # Right: 0-20, Left: 21-41
        right_hand = landmarks[0:21, :]
        left_hand = landmarks[21:42, :]
        
        # Calculate Features
        left_feats = self._process_hand_features(left_hand, self._prev_left)
        right_feats = self._process_hand_features(right_hand, self._prev_right)
        
        # Update state
        self._prev_right = right_hand.copy()
        self._prev_left = left_hand.copy()
        
        # Create (42, 11) array
        new_data = np.zeros((42, NUM_CHANNELS), dtype=np.float32)
        new_data[:, 0:3] = landmarks
        
        # Assign features to all landmarks (broadcasting)
        # Left Hand Features (Channels 3-6)
        new_data[:, 3] = left_feats[0] # Is_Fist
        new_data[:, 4] = left_feats[1] # Pinch_Dist
        new_data[:, 5] = left_feats[2] # Thumb_V
        new_data[:, 6] = left_feats[3] # Index_Z_V
        
        # Right Hand Features (Channels 7-10)
        new_data[:, 7] = right_feats[0] # Is_Fist
        new_data[:, 8] = right_feats[1] # Pinch_Dist
        new_data[:, 9] = right_feats[2] # Thumb_V
        new_data[:, 10] = right_feats[3] # Index_Z_V
        
        return new_data

    def process(self, frame_bgr) -> tuple[Optional[str], float]:
        """
        한 프레임 처리. 버퍼가 찼을 때만 추론.
        반환: ("Pinch_In", confidence) | (None, 0.0).
        """
        landmarks = self._get_landmarks_from_frame(frame_bgr)
        if landmarks is None:
            return None, 0.0

        # (42, 3) → (42, 11) Feature Extraction
        data_11ch = self._construct_11_channel_data(landmarks)

        # (42, 11) → (1, 42, 11) 정규화 후 (462,)로 버퍼에 추가
        data = np.expand_dims(data_11ch, axis=0)
        data = _normalize_landmarks(data)
        row = data.reshape(-1).astype(np.float32)
        self._buffer.append(row)

        if len(self._buffer) < SEQUENCE_LENGTH:
            return None, 0.0

        # (30, 126) → (1, 30, 126) 배치로 추론
        input_data = np.array(self._buffer, dtype=np.float32)
        input_data = np.expand_dims(input_data, axis=0)

        input_details = self._interpreter.get_input_details()
        output_details = self._interpreter.get_output_details()
        self._interpreter.set_tensor(input_details[0]["index"], input_data)
        self._interpreter.invoke()
        output = self._interpreter.get_tensor(output_details[0]["index"])  # (1, 4)
        probs = output[0]
        pred_idx = int(np.argmax(probs))
        confidence = float(probs[pred_idx])
        # 매 추론마다 UI용 확률 갱신 (threshold 통과 여부와 무관)
        self._last_probs = {
            self._gesture_classes[i]: float(probs[i])
            for i in range(len(probs))
        }
        threshold = (
            self._get_confidence_threshold()
            if self._get_confidence_threshold is not None
            else self._confidence_threshold
        )
        if confidence < threshold:
            return None, 0.0
        now = time.monotonic()
        if now < self._cooldown_until:
            return None, 0.0
        self._cooldown_until = now + self._cooldown_sec

        return self._gesture_classes[pred_idx], confidence

    def close(self) -> None:
        if self._hands:
            self._hands.close()
            self._hands = None
        self._buffer.clear()
        self._prev_right = None
        self._prev_left = None
