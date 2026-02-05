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

def draw_landmarks(image, landmarks, two_hands=False):
    """랜드마크 그리기. landmarks: (21, 3) 한 손 또는 (42, 3) 두 손(오른손 0~20, 왼손 21~41). 좌표는 0~1 정규화."""
    h, w, _ = image.shape
    colors = [(0, 255, 0), (255, 165, 0)]  # 오른손 초록, 왼손 주황

    if two_hands and len(landmarks) >= 42:
        # 두 손: 오른손 0~20, 왼손 21~41 (collect_mp 저장 형식)
        chunks = [landmarks[:21], landmarks[21:42]]
    else:
        chunks = [landmarks[:21]]

    for hand_idx, hand_pts in enumerate(chunks):
        color = colors[hand_idx] if two_hands else (0, 255, 0)
        coords = []
        for point in hand_pts:
            x, y = int(point[0] * w), int(point[1] * h)
            coords.append((x, y))
        for connection in HAND_CONNECTIONS:
            if connection[0] < len(coords) and connection[1] < len(coords):
                cv2.line(image, coords[connection[0]], coords[connection[1]], color, 2)
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
    num_frames = data.shape[0]

    # 데이터 형태: (Frames, 21, 3) 한 손 / (Frames, 42, 3) 두 손(collect_mp) / (Frames, 63) 플랫
    if data.ndim == 2 and data.shape[1] == 63:
        data = data.reshape(-1, 21, 3)
        two_hands = False
    elif data.ndim == 3 and data.shape[1] == 21 and data.shape[2] == 3:
        two_hands = False
    elif data.ndim == 3 and data.shape[1] == 42 and data.shape[2] == 3:
        two_hands = True  # 오른손 0~20, 왼손 21~41
    else:
        print("Unsupported data shape. Expected (Frames, 21, 3), (Frames, 42, 3), or (Frames, 63).")
        return

    # 캔버스 설정
    WIDTH, HEIGHT = 640, 480
    FPS = 30
    delay = int(1000 / FPS)
    
    print(f"Frames: {num_frames} (q=quit, p=pause, r=replay)")

    while True:
        for i, frame_landmarks in enumerate(data):
            canvas = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
            cv2.putText(canvas, f"Frame: {i + 1}/{num_frames}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
            cv2.putText(canvas, f"File: {os.path.basename(file_path)}", (10, 450),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
            draw_landmarks(canvas, frame_landmarks, two_hands=two_hands)
            
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
