import cv2
import numpy as np
import time
import sys
import os
import mediapipe as mp

# 프로젝트 루트를 경로에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import config
from app.recognition.lstm_gesture_base import LstmGestureBase

def main():
    print(f"카메라 인덱스: {config.CAMERA_INDEX}")
    print("인식기 초기화 중...")
    
    # 인식기 초기화
    try:
        recognizer = LstmGestureBase(cooldown_sec=0.5, confidence_threshold=0.5)
    except Exception as e:
        print(f"인식기 초기화 실패: {e}")
        return

    # MediaPipe 그리기 유틸리티
    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils
    mp_drawing_styles = mp.solutions.drawing_styles

    # 카메라 열기
    # config.CAMERA_INDEX가 "/dev/video32" 문자열일 수 있으므로 처리
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
        
        # 인식 처리
        gesture, confidence = recognizer.process(frame)
        
        if gesture:
            last_gesture = gesture
            last_confidence = confidence

        # 시각화 (인식기 내부의 MediaPipe 객체 활용이 어려우면 여기서 별도로 돌리거나 
        # 인식기를 수정해야 하지만, 간단하게 구현하기 위해 현재 프레임에 텍스트만 표시)
        
        # 결과 표시
        cv2.putText(frame, f"Gesture: {last_gesture}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, f"Conf: {last_confidence:.2f}", (10, 70), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # 쿨다운 상태 표시
        now = time.monotonic()
        if now < recognizer.cooldown_until:
            cv2.putText(frame, "COOLDOWN", (10, 110), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        cv2.imshow("Webcam Gesture Validation", frame)

        if cv2.waitKey(1) & 0xFF == 27: # ESC
            break

    recognizer.close()
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
