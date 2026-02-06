import os
import sys
import cv2
import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.gridspec as gridspec
from matplotlib.widgets import Button, Slider
import mediapipe as mp
from collections import deque
from PyQt6.QtWidgets import QApplication, QFileDialog

# 프로젝트 루트 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import config

# train.py에서 모델 생성 함수 및 상수를 임포트
try:
    from data_trainer.train import create_model, INPUT_SHAPE, SEQUENCE_LENGTH, LANDMARKS_COUNT
except ImportError:
    # 경로 문제 시 현재 디렉토리에서 임포트 시도
    sys.path.append(os.path.dirname(__file__))
    from train import create_model, INPUT_SHAPE, SEQUENCE_LENGTH, LANDMARKS_COUNT

def normalize_landmarks(data):
    """
    랜드마크 정규화: 손목(랜드마크 0) 기준 상대 좌표 변환
    data: (frames, 21, 3)
    """
    wrist = data[:, 0:1, :]
    normalized = data - wrist
    scale = np.max(np.abs(normalized), axis=(1, 2), keepdims=True) + 1e-6
    normalized = normalized / scale
    return normalized

def analyze_video(video_path, model_path):
    print(f"🎬 분석 시작: {video_path}")
    
    # 라벨 로드
    labels_path = model_path.replace(".h5", "_labels.txt")
    if os.path.exists(labels_path):
        with open(labels_path, "r", encoding="utf-8") as f:
            classes = [line.strip() for line in f if line.strip()]
    else:
        classes = ["Pinch_In", "Pinch_Out", "Swipe_Left", "Swipe_Right"]
        print(f"⚠️ 라벨 파일 없음. 기본값 사용: {classes}")

    # 모델 재구성 및 가중치 로드
    print(f"🧠 모델 구성 및 가중치 로드: {model_path}")
    try:
        model = create_model(len(classes))
        dummy_input = np.zeros((1, *INPUT_SHAPE), dtype=np.float32)
        model(dummy_input)
        model.load_weights(model_path)
    except Exception as e:
        print(f"❌ 모델 로드 실패: {e}")
        return

    # 미디어파이프 설정 (Drawing Utils 포함)
    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils
    mp_drawing_styles = mp.solutions.drawing_styles
    
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"ℹ️ Video info: {fps:.2f} FPS, {total_frames} Frames")

    buffer = deque(maxlen=SEQUENCE_LENGTH)
    results = {cls: [] for cls in classes}
    timestamps = []
    frames = [] 

    frame_idx = 0
    print("⏳ 데이터 처리 중... (랜드마크 오버레이 및 분석)")
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        # BGR -> RGB & Flip
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_rgb = cv2.flip(frame_rgb, 1)

        result = hands.process(frame_rgb)
        
        # 랜드마크 오버레이 그리기 (원본에 오버레이)
        annotated_image = frame_rgb.copy()
        
        landmarks_data = None
        if result.multi_hand_landmarks:
            hand_landmarks = result.multi_hand_landmarks[0]
            landmarks_data = [[lm.x, lm.y, lm.z] for lm in hand_landmarks.landmark]
            
            # 손 뼈대 그리기
            mp_drawing.draw_landmarks(
                annotated_image,
                hand_landmarks,
                mp_hands.HAND_CONNECTIONS,
                mp_drawing_styles.get_default_hand_landmarks_style(),
                mp_drawing_styles.get_default_hand_connections_style())
        else:
            landmarks_data = [[0.0, 0.0, 0.0] for _ in range(LANDMARKS_COUNT)]

        # 시각화용 리스트에 저장
        frames.append(annotated_image)

        # 버퍼 및 추론
        buffer.append(landmarks_data)
        
        probs = [0.0] * len(classes)
        if len(buffer) == SEQUENCE_LENGTH:
            data = np.array(buffer, dtype=np.float32) 
            data_normalized = normalize_landmarks(data)
            data_flat = data_normalized.reshape(SEQUENCE_LENGTH, -1)
            data_input = np.expand_dims(data_flat, axis=0)
            
            prediction = model.predict(data_input, verbose=0)
            probs = prediction[0]

        for i, cls in enumerate(classes):
            results[cls].append(probs[i])
        timestamps.append(frame_idx / fps)

        frame_idx += 1
        pct = (frame_idx / total_frames) * 100 if total_frames > 0 else 0
        if frame_idx % 30 == 0:
            print(f"\r   Progress: {pct:.1f}% ({frame_idx}/{total_frames})", end="")

    print("\n✅ 분석 완료. 시각화 준비 중...")
    cap.release()
    hands.close()

    # --- 시각화 (좌측 비디오 / 우측 그래프 4행) ---
    fig = plt.figure(figsize=(16, 9))
    num_classes = len(classes)
    
    gs = gridspec.GridSpec(num_classes, 2, width_ratios=[1.5, 1])

    # 1. 비디오 화면
    ax_video = fig.add_subplot(gs[:, 0]) 
    ax_video.set_title(f"Video (Mirrored): {os.path.basename(video_path)}")
    ax_video.axis('off')
    if frames:
        im_video = ax_video.imshow(frames[0])
    
    # 2. 그래프
    axs_graphs = []
    lines = []
    cursors = []
    colors = ['#FF5733', '#33FF57', '#3357FF', '#F333FF', '#FF33A8']
    
    max_time = timestamps[-1] if timestamps else 1
    
    for i, cls in enumerate(classes):
        ax = fig.add_subplot(gs[i, 1])
        ax.text(1.02, 0.5, cls, transform=ax.transAxes, va='center', ha='left', fontsize=12, fontweight='bold', color=colors[i % len(colors)])
        
        ax.set_ylim(-0.1, 1.1)
        ax.set_xlim(0, max_time)
        ax.grid(True, linestyle=':', alpha=0.6)
        
        if i < num_classes - 1:
            ax.set_xticklabels([])
        else:
            ax.set_xlabel('Time (s)')
            
        line, = ax.plot(timestamps, results[cls], color=colors[i % len(colors)], linewidth=2, alpha=0.8)
        cursor = ax.axvline(x=0, color='red', linestyle='-', linewidth=1.5, alpha=0.9)
        ax.axhline(y=0.7, color='gray', linestyle='--', linewidth=0.8, alpha=0.5)
        
        axs_graphs.append(ax)
        lines.append(line)
        cursors.append(cursor)

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.15) 

    # --- 플레이어 로직 ---
    class Player:
        def __init__(self):
            self.frame_idx = 0
            self.is_paused = False
            self.is_exporting = False

        def update(self, i):
            if self.is_exporting: # 내보내기 중엔 외부 프레임 번호 따름
                idx = i
            elif slider.eventson and slider.val != self.frame_idx and self.is_paused:
                 self.frame_idx = int(slider.val)
                 idx = self.frame_idx
            elif not self.is_paused:
                self.frame_idx = (self.frame_idx + 1) % len(frames)
                slider.eventson = False
                slider.set_val(self.frame_idx)
                slider.eventson = True
                idx = int(self.frame_idx)
            else:
                idx = int(self.frame_idx)
            
            if idx >= len(frames): idx = len(frames) - 1
            
            # 그리기 업데이트
            im_video.set_data(frames[idx])
            current_time = timestamps[idx] if idx < len(timestamps) else 0
            for cursor in cursors:
                 cursor.set_xdata([current_time, current_time])
                
            return [im_video] + cursors

        def toggle_play(self, event):
            self.is_paused = not self.is_paused
            btn_play.label.set_text('Play' if self.is_paused else 'Pause')

        def on_slider_change(self, val):
            self.frame_idx = int(val)
            self.is_paused = True 
            btn_play.label.set_text('Play')
            
            im_video.set_data(frames[self.frame_idx])
            current_time = timestamps[self.frame_idx]
            for cursor in cursors:
                cursor.set_xdata([current_time, current_time])
            fig.canvas.draw_idle()

        def save_video(self, event):
            self.is_paused = True
            btn_play.label.set_text('Play')
            btn_save.label.set_text('Saving...')
            plt.draw()
            
            save_path = video_path + "_analyzed.mp4"
            print(f"\n💾 비디오 저장 시작: {save_path}")
            
            self.is_exporting = True
            try:
                # FFMpeg Writer 설정
                Writer = animation.writers['ffmpeg']
                writer = Writer(fps=fps, metadata=dict(artist='Gesto'), bitrate=1800)
                
                # 애니메이션을 새로 생성하여 저장 (현재 UI 상태와 분리)
                save_anim = animation.FuncAnimation(fig, self.update, frames=len(frames), blit=False)
                save_anim.save(save_path, writer=writer)
                print("✅ 저장 완료!")
                btn_save.label.set_text('Saved!')
            except Exception as e:
                print(f"❌ 저장 실패: {e}")
                print("FFmpeg가 설치되어 있는지 확인해주세요 (sudo apt install ffmpeg).")
                btn_save.label.set_text('Error')
            
            self.is_exporting = False


    player = Player()

    # 메인 애니메이션
    anim = animation.FuncAnimation(
        fig, 
        player.update, 
        frames=None, 
        interval=1000/fps, 
        blit=False, 
        cache_frame_data=False
    )

    # --- UI 버튼 ---
    # 1. Play/Pause
    ax_play = plt.axes([0.35, 0.02, 0.1, 0.05])
    btn_play = Button(ax_play, 'Pause')
    btn_play.on_clicked(player.toggle_play)
    
    # 2. Save Video
    ax_save = plt.axes([0.55, 0.02, 0.1, 0.05])
    btn_save = Button(ax_save, 'Save MP4')
    btn_save.on_clicked(player.save_video)

    # 3. Slider
    ax_slider = plt.axes([0.15, 0.08, 0.7, 0.03])
    slider = Slider(
        ax=ax_slider, 
        label='Frame', 
        valmin=0, 
        valmax=len(frames)-1, 
        valinit=0, 
        valstep=1,
        color='lightblue'
    )
    slider.on_changed(player.on_slider_change)

    print("🎥 재생 시작!")
    plt.show()

def select_file():
    app = QApplication(sys.argv)
    file_path, _ = QFileDialog.getOpenFileName(
        None, 
        "Select Video File", 
        os.path.join(os.path.dirname(__file__), "data"), 
        "Video Files (*.mp4 *.avi *.mov *.webm *.mkv);;All Files (*)"
    )
    return file_path

if __name__ == "__main__":
    # 모델 경로 자동 탐색
    default_model_path = os.path.join(os.path.dirname(__file__), "models", "lstm_legacy.h5")
    
    if len(sys.argv) > 1:
        target_video = sys.argv[1]
    else:
        target_video = select_file()

    if target_video and os.path.exists(target_video):
        if os.path.exists(default_model_path):
            analyze_video(target_video, default_model_path)
        else:
            print(f"❌ 모델을 찾을 수 없습니다: {default_model_path}")
            print("먼저 train.py를 실행하여 모델을 학습시켜주세요.")
            print("python train.py")
    else:
        print("No video selected.")
