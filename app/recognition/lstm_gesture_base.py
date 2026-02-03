"""
공통 LSTM 제스처 인식기 (Pinch_In, Pinch_Out, Swipe_Left, Swipe_Right).
mp.solutions.hands (Legacy) → 시퀀스 버퍼 → lstm_legacy.tflite 추론.
학습 데이터(collect_mp_legacy)와 동일한 파이프라인 사용.
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

# 학습 시와 동일 (data_trainer/train.py)
SEQUENCE_LENGTH = 45
LANDMARKS_COUNT = 21
COORDS_COUNT = 3
INPUT_SHAPE = (SEQUENCE_LENGTH, LANDMARKS_COUNT * COORDS_COUNT)

# 클래스 순서: load_data에서 Gesture 폴더 알파벳 순 → Pinch_In, Pinch_Out, Swipe_Left, Swipe_Right
LSTM_GESTURE_CLASSES = ["Pinch_In", "Pinch_Out", "Swipe_Left", "Swipe_Right"]


def _normalize_landmarks(data: np.ndarray) -> np.ndarray:
    """
    랜드마크 정규화: 손목(랜드마크 0) 기준 상대 좌표 + 스케일 정규화.
    data: (frames, 21, 3) → (frames, 21, 3)
    """
    wrist = data[:, 0:1, :]
    normalized = data - wrist
    scale = np.max(np.abs(normalized), axis=(1, 2), keepdims=True) + 1e-6
    normalized = normalized / scale
    return normalized.astype(np.float32)


class LstmGestureBase:
    """
    lstm_legacy.tflite + mp.solutions.hands (Legacy) 기반 4종 제스처 인식.
    학습 데이터(collect_mp_legacy)와 동일한 랜드마크 파이프라인 사용.
    process(frame_bgr) → "Pinch_In" | "Pinch_Out" | "Swipe_Left" | "Swipe_Right" | None.
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

        # mp.solutions.hands (Legacy) — 학습 데이터 수집(collect_mp_legacy)과 동일
        self._mp_hands = mp.solutions.hands
        self._hands = self._mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        tflite_path = os.path.join(config.MODELS_DIR, "lstm_legacy.tflite")
        if not os.path.isfile(tflite_path):
            raise RuntimeError(
                f"LSTM 모델 파일이 없습니다: {tflite_path} "
                "(app/models/lstm_legacy.tflite 필요)"
            )
        InterpreterClass = self._get_tflite_interpreter_class()
        self._interpreter: Any = InterpreterClass(model_path=tflite_path)
        self._interpreter.allocate_tensors()

    @property
    def cooldown_until(self) -> float:
        """쿨다운 종료 시각 (time.monotonic()). UI와 시작/종료 시각 공유용."""
        return self._cooldown_until

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

    def _get_landmarks_from_frame(self, frame_bgr) -> Optional[np.ndarray]:
        """BGR 프레임에서 첫 번째 손의 랜드마크 (21, 3) 반환. 없으면 None. Legacy API 사용."""
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        results = self._hands.process(rgb)
        if not results.multi_hand_landmarks:
            return None
        hls = results.multi_hand_landmarks[0]
        arr = np.array([[lm.x, lm.y, lm.z] for lm in hls.landmark], dtype=np.float32)
        return arr  # (21, 3)

    def process(self, frame_bgr) -> Optional[str]:
        """
        한 프레임 처리. 버퍼가 찼을 때만 추론.
        반환: "Pinch_In" | "Pinch_Out" | "Swipe_Left" | "Swipe_Right" | None.
        """
        landmarks = self._get_landmarks_from_frame(frame_bgr)
        if landmarks is None:
            return None

        # (21, 3) → (1, 21, 3) 정규화 후 (63,)로 버퍼에 추가
        data = np.expand_dims(landmarks, axis=0)
        data = _normalize_landmarks(data)
        row = data.reshape(-1).astype(np.float32)
        self._buffer.append(row)

        if len(self._buffer) < SEQUENCE_LENGTH:
            return None

        # (45, 63) → (1, 45, 63) 배치로 추론
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
        threshold = (
            self._get_confidence_threshold()
            if self._get_confidence_threshold is not None
            else self._confidence_threshold
        )
        if confidence < threshold:
            return None
        now = time.monotonic()
        if now < self._cooldown_until:
            return None
        self._cooldown_until = now + self._cooldown_sec

        return LSTM_GESTURE_CLASSES[pred_idx]

    def close(self) -> None:
        if self._hands:
            self._hands.close()
            self._hands = None
        self._buffer.clear()
