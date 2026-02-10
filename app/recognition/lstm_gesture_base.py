"""
공통 LSTM 제스처 인식기 (Pinch_In/Out_Left/Right, Swipe_Left/Right).
mp.solutions.hands (Legacy) → 시퀀스 버퍼 → lstm_legacy.tflite 추론.
학습 데이터(collect_mp)와 동일한 파이프라인 사용.
Ubuntu: tflite-runtime 또는 tensorflow. Mac: tensorflow (tf.lite).
"""

import os
import sys
import time
from collections import deque
from typing import Any, Callable, Optional

import cv2
import numpy as np
import mediapipe as mp

import config

# 프로젝트 루트를 path에 추가 (lib 임포트용)
_root = os.path.dirname(os.path.abspath(config.__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)

from lib.hand_features import NUM_CHANNELS, process_hand_features, is_fist_debug

# 학습 시와 동일 (data_trainer/train.py) — 두 손: 42 랜드마크, 30프레임(1초)
SEQUENCE_LENGTH = 30
LANDMARKS_COUNT = 42
INPUT_SHAPE = (SEQUENCE_LENGTH, LANDMARKS_COUNT * NUM_CHANNELS)


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
        "Play_Pause_Left", "Play_Pause_Right",
        "Volume_Down_Left", "Volume_Down_Right",
        "Volume_Up_Left", "Volume_Up_Right",
        "No_Gesture",
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
        
        # --- Optimization: Cache TFLite Details ---
        self._input_details = self._interpreter.get_input_details()
        self._output_details = self._interpreter.get_output_details()
        self._input_index = self._input_details[0]["index"]
        self._output_index = self._output_details[0]["index"]
        
        # --- Optimization: Pre-allocated Circular Buffer ---
        # (SEQUENCE_LENGTH, 462) shaped buffer
        self._buffer_array = np.zeros((SEQUENCE_LENGTH, LANDMARKS_COUNT * NUM_CHANNELS), dtype=np.float32)
        self._buffer_count = 0
        
        # Velocity calculation state
        self._prev_right = None
        self._prev_left = None
        
        # Pre-allocated feature array to avoid re-allocation
        self._feature_array = np.zeros((LANDMARKS_COUNT, NUM_CHANNELS), dtype=np.float32)
        # GESTURE_DEBUG: 마지막 프레임 11채널 평균, is_fist 손가락별 판정
        self._last_11ch_means = [0.0] * NUM_CHANNELS
        self._last_fist_debug = {"left": (0.0, [False] * 4), "right": (0.0, [False] * 4)}

    @property
    def cooldown_until(self) -> float:
        """쿨다운 종료 시각 (time.monotonic()). UI와 시작/종료 시각 공유용."""
        return self._cooldown_until

    @property
    def last_probs(self) -> dict:
        """마지막 인식 시 모든 클래스별 확률 (클래스명 → 0~1). UI 표시용."""
        return self._last_probs.copy()

    @property
    def last_11ch_means(self) -> list:
        """GESTURE_DEBUG용. 마지막 프레임 11채널 값(채널별 42 랜드마크 평균)."""
        return list(self._last_11ch_means)

    @property
    def last_fist_debug(self) -> dict:
        """GESTURE_DEBUG용. 마지막 프레임 왼/오 is_fist 판정 및 손가락별 접힘: {"left": (0|1, [4 bool]), "right": ...}."""
        return dict(self._last_fist_debug)

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

    def _get_landmarks_from_raw(self, multi_hand_landmarks, multi_handedness) -> np.ndarray:
        """전달받은 landmarks (list)에서 두 손 랜드마크 (42, 3) 반환. handedness로 순서 고정."""
        zero_hand = np.zeros((21, 3), dtype=np.float32)
        right_slot = zero_hand.copy()
        left_slot = zero_hand.copy()
        if multi_hand_landmarks and multi_handedness:
            for hlm, handedness in zip(multi_hand_landmarks, multi_handedness):
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
        
        # Calculate Features (lib: collect_mp와 동일 파이프라인)
        left_feats = process_hand_features(left_hand, self._prev_left)
        right_feats = process_hand_features(right_hand, self._prev_right)
        if getattr(config, "GESTURE_DEBUG", False):
            self._last_fist_debug["left"] = is_fist_debug(left_hand)
            self._last_fist_debug["right"] = is_fist_debug(right_hand)
        # Update state
        self._prev_right = right_hand.copy()
        self._prev_left = left_hand.copy()
        
        # Use pre-allocated (42, 11) array
        self._feature_array.fill(0)
        self._feature_array[:, 0:3] = landmarks
        
        # Assign features to all landmarks (broadcasting)
        # Left Hand Features (Channels 3-6)
        self._feature_array[:, 3] = left_feats[0] # Is_Fist
        self._feature_array[:, 4] = left_feats[1] # Pinch_Dist
        self._feature_array[:, 5] = left_feats[2] # Thumb_V
        self._feature_array[:, 6] = left_feats[3] # Index_Z_V
        
        # Right Hand Features (Channels 7-10)
        self._feature_array[:, 7] = right_feats[0] # Is_Fist
        self._feature_array[:, 8] = right_feats[1] # Pinch_Dist
        self._feature_array[:, 9] = right_feats[2] # Thumb_V
        self._feature_array[:, 10] = right_feats[3] # Index_Z_V
        
        return self._feature_array

    def process_landmarks(self, multi_hand_landmarks, multi_handedness) -> tuple[Optional[str], float]:
        """외부에서 추출한 landmarks 리스트를 처리하여 추론."""
        landmarks = self._get_landmarks_from_raw(multi_hand_landmarks, multi_handedness)
        return self._inference(landmarks)

    def process(self, frame_bgr) -> tuple[Optional[str], float]:
        # Legacy: 더 이상 내부에서 프레임을 처리하지 않음.
        return None, 0.0

    def _inference(self, landmarks: np.ndarray) -> tuple[Optional[str], float]:
        """(42, 3) landmarks를 받아 LSTM 추론 수행. 매 프레임 버퍼에 추가해 시퀀스 연속성 유지; 추론 결과만 '다른 손 주먹'으로 검사."""
        # (42, 3) → (42, 11) Feature Extraction
        data_11ch = self._construct_11_channel_data(landmarks)

        # 버퍼는 매 프레임 갱신 (전제조건으로 막으면 시퀀스 끊김·같은 30프레임만 반복 추론되어 성능 저하)
        # (42, 11) → (1, 42, 11) 정규화 후 (462,)로 버퍼에 추가
        data_11ch = _normalize_landmarks(data_11ch[np.newaxis, ...])[0]
        row = data_11ch.reshape(-1)

        # GESTURE_DEBUG: 채널별 평균 저장
        for c in range(NUM_CHANNELS):
            self._last_11ch_means[c] = float(np.mean(row[c * LANDMARKS_COUNT : (c + 1) * LANDMARKS_COUNT]))

        # 쿨다운 중에는 버퍼에 넣지 않음 (같은 제스처가 연속 인식되는 것 방지)
        now = time.monotonic()
        if now < self._cooldown_until:
            return None, 0.0

        # Circular buffer management
        if self._buffer_count < SEQUENCE_LENGTH:
            self._buffer_array[self._buffer_count] = row
            self._buffer_count += 1
        else:
            # Shift left and add at the end (could be optimized further with an actual circular index, 
            # but for 30 frames, np.roll or slicing is acceptable and simpler)
            self._buffer_array[:-1] = self._buffer_array[1:]
            self._buffer_array[-1] = row

        if self._buffer_count < SEQUENCE_LENGTH:
            return None, 0.0

        # (30, 462) → (1, 30, 462) 배치로 추론
        input_data = self._buffer_array[np.newaxis, ...]

        self._interpreter.set_tensor(self._input_index, input_data)
        self._interpreter.invoke()
        output = self._interpreter.get_tensor(self._output_index)  # (1, 6)
        probs = output[0]
        pred_idx = int(np.argmax(probs))
        confidence = float(probs[pred_idx])
        
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

        gesture_name = self._gesture_classes[pred_idx]
        
        # No_Gesture가 예측되면 None 반환 (액션 실행하지 않음)
        if gesture_name == "No_Gesture":
            return None, 0.0
        
        # LSTM 사용 시: 제스처 손이 아닌 "다른 손"이 반드시 주먹이어야 함.
        # 양손 모두 보일 때만 제스처 인정 (한 손만 보이면 무시).
        row = self._buffer_array[-1]
        # 왼손 fist: 랜드마크 21-41의 채널 3, 오른손 fist: 랜드마크 0-20의 채널 7
        left_fist = float(np.mean([row[i * NUM_CHANNELS + 3] for i in range(21, LANDMARKS_COUNT)]))
        right_fist = float(np.mean([row[i * NUM_CHANNELS + 7] for i in range(21)]))
        # 양손 가시성: xyz 채널(0-2)의 절댓값으로 판단
        left_xyz_max = max(
            (max(abs(row[i * NUM_CHANNELS + 0]), abs(row[i * NUM_CHANNELS + 1]), abs(row[i * NUM_CHANNELS + 2]))
             for i in range(21, LANDMARKS_COUNT))
        )
        right_xyz_max = max(
            (max(abs(row[i * NUM_CHANNELS + 0]), abs(row[i * NUM_CHANNELS + 1]), abs(row[i * NUM_CHANNELS + 2]))
             for i in range(21))
        )
        left_visible = left_xyz_max > 0.01
        right_visible = right_xyz_max > 0.01
        
        # 양손 모두 보여야 제스처 인정
        if not (left_visible and right_visible):
            return None, 0.0
        
        # 다른 손이 주먹이어야 함. Swipe만 규칙이 다름.
        # Swipe_Left: 왼손 주먹, 오른손이 스와이프 → 왼손 fist
        # Swipe_Right: 오른손 주먹, 왼손이 스와이프 → 오른손 fist
        # 그 외 (Pinch, Play_Pause, Volume 등): _Left = 왼손이 제스처 → 오른손 주먹, _Right = 오른손 제스처 → 왼손 주먹
        if gesture_name.startswith("Swipe_"):
            if gesture_name.endswith("_Left"):
                if left_fist < 0.5:
                    return None, 0.0
            elif gesture_name.endswith("_Right"):
                if right_fist < 0.5:
                    return None, 0.0
        else:
            # Pinch_In_Left, Play_Pause_Left 등: 제스처하는 손의 반대가 주먹
            if gesture_name.endswith("_Left"):
                if right_fist < 0.5:
                    return None, 0.0
            elif gesture_name.endswith("_Right"):
                if left_fist < 0.5:
                    return None, 0.0

        self._cooldown_until = now + self._cooldown_sec
        # 제스처 인식 시 버퍼 초기화 (같은 시퀀스가 쿨다운 후 즉시 재인식되는 것 방지)
        self._buffer_count = 0
        self._buffer_array.fill(0)
        return gesture_name, confidence

    def close(self) -> None:
        self._buffer_count = 0
        self._buffer_array.fill(0)
        self._prev_right = None
        self._prev_left = None
        self._last_11ch_means = [0.0] * NUM_CHANNELS
        self._last_fist_debug = {"left": (0.0, [False] * 4), "right": (0.0, [False] * 4)}
