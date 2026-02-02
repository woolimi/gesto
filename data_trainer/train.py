import os
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.utils import to_categorical
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt

# 경로 설정
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data_collector', 'data'))
LEGACY_DATA_DIR = os.path.join(DATA_DIR, 'legacy')
TASKS_DATA_DIR = os.path.join(DATA_DIR, 'tasks')
MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'models'))

# 하이퍼파라미터
SEQUENCE_LENGTH = 45 # 1.5초 * 30fps
LANDMARKS_COUNT = 21
COORDS_COUNT = 3
INPUT_SHAPE = (SEQUENCE_LENGTH, LANDMARKS_COUNT * COORDS_COUNT)
EPOCHS = 50
BATCH_SIZE = 16

def load_data(data_dir):
    """
    특정 디렉토리(legacy 또는 tasks)에서 데이터를 로드합니다.
    구조: data_dir/<Mode>/<GestureName>/*.npy
    Mode는 무시하고 GestureName을 레이블로 사용합니다.
    """
    X = []
    y = []
    labels = []
    label_map = {}
    
    if not os.path.exists(data_dir):
        print(f"경고: 디렉토리 {data_dir}가 존재하지 않습니다.")
        return np.array(X), np.array(y), label_map

    # 모든 하위 디렉토리를 순회하여 제스처 폴더 찾기
    # data_dir/Gesture/GestureName 또는 data_dir/Posture/GestureName 가정
    
    # 알려진 모드 'Gesture'와 'Posture' 탐색
    modes = ['Gesture', 'Posture']
    
    current_label_id = 0
    
    for mode in modes:
        mode_path = os.path.join(data_dir, mode)
        if not os.path.exists(mode_path):
            continue
            
        gestures = os.listdir(mode_path)
        for gesture in gestures:
            gesture_path = os.path.join(mode_path, gesture)
            if not os.path.isdir(gesture_path):
                continue
                
            if gesture not in label_map:
                label_map[gesture] = current_label_id
                labels.append(gesture)
                current_label_id += 1
            
            label_id = label_map[gesture]
            
            # 모든 .npy 파일 로드
            for file in os.listdir(gesture_path):
                if file.endswith('.npy'):
                    file_path = os.path.join(gesture_path, file)
                    try:
                        data = np.load(file_path)
                        # 데이터 모양은 (Frames, 21, 3)
                        # SEQUENCE_LENGTH 프레임을 갖도록 보장해야 함.
                        # 부족하면 패딩, 넘치면 자름.
                        if data.shape[0] > SEQUENCE_LENGTH:
                             data = data[:SEQUENCE_LENGTH]
                        elif data.shape[0] < SEQUENCE_LENGTH:
                            # 0으로 패딩
                            padding = np.zeros((SEQUENCE_LENGTH - data.shape[0], 21, 3))
                            data = np.vstack((data, padding))
                        
                        # 랜드마크 평탄화: (45, 21, 3) -> (45, 63)
                        data_flat = data.reshape(SEQUENCE_LENGTH, -1)
                        
                        X.append(data_flat)
                        y.append(label_id)
                    except Exception as e:
                        print(f"Error loading {file_path}: {e}")
                        
    return np.array(X), np.array(y), label_map

def create_model(num_classes):
    model = Sequential([
        LSTM(64, return_sequences=True, activation='relu', input_shape=INPUT_SHAPE),
        LSTM(128, return_sequences=False, activation='relu'),
        Dense(64, activation='relu'),
        Dense(32, activation='relu'),
        Dense(num_classes, activation='softmax')
    ])
    model.compile(optimizer='Adam', loss='categorical_crossentropy', metrics=['categorical_accuracy'])
    return model

def train_model(X, y, save_path, model_name):
    if len(X) == 0:
        print(f"{model_name}에 대한 데이터가 없어 학습을 건너뜁니다.")
        return None, None

    # 레이블 원-핫 인코딩
    num_classes = len(np.unique(y))
    y_encoded = to_categorical(y, num_classes=num_classes)
    
    X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42)
    
    model = create_model(num_classes)
    
    print(f"{model_name} 학습 시작...")
    history = model.fit(X_train, y_train, epochs=EPOCHS, batch_size=BATCH_SIZE, validation_data=(X_test, y_test))
    
    model.save(save_path)
    print(f"{model_name} 저장 완료: {save_path}")
    return history, model

def plot_comparison(history_legacy, history_tasks):
    plt.figure(figsize=(12, 5))
    
    # Accuracy
    plt.subplot(1, 2, 1)
    if history_legacy:
        plt.plot(history_legacy.history['categorical_accuracy'], label='Legacy Train Acc')
        plt.plot(history_legacy.history['val_categorical_accuracy'], label='Legacy Val Acc')
    if history_tasks:
        plt.plot(history_tasks.history['categorical_accuracy'], label='Tasks Train Acc')
        plt.plot(history_tasks.history['val_categorical_accuracy'], label='Tasks Val Acc')
    plt.title('Model Accuracy')
    plt.ylabel('Accuracy')
    plt.xlabel('Epoch')
    plt.legend()
    
    # Loss
    plt.subplot(1, 2, 2)
    if history_legacy:
        plt.plot(history_legacy.history['loss'], label='Legacy Train Loss')
        plt.plot(history_legacy.history['val_loss'], label='Legacy Val Loss')
    if history_tasks:
        plt.plot(history_tasks.history['loss'], label='Tasks Train Loss')
        plt.plot(history_tasks.history['val_loss'], label='Tasks Val Loss')
    plt.title('Model Loss')
    plt.ylabel('Loss')
    plt.xlabel('Epoch')
    plt.legend()
    
    plt.tight_layout()
    plt.show()

def main():
    os.makedirs(MODELS_DIR, exist_ok=True)
    
    print("Legacy 데이터 로딩 중...")
    X_legacy, y_legacy, label_map_legacy = load_data(LEGACY_DATA_DIR)
    print(f"Legacy 데이터: {X_legacy.shape}, 클래스: {label_map_legacy}")
    
    print("Tasks 데이터 로딩 중...")
    X_tasks, y_tasks, label_map_tasks = load_data(TASKS_DATA_DIR)
    print(f"Tasks 데이터: {X_tasks.shape}, 클래스: {label_map_tasks}")
    
    # Train Legacy
    history_legacy = None
    if len(X_legacy) > 0:
        save_path = os.path.join(MODELS_DIR, 'lstm_legacy.h5')
        history_legacy, _ = train_model(X_legacy, y_legacy, save_path, "Legacy Model")
        
    # Train Tasks
    history_tasks = None
    if len(X_tasks) > 0:
        save_path = os.path.join(MODELS_DIR, 'lstm_tasks.h5')
        history_tasks, _ = train_model(X_tasks, y_tasks, save_path, "Tasks Model")
        
    # Plot
    if history_legacy or history_tasks:
        plot_comparison(history_legacy, history_tasks)
    else:
        print("No models were trained.")

if __name__ == "__main__":
    main()
