import cv2
import numpy as np
import time
import sys
import os
import mediapipe as mp
from types import SimpleNamespace

# 프로젝트 루트를 경로에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import config
from app.recognition.lstm_gesture_base import LstmGestureBase
from app.recognition.trigger import _draw_landmarks_on_frame

def main():
    print(f"카메라 인덱스: {config.CAMERA_INDEX}")
    print("인식기 초기화 중...")
    
    # 인식기 초기화
    try:
        recognizer = LstmGestureBase(cooldown_sec=0.5, confidence_threshold=0.5)
    except Exception as e:
        print(f"인식기 초기화 실패: {e}")
        return

    # MediaPipe 초기화 (validate_inference.py는 CameraWorker를 쓰지 않으므로 직접 초기화)
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7,
    )

    # 카메라 열기
    cap = cv2.VideoCapture(config.CAMERA_INDEX, cv2.CAP_V4L2)
    
    if not cap.isOpened():
        print(f"카메라를 열 수 없습니다: {config.CAMERA_INDEX}")
        return

    print("인식 시작 (ESC를 누르면 종료)...")
    
    last_gesture = "None"
    last_confidence = 0.0

    while True:
        ret, frame = cap.read()
        if not ret:
            print("프레임을 읽을 수 없습니다.")
            break

        # 프레임 좌우 반전
        frame = cv2.flip(frame, 1)
        
        # MediaPipe 처리
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)

        # 인식 처리 (process_landmarks 사용)
        if results.multi_hand_landmarks:
            gesture, confidence = recognizer.process_landmarks(
                results.multi_hand_landmarks, 
                results.multi_handedness
            )
            
            if gesture:
                last_gesture = gesture
                last_confidence = confidence

        # 시각화 (중앙 집중형 그리기 함수 사용)
        annotated_frame = frame.copy()
        if results.multi_hand_landmarks:
            draw_res = SimpleNamespace()
            draw_res.hand_landmarks = [h.landmark for h in results.multi_hand_landmarks]
            _draw_landmarks_on_frame(annotated_frame, draw_res, motion_active=True)
        
        # 결과 표시
        cv2.putText(annotated_frame, f"Gesture: {last_gesture}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(annotated_frame, f"Conf: {last_confidence:.2f}", (10, 60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        # 쿨다운 상태 표시
        now = time.monotonic()
        if now < recognizer.cooldown_until:
            cv2.putText(annotated_frame, "COOLDOWN", (10, 90), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        cv2.imshow("Webcam Gesture Validation (Centralized Logic)", annotated_frame)

        if cv2.waitKey(1) & 0xFF == 27: # ESC
            break

    recognizer.close()
    hands.close()
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
