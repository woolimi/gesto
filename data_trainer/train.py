import os
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.regularizers import l2
from tensorflow.keras.utils import to_categorical
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns

# 경로 설정
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data_collector', 'data'))
LEGACY_DATA_DIR = os.path.join(DATA_DIR, 'legacy')
MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'models'))

# 하이퍼파라미터
SEQUENCE_LENGTH = 45  # 1.5초 * 30fps
LANDMARKS_COUNT = 21
COORDS_COUNT = 3
INPUT_SHAPE = (SEQUENCE_LENGTH, LANDMARKS_COUNT * COORDS_COUNT)
EPOCHS = 100  # Early stopping으로 실제로는 더 적게 학습될 수 있음
BATCH_SIZE = 16

def normalize_landmarks(data):
    """
    랜드마크 정규화: 손목(랜드마크 0)을 기준으로 상대 좌표로 변환
    
    Args:
        data: (frames, 21, 3) shape의 numpy array
    
    Returns:
        정규화된 데이터 (frames, 21, 3)
    """
    # 손목 좌표를 기준으로 상대 좌표 변환
    wrist = data[:, 0:1, :]  # (frames, 1, 3)
    normalized = data - wrist  # 손목 기준 상대 좌표
    
    # 스케일 정규화 (손 크기 차이 보정)
    scale = np.max(np.abs(normalized), axis=(1, 2), keepdims=True) + 1e-6
    normalized = normalized / scale
    
    return normalized

def augment_data(X, y, augmentation_factor=2):
    """
    데이터 증강: 노이즈 추가로 학습 데이터 증가
    
    Args:
        X: 입력 데이터 (N, 45, 63)
        y: 레이블 데이터 (N,)
        augmentation_factor: 증강 배수 (기본 2배)
    
    Returns:
        증강된 X, y
    """
    X_aug = []
    y_aug = []
    
    for i in range(len(X)):
        # 원본 데이터
        X_aug.append(X[i])
        y_aug.append(y[i])
        
        # 증강 버전들
        for _ in range(augmentation_factor - 1):
            # 가우시안 노이즈 추가
            noise = np.random.normal(0, 0.01, X[i].shape)
            X_aug.append(X[i] + noise)
            y_aug.append(y[i])
    
    return np.array(X_aug), np.array(y_aug)

def load_data(data_dir, apply_normalization=True):
    """
    특정 디렉토리(legacy 또는 tasks)에서 데이터를 로드합니다.
    구조: data_dir/<Mode>/<GestureName>/*.npy
    Mode는 무시하고 GestureName을 레이블로 사용합니다.
    
    Args:
        data_dir: 데이터 디렉토리 경로
        apply_normalization: 정규화 적용 여부
    
    Returns:
        X, y, label_map
    """
    X = []
    y = []
    labels = []
    label_map = {}
    
    if not os.path.exists(data_dir):
        print(f"경고: 디렉토리 {data_dir}가 존재하지 않습니다.")
        return np.array(X), np.array(y), label_map

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
                        
                        # 정규화 적용
                        if apply_normalization:
                            data = normalize_landmarks(data)
                        
                        # SEQUENCE_LENGTH 프레임을 갖도록 보장
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
    """
    개선된 LSTM 모델 생성
    - 경량화된 아키텍처 (추론 속도 개선)
    - Dropout 추가 (과적합 방지)
    - L2 정규화 추가 (일반화 성능 개선)
    """
    model = Sequential([
        LSTM(64, return_sequences=True, input_shape=INPUT_SHAPE),
        Dropout(0.3),
        LSTM(64, return_sequences=False),
        Dropout(0.3),
        Dense(32, activation='relu', kernel_regularizer=l2(0.01)),
        Dense(num_classes, activation='softmax')
    ])
    
    model.compile(
        optimizer='Adam',
        loss='categorical_crossentropy',
        metrics=['categorical_accuracy']
    )
    
    return model

def save_tflite_model(model, save_path):
    """
    TensorFlow Lite 모델로 변환하여 저장 (Robust Version)
    
    Args:
        model: Keras 모델
        save_path: .h5 파일 경로
    """
    import tempfile
    
    tflite_path = save_path.replace('.h5', '.tflite')
    print(f"🔄 TFLite 변환 시작...")
    
    try:
        # 안전한 변환을 위해 임시 디렉토리에 SavedModel로 먼저 저장
        # 이는 Keras 모델을 직접 변환할 때 발생하는 그래프 동결 문제를 방지합니다.
        with tempfile.TemporaryDirectory() as temp_dir:
            model.export(temp_dir) # Keras 3 export 사용
            
            # SavedModel에서 컨버터 생성
            converter = tf.lite.TFLiteConverter.from_saved_model(temp_dir)
            
            # TF Ops 지원 추가 (LSTM 등 복잡한 레이어 호환성 및 LLVM 에러 방지)
            converter.target_spec.supported_ops = [
                tf.lite.OpsSet.TFLITE_BUILTINS, # TFLite 기본 Ops
                tf.lite.OpsSet.SELECT_TF_OPS    # TF Ops (필요시 사용)
            ]
            
            # 양자화 및 변환 시도
            try:
                converter.optimizations = [tf.lite.Optimize.DEFAULT]
                tflite_model = converter.convert()
                quantized = True
            except Exception as quant_error:
                print(f"⚠️ 양자화 실패, 기본 변환 시도: {quant_error}")
                # 컨버터 재설정 (SavedModel 다시 로드 불필요, 옵션만 변경 불가하므로 재생성 권장)
                converter = tf.lite.TFLiteConverter.from_saved_model(temp_dir)
                converter.target_spec.supported_ops = [
                    tf.lite.OpsSet.TFLITE_BUILTINS,
                    tf.lite.OpsSet.SELECT_TF_OPS
                ]
                tflite_model = converter.convert()
                quantized = False

            # 파일 저장
            with open(tflite_path, 'wb') as f:
                f.write(tflite_model)
            
            # 결과 출력
            h5_size = os.path.getsize(save_path) / 1024  # KB
            tflite_size = os.path.getsize(tflite_path) / 1024  # KB
            print(f"✅ TFLite 모델 저장 완료: {tflite_path}")
            print(f"   H5 모델 크기: {h5_size:.2f} KB")
            print(f"   TFLite 모델 크기: {tflite_size:.2f} KB (압축률: {(1 - tflite_size/h5_size)*100:.1f}%)")
            print(f"   모드: {'양자화 (Quantized)' if quantized else '일반 (Float32)'} + TF Ops")
            
    except Exception as e:
        print(f"❌ TFLite 변환 실패: {e}")
        print(f"   H5 모델은 정상적으로 저장되었습니다.")

def evaluate_model(model, X_test, y_test, label_map):
    """
    모델 평가 및 상세 메트릭 출력
    
    Args:
        model: 학습된 모델
        X_test: 테스트 데이터
        y_test: 테스트 레이블 (one-hot encoded)
        label_map: 레이블 매핑 딕셔너리
    
    Returns:
        confusion matrix
    """
    # 예측
    y_pred = model.predict(X_test, verbose=0)
    y_pred_classes = np.argmax(y_pred, axis=1)
    y_test_classes = np.argmax(y_test, axis=1)
    
    # Classification Report
    print("\n" + "="*70)
    print("📊 Classification Report")
    print("="*70)
    
    # label_map을 정렬하여 target_names 생성
    sorted_labels = sorted(label_map.items(), key=lambda x: x[1])
    target_names = [label for label, _ in sorted_labels]
    
    print(classification_report(y_test_classes, y_pred_classes, 
                                target_names=target_names,
                                digits=4))
    
    # Confusion Matrix
    cm = confusion_matrix(y_test_classes, y_pred_classes)
    
    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=target_names,
                yticklabels=target_names)
    plt.title('Confusion Matrix', fontsize=14, fontweight='bold')
    plt.ylabel('True Label', fontsize=12)
    plt.xlabel('Predicted Label', fontsize=12)
    plt.tight_layout()
    
    cm_path = os.path.join(MODELS_DIR, 'confusion_matrix.png')
    plt.savefig(cm_path, dpi=150)
    print(f"\n✅ Confusion Matrix 저장됨: {cm_path}")
    plt.show()
    
    return cm

def train_model(X, y, save_path, model_name, apply_augmentation=True):
    """
    개선된 모델 학습 함수
    
    Args:
        X: 입력 데이터
        y: 레이블
        save_path: 모델 저장 경로
        model_name: 모델 이름
        apply_augmentation: 데이터 증강 적용 여부
    
    Returns:
        history, model
    """
    if len(X) == 0:
        print(f"{model_name}에 대한 데이터가 없어 학습을 건너뜁니다.")
        return None, None

    # 데이터 증강 (학습 데이터가 적을 경우 유용)
    if apply_augmentation:
        print("📈 데이터 증강 적용 중...")
        X, y = augment_data(X, y, augmentation_factor=2)
        print(f"   증강 후 데이터 개수: {len(X)}")

    # 클래스 가중치 계산 (클래스 불균형 처리)
    class_weights = compute_class_weight('balanced', classes=np.unique(y), y=y)
    class_weight_dict = dict(enumerate(class_weights))
    print(f"⚖️ 클래스 가중치: {class_weight_dict}")

    # 레이블 원-핫 인코딩
    num_classes = len(np.unique(y))
    y_encoded = to_categorical(y, num_classes=num_classes)
    
    # Train-Test Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"📊 학습 데이터: {X_train.shape}, 검증 데이터: {X_test.shape}")
    
    # 모델 생성
    model = create_model(num_classes)
    
    # 모델 아키텍처 출력
    print("\n🏗️ 모델 아키텍처:")
    model.summary()
    
    # 콜백 설정
    callbacks = [
        # Early Stopping: 10 에포크 동안 개선 없으면 중단
        EarlyStopping(
            monitor='val_loss',
            patience=10,
            restore_best_weights=True,
            verbose=1
        ),
        
        # Model Checkpoint: 최고 성능 모델 저장
        ModelCheckpoint(
            save_path,
            save_best_only=True,
            monitor='val_loss',
            verbose=0
        ),
        
        # Learning Rate Reduction: 5 에포크 동안 개선 없으면 학습률 감소
        ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=5,
            min_lr=1e-6,
            verbose=1
        )
    ]
    
    print(f"\n🚀 {model_name} 학습 시작...")
    print("="*70)
    
    # 모델 학습
    history = model.fit(
        X_train, y_train,
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        validation_data=(X_test, y_test),
        class_weight=class_weight_dict,
        callbacks=callbacks,
        verbose=1
    )
    
    print(f"\n✅ {model_name} 저장 완료: {save_path}")
    
    # TFLite 모델 저장
    save_tflite_model(model, save_path)
    
    # 상세 평가
    print("\n" + "="*70)
    print("🔍 모델 평가 중...")
    print("="*70)
    
    # label_map 재구성 (y에서 역으로 추출)
    label_map = {}
    for i in range(num_classes):
        label_map[f"Class_{i}"] = i
    
    evaluate_model(model, X_test, y_test, label_map)
    
    return history, model

def plot_training_history(history):
    """
    학습 히스토리 시각화
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Accuracy
    axes[0].plot(history.history['categorical_accuracy'], label='Train Acc', linewidth=2)
    axes[0].plot(history.history['val_categorical_accuracy'], label='Val Acc', linewidth=2)
    axes[0].set_title('Model Accuracy', fontsize=14, fontweight='bold')
    axes[0].set_ylabel('Accuracy', fontsize=12)
    axes[0].set_xlabel('Epoch', fontsize=12)
    axes[0].legend(loc='lower right')
    axes[0].grid(True, alpha=0.3)
    
    # Loss
    axes[1].plot(history.history['loss'], label='Train Loss', linewidth=2)
    axes[1].plot(history.history['val_loss'], label='Val Loss', linewidth=2)
    axes[1].set_title('Model Loss', fontsize=14, fontweight='bold')
    axes[1].set_ylabel('Loss', fontsize=12)
    axes[1].set_xlabel('Epoch', fontsize=12)
    axes[1].legend(loc='upper right')
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # 저장
    history_path = os.path.join(MODELS_DIR, 'training_history.png')
    plt.savefig(history_path, dpi=150)
    print(f"✅ 학습 히스토리 저장됨: {history_path}")
    plt.show()

def main():
    os.makedirs(MODELS_DIR, exist_ok=True)
    
    print("="*70)
    print("🧠 LSTM Gesture Recognition Model Training")
    print("="*70)
    
    print("\n📂 Legacy 데이터 로딩 중...")
    X_legacy, y_legacy, label_map_legacy = load_data(LEGACY_DATA_DIR, apply_normalization=True)
    print(f"✅ Legacy 데이터: {X_legacy.shape}, 클래스: {label_map_legacy}")
    
    # Train Legacy
    if len(X_legacy) > 0:
        save_path = os.path.join(MODELS_DIR, 'lstm_legacy.h5')
        history, model = train_model(
            X_legacy, y_legacy, save_path, "Legacy Model",
            apply_augmentation=True
        )
        
        # Plot training history
        if history:
            print("\n📈 학습 히스토리 시각화 중...")
            plot_training_history(history)
            
        print("\n" + "="*70)
        print("🎉 모델 학습 완료!")
        print("="*70)
        print(f"📁 저장된 파일:")
        print(f"   - {save_path}")
        print(f"   - {save_path.replace('.h5', '.tflite')}")
        print(f"   - {os.path.join(MODELS_DIR, 'confusion_matrix.png')}")
        print(f"   - {os.path.join(MODELS_DIR, 'training_history.png')}")
        
    else:
        print("❌ No data found. Please collect data first using collect_mp_legacy.py")

if __name__ == "__main__":
    main()
