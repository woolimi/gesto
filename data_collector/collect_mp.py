import sys
import os
import cv2
import time
import threading
import numpy as np
import mediapipe as mp
import shutil
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QComboBox, 
                             QPushButton, QMessageBox, QSpinBox, QSlider, QGroupBox, QFormLayout, QCheckBox)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QEvent
from PyQt6.QtGui import QImage, QPixmap

# Ensure the project root is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import config
from lib.hand_features import (
    NUM_CHANNELS,
    WRIST,
    THUMB_TIP,
    INDEX_MCP,
    INDEX_PIP,
    INDEX_TIP,
    MIDDLE_PIP,
    MIDDLE_TIP,
    RING_PIP,
    RING_TIP,
    PINKY_PIP,
    PINKY_TIP,
    calculate_euclidean_dist,
    is_fist,
    process_hand_features,
)

# 시나리오 매니저 및 허용 제스처 목록 임포트
try:
    from data_collector.scenario_definitions import ScenarioManager, SUPPORTED_GESTURES
except ImportError:
    from scenario_definitions import ScenarioManager, SUPPORTED_GESTURES

# 폰트 설정
from PIL import ImageFont, ImageDraw, Image

if sys.platform == "darwin":
    # macOS: 한글 폰트 경로 (순서대로 탐색)
    FONT_PATH = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
    if not os.path.exists(FONT_PATH):
        FONT_PATH = "/System/Library/Fonts/Apple SD Gothic Neo.ttc"
    if not os.path.exists(FONT_PATH):
        FONT_PATH = "/Library/Fonts/AppleGothic.ttf"
    if not os.path.exists(FONT_PATH):
        FONT_PATH = "/System/Library/Fonts/Hiragino Sans GB.ttc"
    if not os.path.exists(FONT_PATH):
        FONT_PATH = os.path.expanduser("~/Library/Fonts/NotoSansCJK-Regular.ttc")
    if not os.path.exists(FONT_PATH):
        FONT_PATH = os.path.expanduser("~/Library/Fonts/NanumGothic.ttf")
    FONT_SIZE_SCALE = 1.5  # 맥·Retina에서 글씨 크게
elif sys.platform == "linux":
    # Ubuntu 등 Linux: 한글 폰트 경로 (순서대로 탐색)
    FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
    if not os.path.exists(FONT_PATH):
        FONT_PATH = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
    if not os.path.exists(FONT_PATH):
        FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
    FONT_SIZE_SCALE = 1.5  # 우분투에서도 글씨 크게
else:
    FONT_PATH = ""
    FONT_SIZE_SCALE = 1.0


class VideoThread(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)

    def __init__(self):
        super().__init__()
        self._run_flag = True
        self._lock = threading.Lock()
        self._latest_frame = None  # keep only the newest frame (drop backlog)

        # On Linux, using V4L2 backend tends to reduce capture jitter/latency.
        if sys.platform == "linux":
            cap = cv2.VideoCapture(config.CAMERA_INDEX, cv2.CAP_V4L2)
            if not cap.isOpened():
                cap = cv2.VideoCapture(config.CAMERA_INDEX)
            self.cap = cap
        else:
            self.cap = cv2.VideoCapture(config.CAMERA_INDEX)

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
        self.cap.set(cv2.CAP_PROP_FPS, config.CAMERA_FPS)

    def set_camera_property(self, prop_id, value):
        if self.cap.isOpened():
            self.cap.set(prop_id, value)

    def get_latest_frame(self):
        """Return the most recent frame and clear the buffer (frame dropping)."""
        with self._lock:
            frame = self._latest_frame
            self._latest_frame = None
        return frame

    def run(self):
        while self._run_flag:
            ret, cv_img = self.cap.read()
            if ret:
                # 거울 모드 (좌우 반전)
                cv_img = cv2.flip(cv_img, 1)
                with self._lock:
                    self._latest_frame = cv_img

            # Yield a bit to avoid burning 100% CPU if the camera is fast.
            time.sleep(0.001)

    def stop(self):
        self._run_flag = False
        self.wait()
        self.cap.release()


class LegacyCollector(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Data Collector (Legacy MP)")
        self.resize(1000, 800)
        
        # UI Elements
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # Display Video
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.video_label)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self.gesture_name_combo = QComboBox()
        self.gesture_name_combo.addItems(SUPPORTED_GESTURES)
        self.gesture_name_combo.setMinimumWidth(140)
        controls_layout.addWidget(QLabel("Gesture:"))
        controls_layout.addWidget(self.gesture_name_combo)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Gesture", "Posture"])
        controls_layout.addWidget(self.mode_combo)

        # Scenario Mode Checkbox
        self.scenario_mode_cb = QCheckBox("Scenario Mode")
        self.scenario_mode_cb.setChecked(False)
        self.scenario_mode_cb.stateChanged.connect(self.toggle_scenario_mode)
        controls_layout.addWidget(self.scenario_mode_cb)
        
        # User Name Input (New)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("User Name (e.g. Kyle)")
        self.username_input.setFixedWidth(120)
        controls_layout.addWidget(self.username_input)
        
        # Countdown Config (New)
        self.countdown_spin = QSpinBox()
        self.countdown_spin.setRange(0, 30)
        self.countdown_spin.setValue(5)
        self.countdown_spin.setPrefix("Wait: ")
        self.countdown_spin.setSuffix(" s")
        controls_layout.addWidget(self.countdown_spin)



        # Episode Count Input
        self.episode_count_input = QSpinBox()
        self.episode_count_input.setRange(1, 1000)
        self.episode_count_input.setValue(10)
        self.episode_count_input.setPrefix("Episodes: ")
        controls_layout.addWidget(self.episode_count_input)
        
        self.start_btn = QPushButton("Start Recording")
        self.start_btn.clicked.connect(self.start_recording_sequence)
        controls_layout.addWidget(self.start_btn)
        
        self.layout.addLayout(controls_layout)

        # Webcam Controls Group
        self.camera_group = QGroupBox("Camera Controls")
        self.camera_layout = QHBoxLayout()
        
        # Brightness
        self.bright_layout = QVBoxLayout()
        self.bright_label = QLabel("Brightness: 128")
        self.bright_slider = QSlider(Qt.Orientation.Horizontal)
        self.bright_slider.setRange(0, 255)
        self.bright_slider.setValue(128)
        self.bright_slider.valueChanged.connect(self.update_brightness)
        self.bright_layout.addWidget(self.bright_label)
        self.bright_layout.addWidget(self.bright_slider)
        self.camera_layout.addLayout(self.bright_layout)
        
        # Exposure
        self.exposure_layout = QVBoxLayout()
        self.exposure_label = QLabel("Exposure: -5")
        self.exposure_slider = QSlider(Qt.Orientation.Horizontal)
        self.exposure_slider.setRange(-10, 0) # Typical range, varies by camera
        self.exposure_slider.setValue(-5)
        self.exposure_slider.valueChanged.connect(self.update_exposure)
        self.exposure_layout.addWidget(self.exposure_label)
        self.exposure_layout.addWidget(self.exposure_slider)
        self.camera_layout.addLayout(self.exposure_layout)

        # Contrast
        self.contrast_layout = QVBoxLayout()
        self.contrast_label = QLabel("Contrast: 128")
        self.contrast_slider = QSlider(Qt.Orientation.Horizontal)
        self.contrast_slider.setRange(0, 255)
        self.contrast_slider.setValue(128)
        self.contrast_slider.valueChanged.connect(self.update_contrast)
        self.contrast_layout.addWidget(self.contrast_label)
        self.contrast_layout.addWidget(self.contrast_slider)
        self.camera_layout.addLayout(self.contrast_layout)

        # Saturation
        self.saturation_layout = QVBoxLayout()
        self.saturation_label = QLabel("Saturation: 128")
        self.saturation_slider = QSlider(Qt.Orientation.Horizontal)
        self.saturation_slider.setRange(0, 255)
        self.saturation_slider.setValue(128)
        self.saturation_slider.valueChanged.connect(self.update_saturation)
        self.saturation_layout.addWidget(self.saturation_label)
        self.saturation_layout.addWidget(self.saturation_slider)
        self.camera_layout.addLayout(self.saturation_layout)

        # Gain
        self.gain_layout = QVBoxLayout()
        self.gain_label = QLabel("Gain: 0")
        self.gain_slider = QSlider(Qt.Orientation.Horizontal)
        self.gain_slider.setRange(0, 255) # Gain range can be tricky, start with 0-255
        self.gain_slider.setValue(0)
        self.gain_slider.valueChanged.connect(self.update_gain)
        self.gain_layout.addWidget(self.gain_label)
        self.gain_layout.addWidget(self.gain_slider)
        self.camera_layout.addLayout(self.gain_layout)
        
        self.camera_group.setLayout(self.camera_layout)
        self.layout.addWidget(self.camera_group)

        self.status_label = QLabel("Ready")
        self.layout.addWidget(self.status_label)

        # Performance knobs (Ubuntu tends to be CPU-bound)
        self._is_linux = (sys.platform == "linux")
        self._mp_every_n = 2 if self._is_linux else 1  # run inference every N frames (display can still be 30fps)
        self._mp_tick = 0
        self._mp_cached_results = None
        self._display_max_width = 640 if self._is_linux else None  # downscale display/processing on Ubuntu
        self._font_cache = {}  # (size) -> ImageFont
        self._scenario_header_cache_key = None
        self._scenario_header_cache_img = None
        self._zero_hand = [[0.0] * NUM_CHANNELS for _ in range(21)]
        self._prev_right = None
        self._prev_left = None
        
        # MediaPipe Setup — 두 손 감지 (녹화 데이터: 42 랜드마크 = 손1 21 + 손2 21)
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            model_complexity=0 if self._is_linux else 1,
            max_num_hands=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils

        # Recording State
        self.is_recording = False
        self.recording_frames = []
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.countdown_val = 5 # 3초 -> 5초로 변경 (요청사항)
        self.record_duration = 1.0   # 1초(30프레임): 제스처에 집중, 주먹 등 대기 구간 영향 감소
        self.fps = 30
        self.total_frames = int(self.record_duration * self.fps)  # 30
        
        # Auto-Loop State
        self.target_episodes = 0
        self.current_episode = 0

        # Data storage
        self.recorded_files = [] # Stack for valid multi-undo
        self.last_saved_file = None
        
        # Scenario Manager
        self.scenario_manager = ScenarioManager()
        self.is_scenario_mode = False
        
        # Video Thread
        self.thread = VideoThread()
        self.thread.start()

        # Render loop: pull latest frame at a steady rate (prevents Qt signal backlog stutter)
        self.render_timer = QTimer()
        self.render_timer.timeout.connect(self.render_loop)
        self.render_timer.start(int(1000 / self.fps))

        # z: 마지막 녹화 삭제 (이벤트 필터로 포커스 무관하게 감지)
        QApplication.instance().installEventFilter(self)

    def render_loop(self):
        frame = self.thread.get_latest_frame()
        if frame is None:
            return
        self.update_image(frame)

    def eventFilter(self, obj, event):
        """포커스가 입력창 등에 있어도 'z' 한 번에 마지막 녹화 삭제."""
        if event.type() == QEvent.Type.KeyPress:
            is_z = (event.text() == "z") or (
                event.key() == Qt.Key.Key_Z
                and not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
            )
            if is_z and self.isVisible():
                if obj is self or (isinstance(obj, QWidget) and self.isAncestorOf(obj)):
                    self.delete_last_recording()
                    return True
        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        if hasattr(self, "render_timer"):
            self.render_timer.stop()
        self.thread.stop()
        self.hands.close()
        event.accept()

    def keyPressEvent(self, event):
        # Allow 'q' to quit as well
        if event.text() == 'q':
            self.close()
        elif event.text() == 'z':
            self.delete_last_recording()

    def update_brightness(self, value):
        self.bright_label.setText(f"Brightness: {value}")
        self.thread.set_camera_property(cv2.CAP_PROP_BRIGHTNESS, value) # Value scaling depends on camera

    def update_exposure(self, value):
        self.exposure_label.setText(f"Exposure: {value}")
        self.thread.set_camera_property(cv2.CAP_PROP_EXPOSURE, value)

    def update_contrast(self, value):
        self.contrast_label.setText(f"Contrast: {value}")
        self.thread.set_camera_property(cv2.CAP_PROP_CONTRAST, value)

    def update_saturation(self, value):
        self.saturation_label.setText(f"Saturation: {value}")
        self.thread.set_camera_property(cv2.CAP_PROP_SATURATION, value)

    def update_gain(self, value):
        self.gain_label.setText(f"Gain: {value}")
        self.thread.set_camera_property(cv2.CAP_PROP_GAIN, value)

    def delete_last_recording(self):
        """
        마지막 녹화 파일 삭제 및 상태 복구
        ('z' 키 입력 시 호출)
        """
        if self.recorded_files:
            file_to_delete = self.recorded_files.pop()
            if os.path.exists(file_to_delete):
                try:
                    os.remove(file_to_delete)
                    
                    # 시나리오 모드일 경우 단계 뒤로 가기
                    if self.is_scenario_mode:
                        if self.scenario_manager.prev():
                            self.current_episode -= 1  # Legacy 변수 동기화
                            self.status_label.setText(f"삭제됨: {os.path.basename(file_to_delete)}. 이전 단계로 복귀: {self.scenario_manager.get_current_step()['display_text']}")
                            self.countdown_timer.stop()  # 기존 타이머 중지 후 카운트다운 재시작
                            self.start_countdown()
                        else:
                            self.status_label.setText(f"삭제됨: {os.path.basename(file_to_delete)}. (첫 단계입니다)")
                    else:
                        # 일반 모드: 에피소드 되돌린 뒤 타이머 재가동하여 해당 구간 재녹화
                        if self.current_episode > 0:
                            self.current_episode -= 1
                        self.status_label.setText(f"삭제됨: {os.path.basename(file_to_delete)}. 에피소드 {self.current_episode + 1} 재녹화 대기...")
                        self.start_btn.setEnabled(False)
                        self.toggle_inputs(False)
                        self.countdown_timer.stop()
                        self.start_countdown()

                    self.last_saved_file = self.recorded_files[-1] if self.recorded_files else None
                except Exception as e:
                    self.status_label.setText(f"삭제 오류: {e}")
            else:
                self.status_label.setText(f"파일을 찾을 수 없음: {os.path.basename(file_to_delete)}")
                
        elif self.last_saved_file and os.path.exists(self.last_saved_file):
             # 스택이 비어있을 경우 (재시작 직후 등) 마지막 저장 파일 삭제 시도
            try:
                os.remove(self.last_saved_file)
                self.status_label.setText(f"삭제됨: {os.path.basename(self.last_saved_file)}")
                self.last_saved_file = None
                
                if self.is_scenario_mode:
                    if self.scenario_manager.prev():
                        self.current_episode -= 1
                        self.countdown_timer.stop()
                        self.start_countdown()
                elif self.current_episode > 0:
                        self.current_episode -= 1
            except Exception as e:
                self.status_label.setText(f"삭제 오류: {e}")
        else:
            self.status_label.setText("삭제할 최근 파일이 없습니다.")


    def toggle_scenario_mode(self, state):
        self.is_scenario_mode = (state == Qt.CheckState.Checked.value or state == 2)
        if self.is_scenario_mode:
            self.status_label.setText("Scenario Mode Enabled. Select gesture and Start.")
            self.episode_count_input.setEnabled(False) # Controlled by scenario
        else:
            self.episode_count_input.setEnabled(True)
            self.status_label.setText("Scenario Mode Disabled.")

    def _get_korean_font(self, font_size: int):
        size = int(font_size * FONT_SIZE_SCALE)
        if size in self._font_cache:
            return self._font_cache[size]

        try:
            if FONT_PATH and os.path.exists(FONT_PATH):
                font = ImageFont.truetype(FONT_PATH, size)
            else:
                font = ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()

        self._font_cache[size] = font
        return font

    def put_text_korean(self, img, text, position, font_size, color):
        img_pil = Image.fromarray(img)
        draw = ImageDraw.Draw(img_pil)
        font = self._get_korean_font(font_size)
        draw.text(position, text, font=font, fill=color)
        return np.array(img_pil)

    def _get_scenario_header_overlay(self, width: int, prog_text: str, inst_text: str, status: str):
        """Cache-render the top 100px overlay with Korean text (PIL is expensive per-frame)."""
        key = (width, prog_text, inst_text, status)
        if key == self._scenario_header_cache_key and self._scenario_header_cache_img is not None:
            return self._scenario_header_cache_img

        header = np.zeros((100, width, 3), dtype=np.uint8)
        header = self.put_text_korean(header, prog_text, (20, 15), 16, (200, 200, 200))
        header = self.put_text_korean(header, inst_text, (20, 45), 32, (0, 255, 0))
        header = self.put_text_korean(header, status, (width - 200, 30), 24, (255, 0, 0))

        self._scenario_header_cache_key = key
        self._scenario_header_cache_img = header
        return header


    def update_image(self, cv_img):
        # Process with MediaPipe in the main loop to keep sync
        if cv_img is None:
            return

        # Downscale on Linux to reduce CPU load (display + MediaPipe)
        if self._display_max_width is not None:
            h, w = cv_img.shape[:2]
            if w > self._display_max_width:
                scale = self._display_max_width / float(w)
                new_w = self._display_max_width
                new_h = max(1, int(h * scale))
                cv_img = cv2.resize(cv_img, (new_w, new_h), interpolation=cv2.INTER_AREA)

        img_rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        
        try:
            # Run MediaPipe inference less frequently for preview (but ALWAYS during recording).
            self._mp_tick += 1
            do_infer = self.is_recording or (self._mp_every_n <= 1) or (self._mp_tick % self._mp_every_n == 0) or (self._mp_cached_results is None)

            if do_infer:
                mp_rgb = img_rgb
                # Further downscale only for inference if frame is still large.
                if self._is_linux:
                    mh, mw = mp_rgb.shape[:2]
                    if mw > 640:
                        scale = 640 / float(mw)
                        mp_rgb = cv2.resize(mp_rgb, (640, max(1, int(mh * scale))), interpolation=cv2.INTER_AREA)
                self._mp_cached_results = self.hands.process(mp_rgb)

            results = self._mp_cached_results
            
            # Draw Landmarks
            if results and results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    self.mp_drawing.draw_landmarks(
                        cv_img, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
            
            # --- OVERLAY ---
            # Prepare Text
            # Status: Ready / Countdown / Recording / Finished
            status_text = ""
            color = (0, 255, 0) # Green for Ready
            
            if self.is_recording:
                # Calculate time left
                frames_recorded = len(self.recording_frames)
                time_elapsed = frames_recorded / self.fps
                time_left = max(0.0, self.record_duration - time_elapsed)
                status_text = f"Recording: {time_left:.1f}s"
                color = (0, 0, 255) # Red
            elif self.countdown_timer.isActive():
                status_text = f"Get Ready: {self.countdown_val}"
                color = (0, 255, 255) # Yellow
            else:
                if self.target_episodes > 0 and self.current_episode >= self.target_episodes:
                    status_text = "Finished"
                    color = (255, 0, 0) # Blue
                else:
                    status_text = "Ready"

            # Episode Info
            episode_text = f"Episode: {self.current_episode + 1} / {self.target_episodes}"
            
            # Draw Text
            if not self.is_recording:
                # Top Left Corner Background for text (맥/우분투 모두 FONT_SIZE_SCALE로 크게)
                cv2.rectangle(cv_img, (0, 0), (350, 100), (0, 0, 0), -1)
                scale_s, scale_e = 1.2 * FONT_SIZE_SCALE, 1.0 * FONT_SIZE_SCALE
                thick_s = max(2, int(3 * FONT_SIZE_SCALE))
                thick_e = max(2, int(2 * FONT_SIZE_SCALE))
                cv2.putText(cv_img, status_text, (10, 40), cv2.FONT_HERSHEY_SIMPLEX, scale_s, color, thick_s)
                cv2.putText(cv_img, episode_text, (10, 85), cv2.FONT_HERSHEY_SIMPLEX, scale_e, (255, 255, 255), thick_e)
            # ---------------

            # Recording Logic: 11-channel data (3 original + 8 features)
            if self.is_recording:
                right_landmarks = self._zero_hand[0:21] # Should be [21, 3] for feature calc if not None
                # Actually, landmarks are [x,y,z]. Slot needs to be [21, 11].
                
                # Default xyz slots
                right_xyz = [[0.0, 0.0, 0.0] for _ in range(21)]
                left_xyz = [[0.0, 0.0, 0.0] for _ in range(21)]
                
                if results and results.multi_hand_landmarks and results.multi_handedness:
                    for hlm, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                        label = handedness.classification[0].label if handedness.classification else ""
                        pts = [[lm.x, lm.y, lm.z] for lm in hlm.landmark]
                        if label == "Right":
                            right_xyz = pts
                        else:
                            left_xyz = pts
                
                # Calculate Features
                left_feats = process_hand_features(left_xyz, self._prev_left)
                right_feats = process_hand_features(right_xyz, self._prev_right)
                
                # Update prev state
                self._prev_right = right_xyz
                self._prev_left = left_xyz
                
                # Construct (42, 11) data for this frame
                frame_data_11 = []
                # Right Hand Slot (Indices 0-20)
                for pt in right_xyz:
                    # Ch 0-2: xyz, Ch 3-6: Left Features, Ch 7-10: Right Features
                    # Wait, the user said:
                    # Channel 3: Is_Fist (Left)
                    # Channel 4: Pinch_Dist (Left)
                    # ...
                    # Channel 7: Is_Fist (Right)
                    # ...
                    # This is for ALL landmarks.
                    full_pt = pt + left_feats + right_feats
                    frame_data_11.append(full_pt)
                
                # Left Hand Slot (Indices 21-41)
                for pt in left_xyz:
                    full_pt = pt + left_feats + right_feats
                    frame_data_11.append(full_pt)

                self.recording_frames.append(frame_data_11)
                
                if len(self.recording_frames) >= self.total_frames:
                    self.stop_recording()

            # --- SCENARIO OVERLAY ---
            # 시나리오 모드일 때 HUD 그리기 (녹화 중이 아닐 때)
            if self.is_scenario_mode and not self.is_recording:
                prog_text = self.scenario_manager.get_progress_text()
                inst_text = self.scenario_manager.get_instruction_text()

                status = "READY"
                if self.countdown_timer.isActive():
                    status = f"COUNT: {self.countdown_val}"

                # Cached top header (Korean text)
                header = self._get_scenario_header_overlay(cv_img.shape[1], prog_text, inst_text, status)
                cv_img[0:header.shape[0], 0:header.shape[1]] = header

                # Countdown number in the center (digits only -> use OpenCV, cheaper than PIL)
                if self.countdown_timer.isActive():
                    h, w, _ = cv_img.shape
                    scale = 4.0 * FONT_SIZE_SCALE
                    thickness = max(3, int(6 * FONT_SIZE_SCALE))
                    text = str(self.countdown_val)
                    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
                    x = max(0, (w - tw) // 2)
                    y = max(th + 10, (h + th) // 2)
                    cv2.putText(cv_img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 255, 255), thickness)
            # ------------------------



        except Exception as e:
            print(f"Error in MediaPipe process: {e}")
        
        # 카운트다운 중에는 흑백, 녹화 시작 시 컬러
        if self.countdown_timer.isActive():
            gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
            cv_img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        
        # Show Image
        qt_img = self.convert_cv_qt(cv_img)
        self.video_label.setPixmap(qt_img)

    def convert_cv_qt(self, cv_img):
        # BGR888 avoids an extra cvtColor (cheaper on CPU-bound Linux boxes).
        cv_img = np.ascontiguousarray(cv_img)
        h, w, ch = cv_img.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(cv_img.data, w, h, bytes_per_line, QImage.Format.Format_BGR888)
        p = convert_to_Qt_format.scaled(
            640,
            480,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        return QPixmap.fromImage(p)

    def start_recording_sequence(self):
        gesture_name = self.gesture_name_combo.currentText().strip()
        username = self.username_input.text().strip()

        if self.is_scenario_mode and not username:
            QMessageBox.warning(self, "입력 오류", "사용자 이름(ID)을 입력해주세요.\n데이터 병합 시 충돌 방지를 위해 필요합니다.")
            return

        self.target_episodes = self.episode_count_input.value()


        self.current_episode = 0
        self.recorded_files = [] # Clear stack on new run
        
        # Disable controls during recording
        self.start_btn.setEnabled(False)
        self.curr_controls_enabled = False
        self.toggle_inputs(False)
        
        self.start_countdown()
        
        # Initialize Scenario if in Scenario Mode
        if self.is_scenario_mode:
             self.scenario_manager.generate_scenarios(gesture_name)
             if self.scenario_manager.total_scenarios == 0:
                 QMessageBox.warning(self, "Warning", f"No scenario definition found for '{gesture_name}'. Defaulting to manual.")
                 self.is_scenario_mode = False
             else:
                 self.target_episodes = self.scenario_manager.total_scenarios

        
    def toggle_inputs(self, enabled):
        self.gesture_name_combo.setEnabled(enabled)
        self.episode_count_input.setEnabled(enabled)
        self.mode_combo.setEnabled(enabled)
        self.camera_group.setEnabled(enabled) # Optional: disable camera controls during recording
        # User and Countdown should be disabled during recording
        self.username_input.setEnabled(enabled)
        self.countdown_spin.setEnabled(enabled)

    def start_countdown(self):
        self.countdown_val = self.countdown_spin.value() # UI 값 사용
        self.status_label.setText(f"Episode {self.current_episode + 1}/{self.target_episodes}: Starting in {self.countdown_val}...")
        self.countdown_timer.start(1000)


    def update_countdown(self):
        self.countdown_val -= 1
        if self.countdown_val > 0:
            self.status_label.setText(f"Episode {self.current_episode + 1}/{self.target_episodes}: Starting in {self.countdown_val}...")
        else:
            self.countdown_timer.stop()
            self.start_recording()

    def start_recording(self):
        self.is_recording = True
        self.recording_frames = [] # Reset buffer
        self._prev_right = None # Reset velocity states
        self._prev_left = None
        self.status_label.setText(f"Episode {self.current_episode + 1}/{self.target_episodes}: Recording...")

    def stop_recording(self):
        self.is_recording = False
        # self.start_btn.setEnabled(True) # Don't enable yet
        self.status_label.setText("Recording Finished. Saving...")
        self.save_data()

    def save_data(self):
        gesture_name = self.gesture_name_combo.currentText().strip()
        mode = self.mode_combo.currentText()
        
        # Base Data Dir: data_collector/data/Gesture/<gesture_name> 또는 data/Posture/...
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data', mode, gesture_name))
        os.makedirs(base_dir, exist_ok=True)
        
        timestamp = int(time.time() * 1000)
        
        username = self.username_input.text().strip()
        
        if self.is_scenario_mode:
             # 현재 스텝이 없으면 저장하지 않음 (마지막 완료 후 중복 저장 시 unknown.npy 방지)
             step = self.scenario_manager.get_current_step()
             if step is None:
                 self.start_btn.setEnabled(True)
                 self.toggle_inputs(True)
                 self.status_label.setText("All Scenarios Completed!")
                 return
             filename = self.scenario_manager.get_filename(username=username)
        else:
             # Legacy Filename Logic + Username
             user_suffix = f"_{username}" if username else ""
             filename = f"{gesture_name}_{timestamp}{user_suffix}.npy"
        
        filepath = os.path.join(base_dir, filename)

        
        # Save as (Frames, 42, 11)
        data_To_save = np.array(self.recording_frames, dtype=np.float32)
        
        try:
            np.save(filepath, data_To_save)
            self.last_saved_file = filepath
            self.recorded_files.append(filepath) # Push to stack
            self.current_episode += 1
            self.status_label.setText(f"Saved: {filename}")
            
            # Check for Auto-Loop
            if self.is_scenario_mode:
                # Scenario Mode Logic (next()는 인덱스만 증가시키고, 마지막 저장 후에도 True를 반환할 수 있음)
                self.scenario_manager.next()
                if self.scenario_manager.is_finished():
                    self.start_btn.setEnabled(True)
                    self.toggle_inputs(True)
                    self.status_label.setText("All Scenarios Completed!")
                    QMessageBox.information(self, "Done", "All Scenarios Completed!")
                else:
                    self.current_episode += 1
                    self.status_label.setText(f"Next: {self.scenario_manager.get_instruction_text()}")
                    QTimer.singleShot(1000, self.start_countdown)
            
            elif self.current_episode < self.target_episodes:
                # Restart Countdown
                self.start_countdown()
            else:
                # Finished all episodes
                self.start_btn.setEnabled(True)
                self.toggle_inputs(True)
                self.status_label.setText(f"Completed {self.target_episodes} episodes.")
                
        except Exception as e:
            self.status_label.setText(f"Error saving: {e}")
            self.start_btn.setEnabled(True)
            self.toggle_inputs(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LegacyCollector()
    window.show()
    sys.exit(app.exec())
