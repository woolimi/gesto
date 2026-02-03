"""
공통 LSTM 제스처 인식기 (Pinch_In, Pinch_Out, Swipe_Left, Swipe_Right).
MediaPipe Hand Landmarker → 시퀀스 버퍼 → lstm_legacy.tflite 추론.
학습 시 사용한 정규화·입력 shape와 동일하게 맞춤.
Ubuntu: tflite-runtime 또는 tensorflow. Mac: tensorflow (tf.lite).
"""

import os
import time
from collections import deque
from typing import Any, Callable, Optional

import cv2
import numpy as np
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision
import mediapipe as mp

import config

# 학습 시와 동일 (data_trainer/train.py)
SEQUENCE_LENGTH = 45
LANDMARKS_COUNT = 21
COORDS_COUNT = 3
INPUT_SHAPE = (SEQUENCE_LENGTH, LANDMARKS_COUNT * COORDS_COUNT)

# 클래스 순서: load_data에서 Gesture 폴더 알파벳 순 → Pinch_In, Pinch_Out, Swipe_Left, Swipe_Right
LSTM_GESTURE_CLASSES = ["Pinch_In", "Pinch_Out", "Swipe_Left", "Swipe_Right"]

# 추론 옵션
CONFIDENCE_THRESHOLD = 0.5
COOLDOWN_SEC = 0.6


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
    lstm_legacy.tflite + MediaPipe Hand Landmarker 기반 4종 제스처 인식.
    process(frame_bgr) → "Pinch_In" | "Pinch_Out" | "Swipe_Left" | "Swipe_Right" | None.
    """

    def __init__(
        self,
        confidence_threshold: float = CONFIDENCE_THRESHOLD,
        cooldown_sec: float = COOLDOWN_SEC,
        get_confidence_threshold: Optional[Callable[[], float]] = None,
    ):
        self._confidence_threshold = confidence_threshold
        self._get_confidence_threshold = get_confidence_threshold  # 감도 실시간 반영용
        self._cooldown_sec = cooldown_sec
        self._cooldown_until = 0.0
        self._buffer: deque = deque(maxlen=SEQUENCE_LENGTH)

        # MediaPipe Hand Landmarker
        hand_model_path = os.path.join(config.MODELS_DIR, "hand_landmarker.task")
        base_options = mp_tasks.BaseOptions(model_asset_path=hand_model_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=1,
            min_hand_detection_confidence=0.25,
            min_hand_presence_confidence=0.25,
            min_tracking_confidence=0.25,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)

        tflite_path = os.path.join(config.MODELS_DIR, "lstm_legacy.tflite")
        if not os.path.isfile(tflite_path):
            raise RuntimeError(
                f"LSTM 모델 파일이 없습니다: {tflite_path} "
                "(app/models/lstm_legacy.tflite 필요)"
            )
        InterpreterClass = self._get_tflite_interpreter_class()
        self._interpreter: Any = InterpreterClass(model_path=tflite_path)
        self._interpreter.allocate_tensors()

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
        """BGR 프레임에서 첫 번째 손의 랜드마크 (21, 3) 반환. 없으면 None."""
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect(mp_image)
        if not result.hand_landmarks:
            return None
        hand = result.hand_landmarks[0]
        arr = np.array([[lm.x, lm.y, lm.z] for lm in hand], dtype=np.float32)
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
        if self._landmarker:
            self._landmarker.close()
            self._landmarker = None
        self._buffer.clear()
