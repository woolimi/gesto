import sys
import os
import cv2
import numpy as np
import time
from PyQt6.QtWidgets import QApplication, QFileDialog

# 프로젝트 루트 경로 추가 (config 및 기타 모듈 로드용)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    import mediapipe as mp
    mp_hands = mp.solutions.hands
    HAND_CONNECTIONS = mp_hands.HAND_CONNECTIONS
except ImportError:
    # MediaPipe가 없을 경우 수동으로 연결 정의 (표준 손 랜드마크 연결)
    HAND_CONNECTIONS = [
        (0, 1), (1, 2), (2, 3), (3, 4),      # 엄지
        (0, 5), (5, 6), (6, 7), (7, 8),      # 검지
        (0, 9), (9, 10), (10, 11), (11, 12), # 중지
        (0, 13), (13, 14), (14, 15), (15, 16), # 약지
        (0, 17), (17, 18), (18, 19), (19, 20)  # 새끼
    ]

def draw_landmarks(image, landmarks):
    h, w, _ = image.shape
    
    # 랜드마크 좌표 변환 (0.0~1.0 -> 픽셀 좌표)
    # npy 데이터는 (21, 3) 형태라고 가정 (x, y, z)
    
    coords = []
    for point in landmarks:
        x, y = int(point[0] * w), int(point[1] * h)
        coords.append((x, y))
        
    # 연결선 그리기
    for connection in HAND_CONNECTIONS:
        start_idx = connection[0]
        end_idx = connection[1]
        
        if start_idx < len(coords) and end_idx < len(coords):
            cv2.line(image, coords[start_idx], coords[end_idx], (0, 255, 0), 2)
            
    # 관절 점 그리기
    for x, y in coords:
        cv2.circle(image, (x, y), 4, (0, 0, 255), -1)

def visualize_npy(file_path):
    print(f"Loading: {file_path}")
    try:
        data = np.load(file_path)
    except Exception as e:
        print(f"Error loading file: {e}")
        return

    print(f"Data Shape: {data.shape}")
    
    # 데이터 형태 확인
    # 3차원: (Frames, 21, 3)
    # 2차원: (Frames, 63) -> reshape 필요
    if data.ndim == 2 and data.shape[1] == 63:
        print("Reshaping 2D data to 3D...")
        data = data.reshape(-1, 21, 3)
    elif data.ndim == 3 and data.shape[1] == 21 and data.shape[2] == 3:
        pass
    else:
        print("Unsupported data shape. Expected (Frames, 21, 3) or (Frames, 63).")
        return

    # 캔버스 설정
    WIDTH, HEIGHT = 640, 480
    FPS = 30
    delay = int(1000 / FPS)
    
    print("Press 'q' to quit, 'r' to replay.")

    while True:
        for i, frame_landmarks in enumerate(data):
            # 검은 배경 생성
            canvas = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
            
            # 텍스트 정보
            cv2.putText(canvas, f"Frame: {i}/{len(data)}", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
            cv2.putText(canvas, f"File: {os.path.basename(file_path)}", (10, 450), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
            
            # 그리기
            draw_landmarks(canvas, frame_landmarks)
            
            cv2.imshow("NPY Visualizer", canvas)
            
            key = cv2.waitKey(delay) & 0xFF
            if key == ord('q'):
                return
            if key == ord('p'): # 일시정지
                cv2.waitKey(-1)

        # 재생 끝난 후 대기
        key = cv2.waitKey(0) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):
            continue # 재시작
        else:
            break

    cv2.destroyAllWindows()

def select_file():
    app = QApplication(sys.argv)
    file_path, _ = QFileDialog.getOpenFileName(
        None, 
        "Select NPY File", 
        os.path.join(os.path.dirname(__file__), "data"), 
        "Numpy Files (*.npy);;All Files (*)"
    )
    return file_path

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_file = sys.argv[1]
    else:
        target_file = select_file()
        
    if target_file:
        visualize_npy(target_file)
    else:
        print("No file selected.")
