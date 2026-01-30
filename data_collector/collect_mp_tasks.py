import sys
import os
import cv2
import time
import numpy as np
import mediapipe as mp
import shutil
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,  
                             QHBoxLayout, QLabel, QLineEdit, QComboBox, 
                             QPushButton, QMessageBox, QSpinBox, QSlider, QGroupBox, QFormLayout)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QImage, QPixmap

# Ensure the project root is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class VideoThread(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)
    
    def __init__(self):
        super().__init__()
        self._run_flag = True
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

    def set_camera_property(self, prop_id, value):
        if self.cap.isOpened():
            self.cap.set(prop_id, value)
        
    def run(self):
        while self._run_flag:
            start_time = time.time()
            ret, cv_img = self.cap.read()
            if ret:
                # Mirror the image
                cv_img = cv2.flip(cv_img, 1)
                self.change_pixmap_signal.emit(cv_img)
            
            elapsed = time.time() - start_time
            # Maintain 30 FPS
            delay = max(0.001, 0.033 - elapsed)
            time.sleep(delay)
            
    def stop(self):
        self._run_flag = False
        self.wait()
        self.cap.release()

class TasksCollector(QMainWindow):
    landmark_result_signal = pyqtSignal(list, int) # Landmarks list, timestamp

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Data Collector (Tasks MP)")
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
        
        self.gesture_name_input = QLineEdit()
        self.gesture_name_input.setPlaceholderText("Enter Gesture Name")
        controls_layout.addWidget(self.gesture_name_input)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Gesture", "Posture"])
        controls_layout.addWidget(self.mode_combo)
        
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
        self.gain_slider.setRange(0, 255)
        self.gain_slider.setValue(0)
        self.gain_slider.valueChanged.connect(self.update_gain)
        self.gain_layout.addWidget(self.gain_label)
        self.gain_layout.addWidget(self.gain_slider)
        self.camera_layout.addLayout(self.gain_layout)
        
        self.camera_group.setLayout(self.camera_layout)
        self.layout.addWidget(self.camera_group)
        
        self.status_label = QLabel("Ready")
        self.layout.addWidget(self.status_label)
        
        # MediaPipe Tasks Setup
        # Loading the model from local models dir
        model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'models', 'hand_landmarker.task'))
        
        if not os.path.exists(model_path):
            QMessageBox.critical(self, "Error", f"Model not found at: {model_path}")
            sys.exit(1)

        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.LIVE_STREAM,
            num_hands=1,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            result_callback=self.handle_result
        )
        self.landmarker = vision.HandLandmarker.create_from_options(options)

        # Drawing Utils (Legacy MP drawing helps visualization)
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_hands = mp.solutions.hands

        # Recording State
        self.is_recording = False
        self.recording_frames = []
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.countdown_val = 3
        self.record_duration = 1.5
        self.fps = 30
        self.total_frames = int(self.record_duration * self.fps)
        
        # Auto-Loop State
        self.target_episodes = 0
        self.current_episode = 0

        # Data storage
        self.recorded_files = [] 
        self.last_saved_file = None
        
        self.latest_landmarks = None

        # Video Thread
        self.thread = VideoThread()
        self.thread.change_pixmap_signal.connect(self.process_frame)
        self.thread.start()
        
        self.landmark_result_signal.connect(self.process_landmark_result)

    def closeEvent(self, event):
        self.thread.stop()
        self.landmarker.close()
        event.accept()

    def keyPressEvent(self, event):
        if event.text() == 'q':
            self.close()
        elif event.text() == 'z':
            self.delete_last_recording()

    def update_brightness(self, value):
        self.bright_label.setText(f"Brightness: {value}")
        self.thread.set_camera_property(cv2.CAP_PROP_BRIGHTNESS, value) 

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
        if self.recorded_files:
            file_to_delete = self.recorded_files.pop()
            if os.path.exists(file_to_delete):
                try:
                    os.remove(file_to_delete)
                    if self.current_episode > 0:
                        self.current_episode -= 1
                    self.status_label.setText(f"Deleted: {os.path.basename(file_to_delete)}. Resume Ep {self.current_episode + 1}")
                    self.last_saved_file = self.recorded_files[-1] if self.recorded_files else None
                except Exception as e:
                    self.status_label.setText(f"Error deleting: {e}")
            else:
                self.status_label.setText(f"File not found: {os.path.basename(file_to_delete)}")
        elif self.last_saved_file and os.path.exists(self.last_saved_file):
             # Fallback
            try:
                os.remove(self.last_saved_file)
                self.status_label.setText(f"Deleted: {os.path.basename(self.last_saved_file)}")
                self.last_saved_file = None
                if self.current_episode > 0:
                        self.current_episode -= 1
            except Exception as e:
                self.status_label.setText(f"Error deleting: {e}")
        else:
            self.status_label.setText("No recent file to delete.")

    def handle_result(self, result, output_image: mp.Image, timestamp_ms: int):
        # This runs in a separate thread. Emit signal to main thread.
        # We only care about landmarks
        if result.hand_landmarks:
            self.landmark_result_signal.emit(result.hand_landmarks, timestamp_ms)
        else:
            self.landmark_result_signal.emit([], timestamp_ms)

    def process_frame(self, cv_img):
        if cv_img is None:
            return
            
        # 1. Convert to MP Image
        rgb_frame = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        
        # 2. Asynchronously detect
        timestamp_ms = int(time.time() * 1000)
        self.landmarker.detect_async(mp_image, timestamp_ms)
        
        # 3. Draw LATEST landmarks on THIS frame for visualization
        # Note: This might be from previous frame, but acceptable for real-time visualization
        if self.latest_landmarks:
             # Convert HandLandmark objects to normalized list for drawing
             # Legacy Drawing utils expect normalized landmarks formatted differently
             # We might need to manually draw or convert
             # Easier: Manually draw
             self.draw_landmarks(cv_img, self.latest_landmarks)
        
        # --- OVERLAY ---
        # Prepare Text
        status_text = ""
        color = (0, 255, 0) # Green for Ready
        
        if self.is_recording:
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

        episode_text = f"Episode: {self.current_episode + 1} / {self.target_episodes}"
        
        if not self.is_recording:
            # Draw Background
            cv2.rectangle(cv_img, (0, 0), (350, 100), (0, 0, 0), -1)
            # Draw Text
            cv2.putText(cv_img, status_text, (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3)
            cv2.putText(cv_img, episode_text, (10, 85), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        # ---------------

        # 4. Show Image
        qt_img = self.convert_cv_qt(cv_img)
        self.video_label.setPixmap(qt_img)

    def process_landmark_result(self, landmarks_list, timestamp):
        # This is where we record data
        # Since 'landmarks_list' is a list of lists (one per hand), and we set max_num_hands=1
        
        hand_landmarks = []
        if landmarks_list:
            hand_landmarks = landmarks_list[0] # List of NormalizedLandmark
            self.latest_landmarks = hand_landmarks
        else:
            self.latest_landmarks = None
        
        if self.is_recording:
            frame_data = [] # 21 landmarks * 3 coords
            if hand_landmarks:
                for lm in hand_landmarks:
                    frame_data.append([lm.x, lm.y, lm.z])
            else:
                # Fill with zeros if no hand
                frame_data = [[0.0, 0.0, 0.0] for _ in range(21)]
            
            self.recording_frames.append(frame_data)
            
            if len(self.recording_frames) >= self.total_frames:
                self.stop_recording()

    def draw_landmarks(self, image, landmarks):
        # landmarks is list of NormalizedLandmark objects
        h, w, c = image.shape
        if landmarks:
            # Draw connections
            # We can use mp_drawing if we convert to a protobuf-like object or similar structure?
            # Actually, Tasks API returns a different object structure than Legacy.
            # So let's draw manually for simplicity.
            
            # Draw Points
            points = []
            for lm in landmarks:
                cx, cy = int(lm.x * w), int(lm.y * h)
                points.append((cx, cy))
                cv2.circle(image, (cx, cy), 5, (0, 255, 0), -1)
                
            # Draw Connections (Standard Hand Connections)
            connections = self.mp_hands.HAND_CONNECTIONS
            for start_idx, end_idx in connections:
                if start_idx < len(points) and end_idx < len(points):
                    cv2.line(image, points[start_idx], points[end_idx], (0, 255, 0), 2)

    def convert_cv_qt(self, cv_img):
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        p = convert_to_Qt_format.scaled(640, 480, Qt.AspectRatioMode.KeepAspectRatio)
        return QPixmap.fromImage(p)

    def start_recording_sequence(self):
        gesture_name = self.gesture_name_input.text().strip()
        if not gesture_name:
            QMessageBox.warning(self, "Input Error", "Please enter a gesture name.")
            return

        self.target_episodes = self.episode_count_input.value()
        self.current_episode = 0
        self.recorded_files = [] # clean stack
        
        # Disable controls during recording
        self.start_btn.setEnabled(False)
        self.toggle_inputs(False)
        
        self.start_countdown()
        
    def toggle_inputs(self, enabled):
        self.gesture_name_input.setEnabled(enabled)
        self.episode_count_input.setEnabled(enabled)
        self.mode_combo.setEnabled(enabled)
        self.camera_group.setEnabled(enabled)

    def start_countdown(self):
        self.countdown_val = 3
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
        self.status_label.setText(f"Episode {self.current_episode + 1}/{self.target_episodes}: Recording...")

    def stop_recording(self):
        self.is_recording = False
        # self.start_btn.setEnabled(True) # Don't enable yet
        self.status_label.setText("Recording Finished. Saving...")
        self.save_data()

    def save_data(self):
        gesture_name = self.gesture_name_input.text().strip()
        mode = self.mode_combo.currentText()
        
        # Save to data/tasks inside this directory
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data', 'tasks', mode, gesture_name))
        os.makedirs(base_dir, exist_ok=True)
        
        timestamp = int(time.time() * 1000)
        filename = f"{gesture_name}_{timestamp}.npy"
        filepath = os.path.join(base_dir, filename)
        
        data_To_save = np.array(self.recording_frames, dtype=np.float32)
        
        try:
            np.save(filepath, data_To_save)
            self.last_saved_file = filepath
            self.recorded_files.append(filepath)
            self.current_episode += 1
            self.status_label.setText(f"Saved: {filename}")
            
            # Check for Auto-Loop
            if self.current_episode < self.target_episodes:
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
    window = TasksCollector()
    window.show()
    sys.exit(app.exec())
